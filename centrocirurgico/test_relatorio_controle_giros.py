from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cirurgia, GiroSala, Paciente


class RelatorioControleGirosTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="relatorio_giros",
            password="teste",
        )
        self.client.force_login(self.user)
        self.hoje = timezone.localdate()

    def _momento(self, hora, minuto=0):
        valor = datetime.combine(self.hoje, time(hora, minuto))
        return timezone.make_aware(valor, timezone.get_current_timezone())

    def _giro(self, numero, inicio=None, final=None):
        paciente = Paciente.objects.create(
            nome=f"Paciente {numero}",
            prontuario=str(1000 + numero),
        )
        cirurgia = Cirurgia.objects.create(
            paciente=paciente,
            procedimento=f"Cirurgia {numero}",
            sala=f"SALA {numero}",
            data=self.hoje,
            hora=time(7 + numero),
        )
        return GiroSala.objects.create(
            paciente=paciente,
            cirurgia=cirurgia,
            dataInicioCirurgia=inicio,
            dataFinalCirurgia=final,
        )

    def test_periodo_padrao_e_mes_corrente_ate_hoje(self):
        response = self.client.get(
            reverse("centrocirurgico:relatorio_controle_giros")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["data_inicio"],
            self.hoje.replace(day=1),
        )
        self.assertEqual(response.context["data_fim"], self.hoje)

    def test_distribui_inicio_e_finalizacao_por_turno(self):
        self._giro(1, self._momento(8), self._momento(10))
        self._giro(2, self._momento(13), self._momento(17, 59))
        self._giro(3, self._momento(18), self._momento(22))
        self._giro(4, None, None)

        response = self.client.get(
            reverse("centrocirurgico:relatorio_controle_giros")
        )

        linha = response.context["linhas"][0]
        self.assertEqual(linha["total"], 4)
        self.assertEqual(linha["inicio_manha"], 1)
        self.assertEqual(linha["inicio_tarde"], 1)
        self.assertEqual(linha["inicio_noite"], 1)
        self.assertEqual(linha["final_manha"], 1)
        self.assertEqual(linha["final_tarde"], 1)
        self.assertEqual(linha["final_noite"], 1)
        self.assertEqual(response.context["totais"]["iniciadas"], 3)
        self.assertEqual(response.context["totais"]["finalizadas"], 3)

    def test_filtro_de_datas_restringe_as_cirurgias(self):
        self._giro(1, self._momento(8), self._momento(10))
        paciente = Paciente.objects.create(nome="Paciente fora", prontuario="2000")
        cirurgia = Cirurgia.objects.create(
            paciente=paciente,
            procedimento="Cirurgia fora",
            data=self.hoje - timedelta(days=40),
            hora=time(8),
        )
        GiroSala.objects.create(paciente=paciente, cirurgia=cirurgia)

        response = self.client.get(
            reverse("centrocirurgico:relatorio_controle_giros"),
            {
                "data_inicio": self.hoje.isoformat(),
                "data_fim": self.hoje.isoformat(),
            },
        )

        self.assertEqual(response.context["totais"]["total"], 1)
        self.assertEqual(len(response.context["linhas"]), 1)
