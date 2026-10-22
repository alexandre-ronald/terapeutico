from datetime import date, datetime, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cirurgia, GiroSala, Paciente


class RelatorioControleGirosSemanalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="semanal", password="teste")
        self.client.force_login(self.user)
        patcher = patch(
            "centrocirurgico.views_relatorio_giros.buscar_mapa_cirurgico_aghu",
            return_value=[],
        )
        self.buscar_aghu = patcher.start()
        self.addCleanup(patcher.stop)

    def _momento(self, dia, hora, minuto=0):
        valor = datetime.combine(date(2026, 9, dia), time(hora, minuto))
        return timezone.make_aware(valor, timezone.get_current_timezone())

    def _giro(self, numero, dia, inicio, final):
        paciente = Paciente.objects.create(nome=f"Paciente {numero}", prontuario=str(numero))
        cirurgia = Cirurgia.objects.create(
            paciente=paciente, procedimento=f"Cirurgia {numero}",
            data=date(2026, 9, dia), hora=time(8),
        )
        return GiroSala.objects.create(
            paciente=paciente, cirurgia=cirurgia,
            dataInicioAnestesia=inicio, dataInicioCirurgia=inicio,
            dataFinalCirurgia=final,
        )

    def test_compara_aghu_e_giro_por_semana_turno_e_etapa(self):
        self._giro(1, 3, self._momento(3, 12, 59), self._momento(3, 13))
        self._giro(2, 15, self._momento(15, 19), self._momento(15, 21))
        self.buscar_aghu.return_value = [
            {"data": date(2026, 9, 3), "situacao": "RZDA", "data_inicio_cirurgia": self._momento(3, 8), "data_fim_real_aghu": self._momento(3, 18, 59)},
            {"data": date(2026, 9, 3), "situacao": "CANC", "atendimento_seq": 99, "data_inicio_cirurgia": self._momento(3, 10), "data_fim_real_aghu": None},
            {"data": date(2026, 9, 15), "situacao": "RZDA", "data_inicio_cirurgia": self._momento(15, 19), "data_fim_real_aghu": self._momento(15, 22)},
        ]

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros_semanal"), {"mes": "2026-09"})

        self.assertEqual(response.status_code, 200)
        semana_1 = response.context["semanas"][0]
        self.assertEqual(semana_1["inicio"]["manha"]["aghu"], 2)
        self.assertEqual(semana_1["inicio"]["manha"]["giro"], 1)
        self.assertEqual(semana_1["inicio"]["manha"]["percentual"], 50.0)
        self.assertEqual(semana_1["fim"]["tarde"]["aghu"], 1)
        self.assertEqual(semana_1["fim"]["tarde"]["giro"], 1)
        self.assertEqual(semana_1["fim"]["tarde"]["percentual"], 100.0)
        semana_3 = response.context["semanas"][2]
        self.assertEqual(semana_3["inicio"]["noite"]["aghu"], 1)
        self.assertEqual(semana_3["inicio"]["noite"]["giro"], 1)
        self.assertEqual(response.context["totais"]["inicio"]["manha"]["percentual"], 50.0)

    def test_outubro_2026_tem_cinco_semanas_domingo_a_sabado(self):
        response = self.client.get(
            reverse("centrocirurgico:relatorio_controle_giros_semanal"),
            {"mes": "2026-10"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [semana["periodo"] for semana in response.context["semanas"]],
            ["01 a 03", "04 a 10", "11 a 17", "18 a 24", "25 a 31"],
        )

    def test_mes_com_seis_semanas_nao_perde_dias(self):
        response = self.client.get(
            reverse("centrocirurgico:relatorio_controle_giros_semanal"),
            {"mes": "2026-08"},
        )
        self.assertEqual(
            [semana["periodo"] for semana in response.context["semanas"]],
            ["01 a 01", "02 a 08", "09 a 15", "16 a 22", "23 a 29", "30 a 31"],
        )

    def test_sem_denominador_mostra_percentual_vazio(self):
        self._giro(1, 8, self._momento(8, 13), self._momento(8, 15))

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros_semanal"), {"mes": "2026-09"})

        celula = response.context["semanas"][1]["inicio"]["tarde"]
        self.assertEqual(celula["giro"], 1)
        self.assertEqual(celula["aghu"], 0)
        self.assertIsNone(celula["percentual"])
        self.assertContains(response, "—")

    def test_mes_invalido_retorna_mes_atual_e_falha_aghu_nao_interrompe(self):
        self.buscar_aghu.side_effect = RuntimeError("indisponível")

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros_semanal"), {"mes": "invalido"})

        hoje = timezone.localdate()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["mes_referencia"], hoje.replace(day=1))
        self.assertContains(response, "Não foi possível consultar o AGHU agora")
