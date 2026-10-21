import calendar
from datetime import datetime, time, timedelta
from unittest.mock import patch

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
        patcher = patch(
            "centrocirurgico.views_relatorio_giros.buscar_mapa_cirurgico_aghu",
            return_value=[],
        )
        self.buscar_aghu = patcher.start()
        self.addCleanup(patcher.stop)

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
            dataInicioAnestesia=inicio,
            dataInicioCirurgia=inicio,
            dataFinalCirurgia=final,
        )

    def test_periodo_padrao_e_mes_corrente_completo(self):
        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["data_inicio"], self.hoje.replace(day=1))
        self.assertEqual(
            response.context["data_fim"],
            self.hoje.replace(
                day=calendar.monthrange(self.hoje.year, self.hoje.month)[1]
            ),
        )
        self.buscar_aghu.assert_called_once_with(
            data_inicio=response.context["data_inicio"],
            data_fim=response.context["data_fim"],
        )

    def test_distribui_inicio_e_finalizacao_por_turno(self):
        self._giro(1, self._momento(12, 59), self._momento(12, 59))
        self._giro(2, self._momento(13), self._momento(18, 59))
        self._giro(3, self._momento(19), self._momento(22))
        self._giro(4, None, None)

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros"))

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

    def test_resume_aghu_e_detalha_horarios_do_aghu_e_do_giro(self):
        giro = self._giro(1, self._momento(8), self._momento(10))
        inicio_aghu = self._momento(8, 5)
        fim_aghu = self._momento(9, 55)
        self.buscar_aghu.return_value = [
            {
                "data": self.hoje,
                "sala": "SALA 1",
                "prontuario": "1001",
                "paciente": "Paciente 1",
                "procedimento": "Cirurgia 1",
                "situacao": "RZDA",
                "data_inicio_cirurgia": self._momento(8),
                "data_inicio_real_aghu": inicio_aghu,
                "data_fim_real_aghu": fim_aghu,
            },
            {
                "data": self.hoje,
                "sala": "SALA 2",
                "prontuario": "2002",
                "paciente": "Paciente cancelado",
                "procedimento": "Cirurgia cancelada",
                "situacao": "CANC",
                "data_inicio_cirurgia": self._momento(11),
                "data_inicio_real_aghu": None,
                "data_fim_real_aghu": None,
            },
        ]

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros"))

        linha = response.context["linhas"][0]
        self.assertEqual(linha["aghu_total"], 2)
        self.assertEqual(linha["aghu_realizadas"], 1)
        self.assertEqual(linha["aghu_canceladas"], 1)
        self.assertEqual(response.context["totais"]["aghu_realizadas"], 1)
        self.assertEqual(response.context["totais"]["aghu_canceladas"], 1)

        detalhe = response.context["detalhes"][0]["cirurgias"][0]
        self.assertEqual(detalhe["aghu_inicio"], inicio_aghu)
        self.assertEqual(detalhe["aghu_fim"], fim_aghu)
        self.assertEqual(detalhe["giro_inicio"], giro.dataInicioAnestesia)
        self.assertEqual(detalhe["giro_fim"], giro.dataFinalCirurgia)
        self.assertEqual(detalhe["giro"], giro)
        self.assertEqual(len(linha["cirurgias"]), 2)
        self.assertContains(response, "Detalhar")
        self.assertContains(response, "Cirurgias de")
        self.assertContains(response, "Ver giro")
        self.assertContains(response, "Giro registrado no sistema")
        self.assertContains(response, "Sem giro")

    def test_falha_do_aghu_nao_impede_relatorio_local(self):
        self._giro(1, self._momento(8), self._momento(10))
        self.buscar_aghu.side_effect = RuntimeError("AGHU indisponível")

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totais"]["total"], 1)
        self.assertContains(response, "Não foi possível consultar o AGHU agora")

    def test_reinclusao_fica_na_data_exibida_no_mapa_aghu(self):
        data_original = self.hoje
        data_reincluida = self.hoje + timedelta(days=1)
        paciente = Paciente.objects.create(nome="Paciente reagendado", prontuario="3001")
        cirurgia_nova = Cirurgia.objects.create(
            paciente=paciente,
            procedimento="Colecistectomia",
            data=data_reincluida,
            hora=time(10),
        )
        GiroSala.objects.create(
            paciente=paciente,
            cirurgia=cirurgia_nova,
            dataInicioAnestesia=self._momento(10),
            dataInicioCirurgia=self._momento(10, 30),
            dataFinalCirurgia=self._momento(12),
        )
        self.buscar_aghu.return_value = [
            {
                "data": data_reincluida,
                "prontuario": "3001",
                "nome_paciente": "Paciente reagendado",
                "procedimento": "Colecistectomia",
                "situacao": "RZDA",
                "data_inicio_cirurgia": datetime.combine(
                    data_original,
                    time(13, 30),
                ),
                "data_inicio_real_aghu": None,
                "data_fim_real_aghu": None,
            }
        ]

        response = self.client.get(reverse("centrocirurgico:relatorio_controle_giros"))

        linha_reincluida = next(
            linha for linha in response.context["linhas"]
            if linha["data"] == data_reincluida
        )
        reinclusao = linha_reincluida["cirurgias"][0]
        self.assertEqual(linha_reincluida["aghu_realizadas"], 1)
        self.assertEqual(reinclusao["giro"].cirurgia, cirurgia_nova)
        self.assertEqual(reinclusao["giro_inicio"], reinclusao["giro"].dataInicioAnestesia)

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
