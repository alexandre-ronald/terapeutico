from datetime import date, time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from .models import Cirurgia, GiroSala, NecessidadeCirurgica, Paciente, ProgramacaoCirurgia, ProgramacaoNecessidade


class PainelProgramadorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="painel", password="teste")
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="centrocirurgico", content_type__model__in=("programacaocirurgia", "programacaonecessidade")))
        self.client.force_login(self.user)
        paciente = Paciente.objects.create(nome="Paciente Painel", prontuario="100")
        cirurgia = Cirurgia.objects.create(paciente=paciente, procedimento="Cirurgia Teste", medico="Cirurgião", sala="SALA 2", data=date.today(), hora=time(8))
        self.programacao = ProgramacaoCirurgia.objects.create(cirurgia=cirurgia, sala_painel="2", hora_painel=time(9), leito_paciente="UTI-12", criado_por=self.user, atualizado_por=self.user, status=ProgramacaoCirurgia.ENVIADA)
        GiroSala.objects.create(paciente=paciente, cirurgia=cirurgia, dataInicioCirurgia="2026-09-11T09:00:00Z")
        catalogo = NecessidadeCirurgica.objects.create(nome="Leito de UTI")
        self.necessidade = ProgramacaoNecessidade.objects.create(
            programacao=self.programacao, necessidade=catalogo, complemento="P1",
            atendida=True, atendida_por=self.user,
        )

    def test_exibe_dados_operacionais_e_etapa(self):
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        self.assertContains(response, '<div class="sala-numero">02</div>', html=True)
        self.assertContains(response, "09:00")
        self.assertContains(response, "Cirurgia em andamento")
        self.assertContains(response, "Leito de UTI")
        self.assertContains(response, "P1")
        self.assertContains(response, "Leito: UTI-12")
        self.assertContains(response, "Prontuário · Nascimento · Leito")
        self.assertContains(response, "Nova atualização em")
        self.assertContains(response, "Sala sem cirurgia enviada ao painel", count=8)
        self.assertContains(response, "Cirurgia iniciada")

    def test_preparacao_colore_linha_sem_textos_redundantes(self):
        giro = GiroSala.objects.get(cirurgia=self.programacao.cirurgia)
        giro.dataInicioCirurgia = None
        giro.save(update_fields=("dataInicioCirurgia",))
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        self.assertContains(response, 'class="linha-sala status-preparacao"')
        self.assertNotContains(response, "Aguardando início da cirurgia")
        self.assertContains(response, "Painel de Cirurgias")
        self.assertNotContains(response, "Cirurgias enviadas para as salas cirúrgicas")

    def test_painel_e_somente_leitura_e_sem_layout_do_sistema(self):
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        self.assertNotContains(response, "app-menu navbar-menu")
        self.assertNotContains(response, "necessidade_alternar_atendimento")
        self.assertNotContains(response, "<form")

    def test_painel_mostra_as_nove_salas_e_legenda_antes_da_tabela(self):
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        conteudo = response.content.decode()
        for numero in range(1, 10):
            self.assertContains(response, f'<div class="sala-numero">{numero:02d}</div>', html=True)
        self.assertLess(conteudo.index("painel-legenda"), conteudo.index("painel-tabela"))

    def test_sala_liberada_retira_cirurgia_do_painel(self):
        giro = GiroSala.objects.get(cirurgia=self.programacao.cirurgia)
        giro.dataSalaLiberada = "2026-09-11T12:00:00Z"
        giro.save()
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        self.programacao.refresh_from_db()
        self.assertNotContains(response, "Paciente Painel")
        self.assertEqual(self.programacao.status, ProgramacaoCirurgia.FINALIZADA)
