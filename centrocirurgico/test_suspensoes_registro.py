from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import signing
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Cirurgia,
    MotivoSuspensao,
    Paciente,
    SuspensaoCirurgia,
    TipoSuspensao,
)


class SuspensaoCirurgiaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="operador_suspensao",
            password="senha-segura-123",
        )
        cls.user.user_permissions.add(
            Permission.objects.get(codename="add_suspensaocirurgia")
        )
        cls.paciente = Paciente.objects.create(
            nome="Paciente Teste",
            prontuario="123456",
            nascimento=date(1980, 1, 2),
        )
        cls.cirurgia = Cirurgia.objects.create(
            paciente=cls.paciente,
            especialidade="Cirurgia Geral",
            procedimento="Procedimento Teste",
            medico="Médico Teste",
            sala="SALA 01",
            data=date(2026, 9, 11),
            hora=time(8, 30),
        )
        cls.tipo = TipoSuspensao.objects.create(nome="Paciente")
        cls.motivo = MotivoSuspensao.objects.create(
            tipo=cls.tipo,
            nome="Paciente não compareceu",
        )
        cls.url = reverse("centrocirurgico:suspensao_nova")

    def setUp(self):
        self.client.force_login(self.user)

    def _token_cirurgia(self):
        return signing.dumps(
            {"cirurgia_id": self.cirurgia.id},
            salt="centrocirurgico.suspensao.cirurgia",
        )

    def test_registra_um_unico_motivo_com_observacao_opcional(self):
        response = self.client.post(
            self.url,
            {
                "cirurgia_token": self._token_cirurgia(),
                "tipo": self.tipo.id,
                "motivo": self.motivo.id,
                "observacao": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        suspensao = SuspensaoCirurgia.objects.get()
        self.assertEqual(suspensao.cirurgia, self.cirurgia)
        self.assertEqual(suspensao.tipo, self.tipo)
        self.assertEqual(suspensao.motivo, self.motivo)
        self.assertEqual(suspensao.observacao, "")
        self.assertEqual(suspensao.registrado_por, self.user)

    def test_impede_suspensao_duplicada(self):
        SuspensaoCirurgia.objects.create(
            cirurgia=self.cirurgia,
            tipo=self.tipo,
            motivo=self.motivo,
            registrado_por=self.user,
        )
        response = self.client.post(
            self.url,
            {
                "cirurgia_token": self._token_cirurgia(),
                "tipo": self.tipo.id,
                "motivo": self.motivo.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SuspensaoCirurgia.objects.count(), 1)

    def test_rejeita_motivo_de_outro_tipo(self):
        outro_tipo = TipoSuspensao.objects.create(nome="Equipamentos")
        outro_motivo = MotivoSuspensao.objects.create(
            tipo=outro_tipo,
            nome="Equipamento indisponível",
        )
        response = self.client.post(
            self.url,
            {
                "cirurgia_token": self._token_cirurgia(),
                "tipo": self.tipo.id,
                "motivo": outro_motivo.id,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SuspensaoCirurgia.objects.exists())

    def test_rejeita_motivo_inativo(self):
        self.motivo.ativo = False
        self.motivo.save()
        response = self.client.post(
            self.url,
            {
                "cirurgia_token": self._token_cirurgia(),
                "tipo": self.tipo.id,
                "motivo": self.motivo.id,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SuspensaoCirurgia.objects.exists())

    def test_token_alterado_e_rejeitado(self):
        response = self.client.post(
            self.url,
            {
                "cirurgia_token": self._token_cirurgia() + "alterado",
                "tipo": self.tipo.id,
                "motivo": self.motivo.id,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_usuario_sem_permissao_recebe_403(self):
        outro = get_user_model().objects.create_user(
            username="sem_permissao",
            password="senha-segura-123",
        )
        self.client.force_login(outro)
        response = self.client.post(
            self.url,
            {"cirurgia_token": self._token_cirurgia()},
        )
        self.assertEqual(response.status_code, 403)

    def test_motivo_utilizado_fica_protegido_contra_exclusao(self):
        SuspensaoCirurgia.objects.create(
            cirurgia=self.cirurgia,
            tipo=self.tipo,
            motivo=self.motivo,
            registrado_por=self.user,
        )
        with self.assertRaises(ProtectedError):
            self.motivo.delete()

    def test_api_retorna_somente_motivos_ativos_do_tipo(self):
        MotivoSuspensao.objects.create(
            tipo=self.tipo,
            nome="Motivo inativo",
            ativo=False,
        )
        response = self.client.get(
            reverse(
                "centrocirurgico:motivos_ativos_por_tipo",
                args=[self.tipo.id],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["motivos"],
            [{"id": self.motivo.id, "nome": self.motivo.nome}],
        )
