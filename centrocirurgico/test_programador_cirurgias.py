from datetime import date, datetime, time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from .models import (
    Cirurgia, GiroSala, NecessidadeCirurgica, Paciente,
    ProgramacaoCirurgia, ProgramacaoNecessidade,
)


class ProgramadorCirurgiasTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="programador", password="teste")
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="centrocirurgico", content_type__model="programacaocirurgia"))
        self.client.force_login(self.user)
        self.p1 = Paciente.objects.create(nome="Paciente Um", prontuario="1")
        self.p2 = Paciente.objects.create(nome="Paciente Dois", prontuario="2")
        self.c1 = Cirurgia.objects.create(paciente=self.p1, procedimento="Cirurgia 1", sala="SALA 1", data=date.today(), hora=time(8))
        self.c2 = Cirurgia.objects.create(paciente=self.p2, procedimento="Cirurgia 2", sala="SALA 1", data=date.today(), hora=time(10))
        self.a = ProgramacaoCirurgia.objects.create(cirurgia=self.c1, tipo_cirurgia=ProgramacaoCirurgia.ELETIVA, criado_por=self.user, atualizado_por=self.user, status=ProgramacaoCirurgia.ENVIADA)
        self.b = ProgramacaoCirurgia.objects.create(cirurgia=self.c2, tipo_cirurgia=ProgramacaoCirurgia.EXTRA_MAPA, criado_por=self.user, atualizado_por=self.user)

    @patch("centrocirurgico.views_programador.buscar_mapa_cirurgico_aghu")
    def test_data_atual_vem_preenchida_sem_consulta_automatica(self, buscar_mapa):
        response = self.client.get(reverse("centrocirurgico:programador_mapa"))
        buscar_mapa.assert_not_called()
        self.assertContains(response, f'value="{date.today().isoformat()}"')

    def test_bloqueia_envio_quando_sala_esta_ocupada(self):
        response = self.client.post(reverse("centrocirurgico:programacao_enviar", args=[self.b.pk]), follow=True)
        self.b.refresh_from_db()
        self.assertEqual(self.b.status, ProgramacaoCirurgia.RASCUNHO)
        self.assertContains(response, "está ocupada")

    def test_libera_envio_apos_final_da_cirurgia_anterior(self):
        GiroSala.objects.create(paciente=self.p1, cirurgia=self.c1, dataFinalCirurgia="2026-09-11T10:00:00Z")
        self.client.post(reverse("centrocirurgico:programacao_enviar", args=[self.b.pk]))
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertEqual(self.a.status, ProgramacaoCirurgia.FINALIZADA)
        self.assertEqual(self.b.status, ProgramacaoCirurgia.ENVIADA)

    def test_sala_alterada_e_usada_no_bloqueio(self):
        self.b.sala_painel = "2"
        self.b.hora_painel = time(11, 30)
        self.b.circulante = "Circulante Teste"
        self.b.residente = "Residente Teste"
        self.b.enfermeiro = "Enfermeiro Teste"
        self.b.save()

        self.client.post(reverse("centrocirurgico:programacao_enviar", args=[self.b.pk]))

        self.b.refresh_from_db()
        self.assertEqual(self.b.status, ProgramacaoCirurgia.ENVIADA)
        self.assertEqual(self.b.sala_painel, "2")
        self.assertEqual(self.b.hora_painel, time(11, 30))
        self.assertEqual(self.b.circulante, "Circulante Teste")
        self.assertEqual(self.b.residente, "Residente Teste")
        self.assertEqual(self.b.enfermeiro, "Enfermeiro Teste")

    def test_formulario_exige_tipo_da_cirurgia(self):
        response = self.client.post(reverse("centrocirurgico:programacao_editar", args=[self.b.pk]), {
            "tipo_cirurgia": "", "sala_painel": "2", "hora_painel": "11:30",
            "anestesistas": "", "instrumentador": "", "circulante": "",
            "residente": "", "enfermeiro": "", "outros_profissionais": "",
            "observacao": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo é obrigatório")

    def test_formulario_exige_sala_entre_um_e_nove(self):
        response = self.client.post(reverse("centrocirurgico:programacao_editar", args=[self.b.pk]), {
            "tipo_cirurgia": "eletiva", "sala_painel": "10", "hora_painel": "11:30", "anestesistas": "",
            "instrumentador": "", "circulante": "", "residente": "", "enfermeiro": "",
            "outros_profissionais": "", "observacao": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Faça uma escolha válida")

    @patch("centrocirurgico.views_programador.buscar_mapa_cirurgico_aghu")
    def test_mapa_sincroniza_leito_de_programacao_existente(self, buscar_mapa):
        buscar_mapa.return_value = [{
            "prontuario": "1", "nome_paciente": "Paciente Um",
            "data_nascimento": None, "data_inicio_cirurgia": datetime.combine(date.today(), time(8)),
            "sala": "SALA 1", "procedimento": "Cirurgia 1",
            "especialidade": "", "medico": "", "leito": "UTI-07",
        }]

        response = self.client.get(reverse("centrocirurgico:programador_mapa"), {"data_mapa": date.today().isoformat()})

        self.assertEqual(response.status_code, 200)
        self.a.refresh_from_db()
        self.assertEqual(self.a.leito_paciente, "UTI-07")

    def test_retira_do_painel_por_sala_sem_excluir_programacao(self):
        self.a.sala_painel = "2"
        self.a.save(update_fields=("sala_painel",))

        response = self.client.post(
            reverse("centrocirurgico:programacao_retirar_painel"),
            {"acao": "sala", "sala": "2"},
        )

        self.assertEqual(response.status_code, 302)
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, ProgramacaoCirurgia.RASCUNHO)
        self.assertIsNone(self.a.enviado_em)
        self.assertTrue(ProgramacaoCirurgia.objects.filter(pk=self.a.pk).exists())

    def test_retira_do_painel_por_paciente(self):
        self.client.post(
            reverse("centrocirurgico:programacao_retirar_painel"),
            {"acao": "paciente", "programacao": str(self.a.pk)},
        )

        self.a.refresh_from_db()
        self.assertEqual(self.a.status, ProgramacaoCirurgia.RASCUNHO)

    def test_limpa_todas_as_cirurgias_do_painel(self):
        self.b.status = ProgramacaoCirurgia.ENVIADA
        self.b.sala_painel = "2"
        self.b.save(update_fields=("status", "sala_painel"))

        self.client.post(
            reverse("centrocirurgico:programacao_retirar_painel"),
            {"acao": "todos"},
        )

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.status, ProgramacaoCirurgia.RASCUNHO)
        self.assertEqual(self.b.status, ProgramacaoCirurgia.RASCUNHO)

    def test_permite_envio_com_necessidade_pendente(self):
        self.b.sala_painel = "2"
        self.b.save(update_fields=("sala_painel",))
        catalogo = NecessidadeCirurgica.objects.create(nome="Leito de UTI")
        ProgramacaoNecessidade.objects.create(
            programacao=self.b, necessidade=catalogo, complemento="P1"
        )
        response = self.client.post(
            reverse("centrocirurgico:programacao_enviar", args=[self.b.pk]),
            follow=True,
        )
        self.b.refresh_from_db()
        self.assertEqual(self.b.status, ProgramacaoCirurgia.ENVIADA)
        self.assertNotContains(response, "Confirme todas as necessidades")

    def test_confirmacao_da_necessidade_e_auditada_no_programador(self):
        catalogo = NecessidadeCirurgica.objects.create(nome="Sangue")
        response = self.client.post(
            reverse("centrocirurgico:programacao_editar", args=[self.b.pk]),
            {
                "tipo_cirurgia": "eletiva", "sala_painel": "1", "hora_painel": "10:00",
                "anestesistas": "", "instrumentador": "", "circulante": "",
                "residente": "", "enfermeiro": "", "outros_profissionais": "",
                "observacao": "", "necessidades": [str(catalogo.pk)],
                f"complemento_{catalogo.pk}": "Plaquetas",
                f"atendida_{catalogo.pk}": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        vinculo = ProgramacaoNecessidade.objects.get(programacao=self.b)
        self.assertTrue(vinculo.atendida)
        self.assertEqual(vinculo.atendida_por, self.user)
        self.assertIsNotNone(vinculo.atendida_em)
