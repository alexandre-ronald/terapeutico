from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cirurgia, GiroSala, Paciente


class SequenciaGiroSalaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador_giro",
            password="teste",
        )
        self.client.force_login(self.user)
        paciente = Paciente.objects.create(nome="Paciente Giro", prontuario="900")
        cirurgia = Cirurgia.objects.create(
            paciente=paciente,
            procedimento="Cirurgia Teste",
            sala="SALA 1",
            data=date.today(),
            hora=time(8),
        )
        self.giro = GiroSala.objects.create(paciente=paciente, cirurgia=cirurgia)

    def test_inicio_cirurgia_fica_bloqueado_antes_da_anestesia(self):
        response = self.client.get(
            reverse("centrocirurgico:inicio_cirurgia", args=[self.giro.pk])
        )

        self.giro.refresh_from_db()
        self.assertIsNone(self.giro.dataInicioCirurgia)
        self.assertContains(response, "Registre &#x27;Início da anestesia&#x27; antes desta etapa.")

    def test_anestesia_libera_inicio_da_cirurgia(self):
        self.client.get(
            reverse("centrocirurgico:inicio_anestesia", args=[self.giro.pk])
        )
        self.client.get(
            reverse("centrocirurgico:inicio_cirurgia", args=[self.giro.pk])
        )

        self.giro.refresh_from_db()
        self.assertIsNotNone(self.giro.dataInicioAnestesia)
        self.assertIsNotNone(self.giro.dataInicioCirurgia)
        self.assertLessEqual(
            self.giro.dataInicioAnestesia,
            self.giro.dataInicioCirurgia,
        )

    def test_registro_manual_rejeita_horario_anterior_a_anestesia(self):
        inicio_anestesia = timezone.make_aware(datetime(2026, 9, 14, 10, 0))
        self.giro.dataInicioAnestesia = inicio_anestesia
        self.giro.save(update_fields=("dataInicioAnestesia",))

        response = self.client.post(
            reverse("centrocirurgico:registrar_etapa_manual", args=[self.giro.pk]),
            {
                "etapa": "dataInicioCirurgia",
                "data_hora": "2026-09-14T09:59",
            },
        )

        self.giro.refresh_from_db()
        self.assertIsNone(self.giro.dataInicioCirurgia)
        self.assertContains(response, "O horário não pode ser anterior")

    def test_etapa_posterior_exige_todas_as_anteriores(self):
        response = self.client.get(
            reverse("centrocirurgico:fim_cirurgia", args=[self.giro.pk])
        )

        self.giro.refresh_from_db()
        self.assertIsNone(self.giro.dataFinalCirurgia)
        self.assertContains(response, "Registre &#x27;Início da anestesia&#x27; antes desta etapa.")

    def test_tela_bloqueia_inicio_da_cirurgia_ate_anestesia(self):
        response = self.client.get(
            reverse("centrocirurgico:inicio_anestesia", args=[self.giro.pk])
        )
        self.assertContains(response, "Início da cirurgia")

        novo_giro = GiroSala.objects.create(
            paciente=self.giro.paciente,
            cirurgia=Cirurgia.objects.create(
                paciente=self.giro.paciente,
                procedimento="Outra cirurgia",
                sala="SALA 2",
                data=date.today(),
                hora=time(10),
            ),
        )
        response = self.client.get(
            reverse("centrocirurgico:registrar_etapa_manual", args=[novo_giro.pk])
        )
        self.assertContains(response, "Registre primeiro o início da anestesia")


class IdentidadeCirurgiaGiroSalaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador_multiplas_cirurgias",
            password="teste",
        )
        self.client.force_login(self.user)
        self.paciente = Paciente.objects.create(
            nome="Paciente com retorno",
            prontuario="901",
        )
        cirurgia_antiga = Cirurgia.objects.create(
            paciente=self.paciente,
            procedimento="Cirurgia antiga",
            sala="SALA 1",
            data=date(2026, 8, 11),
            hora=time(8),
        )
        self.giro_antigo = GiroSala.objects.create(
            paciente=self.paciente,
            cirurgia=cirurgia_antiga,
            dataInicioAnestesia=timezone.make_aware(
                datetime(2026, 8, 11, 8, 0)
            ),
        )

    def test_nova_cirurgia_do_mesmo_paciente_cria_outro_giro(self):
        response = self.client.post(
            reverse("centrocirurgico:giro_sala_novo"),
            {
                "nome": self.paciente.nome,
                "prontuario": self.paciente.prontuario,
                "data_nascimento": "",
                "especialidade": "Cirurgia Geral",
                "procedimento": "Nova cirurgia",
                "data_cirurgia": "15/10/2026",
                "hora_cirurgia": "10:00:00",
                "medico": "Cirurgião Teste",
                "sala": "SALA 2",
            },
        )

        novo_giro = response.context["giro"]
        self.assertNotEqual(novo_giro.pk, self.giro_antigo.pk)
        self.assertNotEqual(
            novo_giro.cirurgia_id,
            self.giro_antigo.cirurgia_id,
        )
        self.assertEqual(novo_giro.cirurgia.data, date(2026, 10, 15))
        self.assertEqual(novo_giro.cirurgia.procedimento, "Nova cirurgia")
        self.assertIsNone(novo_giro.dataInicioAnestesia)
        self.assertEqual(
            GiroSala.objects.filter(paciente=self.paciente).count(),
            2,
        )
