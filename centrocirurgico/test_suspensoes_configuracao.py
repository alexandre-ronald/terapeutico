from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from .models import MotivoSuspensao, TipoSuspensao


class TipoMotivoSuspensaoModelTests(TestCase):
    def test_cria_tipo_e_motivo(self):
        tipo = TipoSuspensao.objects.create(nome="Paciente", ordem=2)
        motivo = MotivoSuspensao.objects.create(
            tipo=tipo,
            nome="Paciente não compareceu",
            ordem=1,
        )
        self.assertEqual(motivo.tipo, tipo)
        self.assertEqual(str(motivo), "Paciente - Paciente não compareceu")

    def test_tipo_nao_repete_nome_sem_diferenciar_caixa(self):
        TipoSuspensao.objects.create(nome="Paciente")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TipoSuspensao.objects.create(nome="paciente")

    def test_motivo_nao_repete_no_mesmo_tipo(self):
        tipo = TipoSuspensao.objects.create(nome="Materiais")
        MotivoSuspensao.objects.create(tipo=tipo, nome="Falta de OPME")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MotivoSuspensao.objects.create(tipo=tipo, nome="falta de opme")

    def test_motivo_pode_repetir_em_tipos_diferentes(self):
        primeiro = TipoSuspensao.objects.create(nome="Materiais")
        segundo = TipoSuspensao.objects.create(nome="Equipamentos")
        MotivoSuspensao.objects.create(tipo=primeiro, nome="Indisponível")
        MotivoSuspensao.objects.create(tipo=segundo, nome="Indisponível")
        self.assertEqual(MotivoSuspensao.objects.count(), 2)

    def test_motivo_ativo_nao_pode_pertencer_a_tipo_inativo(self):
        tipo = TipoSuspensao.objects.create(nome="Equipe", ativo=False)
        motivo = MotivoSuspensao(tipo=tipo, nome="Falta de anestesista", ativo=True)
        with self.assertRaises(ValidationError):
            motivo.full_clean()

    def test_tipo_com_motivo_nao_pode_ser_excluido(self):
        tipo = TipoSuspensao.objects.create(nome="Processos")
        MotivoSuspensao.objects.create(tipo=tipo, nome="Falha de programação")
        with self.assertRaises(ProtectedError):
            tipo.delete()

    def test_ordenacao(self):
        TipoSuspensao.objects.create(nome="Zeta", ordem=2)
        TipoSuspensao.objects.create(nome="Beta", ordem=1)
        TipoSuspensao.objects.create(nome="Alfa", ordem=1)
        self.assertEqual(
            list(TipoSuspensao.objects.values_list("nome", flat=True)),
            ["Alfa", "Beta", "Zeta"],
        )


class ConfiguracoesSuspensaoViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.user = cls.User.objects.create_user(
            username="configurador",
            password="senha-segura-123",
        )
        cls.url = reverse("centrocirurgico:configuracoes_suspensao")

    def test_anonimo_e_redirecionado_para_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("usuarios:login"), response.url)

    def test_usuario_sem_permissao_recebe_403(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_usuario_com_permissoes_visualiza_tela(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_tiposuspensao"),
            Permission.objects.get(codename="view_motivosuspensao"),
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tipos e Motivos de Suspensão")

    def test_criacao_de_tipo_exige_permissao(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("centrocirurgico:tipo_suspensao_salvar"),
            {
                "tipo-nome": "Paciente",
                "tipo-descricao": "",
                "tipo-ordem": 0,
                "tipo-ativo": "on",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_usuario_autorizado_cria_tipo(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="add_tiposuspensao")
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("centrocirurgico:tipo_suspensao_salvar"),
            {
                "tipo-nome": "Paciente",
                "tipo-descricao": "",
                "tipo-ordem": 0,
                "tipo-ativo": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TipoSuspensao.objects.filter(nome="Paciente").exists())

    def test_operacao_mutavel_nao_aceita_get(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("centrocirurgico:tipo_suspensao_salvar")
        )
        self.assertEqual(response.status_code, 405)

    def test_post_sem_csrf_e_rejeitado(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="add_tiposuspensao")
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            reverse("centrocirurgico:tipo_suspensao_salvar"),
            {
                "tipo-nome": "Paciente",
                "tipo-ordem": 0,
                "tipo-ativo": "on",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_desativar_tipo_desativa_motivos(self):
        tipo = TipoSuspensao.objects.create(nome="Equipe")
        motivo = MotivoSuspensao.objects.create(tipo=tipo, nome="Anestesista")
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_tiposuspensao")
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("centrocirurgico:tipo_suspensao_alternar", args=[tipo.pk])
        )
        self.assertEqual(response.status_code, 302)
        tipo.refresh_from_db()
        motivo.refresh_from_db()
        self.assertFalse(tipo.ativo)
        self.assertFalse(motivo.ativo)
