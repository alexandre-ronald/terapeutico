from datetime import date, time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from .models import Cirurgia, GiroSala, Paciente, ProgramacaoCirurgia


class ProgramadorCirurgiasTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="programador", password="teste")
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="centrocirurgico", content_type__model="programacaocirurgia"))
        self.client.force_login(self.user)
        self.p1 = Paciente.objects.create(nome="Paciente Um", prontuario="1")
        self.p2 = Paciente.objects.create(nome="Paciente Dois", prontuario="2")
        self.c1 = Cirurgia.objects.create(paciente=self.p1, procedimento="Cirurgia 1", sala="SALA 1", data=date.today(), hora=time(8))
        self.c2 = Cirurgia.objects.create(paciente=self.p2, procedimento="Cirurgia 2", sala="SALA 1", data=date.today(), hora=time(10))
        self.a = ProgramacaoCirurgia.objects.create(cirurgia=self.c1, criado_por=self.user, atualizado_por=self.user, status=ProgramacaoCirurgia.ENVIADA)
        self.b = ProgramacaoCirurgia.objects.create(cirurgia=self.c2, criado_por=self.user, atualizado_por=self.user)

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
