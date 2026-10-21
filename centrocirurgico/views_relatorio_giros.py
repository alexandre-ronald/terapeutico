import calendar
from collections import defaultdict
from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone

from .models import GiroSala


FAIXAS = ("manha", "tarde", "noite")


def _data_filtro(valor, padrao):
    if not valor:
        return padrao
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return padrao


def _faixa_horaria(valor):
    if not valor:
        return None
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    hora = valor.hour
    if hora < 12:
        return "manha"
    if hora < 18:
        return "tarde"
    return "noite"


def _linha_vazia(data_cirurgia):
    return {
        "data": data_cirurgia,
        "total": 0,
        "inicio_manha": 0,
        "inicio_tarde": 0,
        "inicio_noite": 0,
        "final_manha": 0,
        "final_tarde": 0,
        "final_noite": 0,
    }


@login_required
def relatorio_controle_giros(request):
    hoje = timezone.localdate()
    inicio_padrao = hoje.replace(day=1)
    fim_padrao = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    data_inicio = _data_filtro(request.GET.get("data_inicio"), inicio_padrao)
    data_fim = _data_filtro(request.GET.get("data_fim"), fim_padrao)

    if data_inicio > data_fim:
        messages.error(request, "A data inicial não pode ser posterior à data final.")
        data_inicio, data_fim = data_fim, data_inicio

    registros = (
        GiroSala.objects
        .select_related("cirurgia")
        .filter(cirurgia__data__range=(data_inicio, data_fim))
        .order_by("cirurgia__data", "cirurgia_id", "pk")
    )

    # Um giro representa uma cirurgia. A deduplicação protege o relatório
    # contra registros antigos repetidos para a mesma cirurgia.
    giros_por_cirurgia = {}
    for giro in registros:
        giros_por_cirurgia.setdefault(giro.cirurgia_id, giro)

    por_dia = defaultdict(dict)
    for giro in giros_por_cirurgia.values():
        dia = giro.cirurgia.data
        linha = por_dia.setdefault(dia, _linha_vazia(dia))
        linha["total"] += 1

        faixa_inicio = _faixa_horaria(giro.dataInicioCirurgia)
        if faixa_inicio:
            linha[f"inicio_{faixa_inicio}"] += 1

        faixa_final = _faixa_horaria(giro.dataFinalCirurgia)
        if faixa_final:
            linha[f"final_{faixa_final}"] += 1

    linhas = [por_dia[dia] for dia in sorted(por_dia)]
    totais = _linha_vazia(None)
    for linha in linhas:
        for campo in (
            "total",
            "inicio_manha", "inicio_tarde", "inicio_noite",
            "final_manha", "final_tarde", "final_noite",
        ):
            totais[campo] += linha[campo]

    totais["iniciadas"] = sum(totais[f"inicio_{faixa}"] for faixa in FAIXAS)
    totais["finalizadas"] = sum(totais[f"final_{faixa}"] for faixa in FAIXAS)
    totais["dias"] = len(linhas)

    return render(
        request,
        "centrocirurgico/relatorios/controle_giros.html",
        {
            "linhas": linhas,
            "totais": totais,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )
