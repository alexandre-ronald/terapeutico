from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import (
    Cirurgia,
    MotivoSuspensao,
    Paciente,
    SuspensaoCirurgia,
    TipoSuspensao,
)


class ConsultaSuspensoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="consulta_suspensao",
            password="senha-segura-123",
        )
        cls.paciente = Paciente.objects.create(
            nome="Maria Teste",
            prontuario="98765",
        )
        cls.cirurgia = Cirurgia.objects.create(
            paciente=cls.paciente,
            especialidade="Ortopedia",
            procedimento="Procedimento A",
            medico="Médico",
            sala="SALA 02",
            data=date.today(),
            hora=time(9, 0),
        )
        cls.tipo = TipoSuspensao.objects.create(nome="Paciente")
        cls.motivo = MotivoSuspensao.objects.create(
            tipo=cls.tipo,
            nome="Não compareceu",
        )
        cls.suspensao = SuspensaoCirurgia.objects.create(
            cirurgia=cls.cirurgia,
            tipo=cls.tipo,
            motivo=cls.motivo,
            observacao="Original",
            registrado_por=cls.user,
        )

    def test_lista_exige_permissao(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("centrocirurgico:suspensoes_lista")
        )
        self.assertEqual(response.status_code, 403)

    def test_lista_filtra_por_prontuario(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_suspensaocirurgia")
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("centrocirurgico:suspensoes_lista"),
            {"q": "98765"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maria Teste")

    def test_edicao_preserva_auditoria_original(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_suspensaocirurgia")
        )
        self.client.force_login(self.user)
        registrado_em = self.suspensao.registrado_em

        response = self.client.post(
            reverse(
                "centrocirurgico:suspensao_editar",
                args=[self.suspensao.pk],
            ),
            {
                "tipo": self.tipo.id,
                "motivo": self.motivo.id,
                "observacao": "Observação alterada",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.suspensao.refresh_from_db()
        self.assertEqual(self.suspensao.registrado_por, self.user)
        self.assertEqual(self.suspensao.registrado_em, registrado_em)
        self.assertEqual(self.suspensao.atualizado_por, self.user)
        self.assertIsNotNone(self.suspensao.atualizado_em)
        self.assertEqual(self.suspensao.observacao, "Observação alterada")


    def test_usuario_de_consulta_pode_carregar_motivos_do_filtro(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_suspensaocirurgia")
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "centrocirurgico:motivos_ativos_por_tipo",
                args=[self.tipo.id],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["motivos"][0]["id"], self.motivo.id)
