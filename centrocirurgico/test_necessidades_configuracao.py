from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import NecessidadeCirurgica


class NecessidadeCirurgicaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="programador", password="teste")
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="centrocirurgico", content_type__model="necessidadecirurgica"))
        self.client.force_login(self.user)

    def test_cadastra_necessidade_com_complemento(self):
        response = self.client.post(reverse("centrocirurgico:necessidade_salvar"), {
            "nome": "Leito de UTI", "descricao": "Reserva pós-operatória",
            "dica_complemento": "P1", "complemento_obrigatorio": "on",
            "ordem": 1, "ativo": "on",
        })
        self.assertEqual(response.status_code, 302)
        item = NecessidadeCirurgica.objects.get()
        self.assertEqual(item.dica_complemento, "P1")
        self.assertTrue(item.complemento_obrigatorio)

    def test_impede_nome_duplicado_sem_diferenciar_caixa(self):
        NecessidadeCirurgica.objects.create(nome="Sangue")
        response = self.client.post(reverse("centrocirurgico:necessidade_salvar"), {"nome": "sangue", "ordem": 0, "ativo": "on"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(NecessidadeCirurgica.objects.count(), 1)

    def test_usuario_sem_permissao_nao_acessa(self):
        outro = get_user_model().objects.create_user(username="sem-permissao", password="teste")
        self.client.force_login(outro)
        response = self.client.get(reverse("centrocirurgico:necessidade_lista"))
        self.assertEqual(response.status_code, 403)
