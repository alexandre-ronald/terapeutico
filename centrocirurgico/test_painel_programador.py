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
        self.programacao = ProgramacaoCirurgia.objects.create(cirurgia=cirurgia, sala_painel="2", hora_painel=time(9), criado_por=self.user, atualizado_por=self.user, status=ProgramacaoCirurgia.ENVIADA)
        GiroSala.objects.create(paciente=paciente, cirurgia=cirurgia, dataInicioCirurgia="2026-09-11T09:00:00Z")
        catalogo = NecessidadeCirurgica.objects.create(nome="Leito de UTI")
        self.necessidade = ProgramacaoNecessidade.objects.create(programacao=self.programacao, necessidade=catalogo, complemento="P1")

    def test_exibe_dados_operacionais_e_etapa(self):
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        self.assertContains(response, '<div class="sala-numero">02</div>', html=True)
        self.assertContains(response, "09:00")
        self.assertContains(response, "Cirurgia em andamento")
        self.assertContains(response, "Leito de UTI")
        self.assertContains(response, "P1")
        self.assertContains(response, "Nova atualização em")
        self.assertContains(response, "Sala sem cirurgia enviada ao painel", count=8)
        self.assertContains(response, "Cirurgia iniciada")

    def test_alterna_atendimento_com_auditoria(self):
        self.client.post(reverse("centrocirurgico:necessidade_alternar_atendimento", args=[self.necessidade.pk]))
        self.necessidade.refresh_from_db()
        self.assertTrue(self.necessidade.atendida)
        self.assertEqual(self.necessidade.atendida_por, self.user)
        self.assertIsNotNone(self.necessidade.atendida_em)

    def test_sala_liberada_retira_cirurgia_do_painel(self):
        giro = GiroSala.objects.get(cirurgia=self.programacao.cirurgia)
        giro.dataSalaLiberada = "2026-09-11T12:00:00Z"
        giro.save()
        response = self.client.get(reverse("centrocirurgico:painel_programador"))
        self.programacao.refresh_from_db()
        self.assertNotContains(response, "Paciente Painel")
        self.assertEqual(self.programacao.status, ProgramacaoCirurgia.FINALIZADA)
