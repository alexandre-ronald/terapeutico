import calendar
from collections import defaultdict
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .models import GiroSala
from .views import buscar_mapa_cirurgico_aghu


FAIXAS = ("manha", "tarde", "noite")
SITUACOES_REALIZADAS = {"RZDA", "REALIZADA", "REALIZADO"}
SITUACOES_CANCELADAS = {"CANC", "CANCELADA", "CANCELADO"}


def _data_filtro(valor, padrao):
    if not valor:
        return padrao
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return padrao


def _data_aghu(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if valor:
        try:
            return date.fromisoformat(str(valor)[:10])
        except ValueError:
            pass
    return None


def _texto_normalizado(valor):
    return " ".join(str(valor or "").split()).casefold()


def _faixa_horaria(valor):
    if not valor:
        return None
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    hora = valor.hour
    if hora < 13:
        return "manha"
    if hora < 19:
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
        "aghu_total": 0,
        "aghu_realizadas": 0,
        "aghu_canceladas": 0,
    }


def _situacao_aghu(registro):
    return str(registro.get("situacao") or "").strip().upper()


def _rotulo_situacao(codigo):
    if codigo in SITUACOES_REALIZADAS:
        return "Realizada", "success"
    if codigo in SITUACOES_CANCELADAS:
        return "Cancelada", "danger"
    return codigo or "Não informada", "secondary"


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
        .select_related("cirurgia", "paciente", "cirurgia__paciente")
        .filter(cirurgia__data__range=(data_inicio, data_fim))
        .order_by("cirurgia__data", "cirurgia_id", "pk")
    )

    # Um giro representa uma cirurgia. A deduplicação protege o relatório
    # contra registros antigos repetidos para a mesma cirurgia.
    giros_por_cirurgia = {}
    for giro in registros:
        giros_por_cirurgia.setdefault(giro.cirurgia_id, giro)

    por_dia = defaultdict(dict)
    giros_por_chave = {}
    giros_por_prontuario_data = defaultdict(list)
    for giro in giros_por_cirurgia.values():
        dia = giro.cirurgia.data
        linha = por_dia.setdefault(dia, _linha_vazia(dia))
        linha["total"] += 1

        faixa_inicio = _faixa_horaria(giro.dataInicioAnestesia)
        if faixa_inicio:
            linha[f"inicio_{faixa_inicio}"] += 1

        faixa_final = _faixa_horaria(giro.dataFinalCirurgia)
        if faixa_final:
            linha[f"final_{faixa_final}"] += 1

        prontuario = _texto_normalizado(
            getattr(giro.paciente, "prontuario", None)
            or getattr(giro.cirurgia.paciente, "prontuario", None)
        )
        procedimento = _texto_normalizado(giro.cirurgia.procedimento)
        chave_base = (prontuario, dia)
        giros_por_prontuario_data[chave_base].append(giro)
        giros_por_chave[(prontuario, dia, procedimento)] = giro

    try:
        cirurgias_aghu = buscar_mapa_cirurgico_aghu(
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except Exception:
        cirurgias_aghu = []
        messages.warning(
            request,
            "Não foi possível consultar o AGHU agora. Os dados locais do Giro continuam disponíveis.",
        )

    realizacoes_posteriores = defaultdict(list)
    for cirurgia_aghu in cirurgias_aghu:
        if _situacao_aghu(cirurgia_aghu) not in SITUACOES_REALIZADAS:
            continue
        dia_realizacao = _data_aghu(cirurgia_aghu.get("data"))
        if not dia_realizacao:
            continue
        chave = (
            _texto_normalizado(cirurgia_aghu.get("prontuario")),
            _texto_normalizado(cirurgia_aghu.get("procedimento")),
        )
        realizacoes_posteriores[chave].append(dia_realizacao)

    detalhes_por_dia = defaultdict(list)
    for cirurgia_aghu in cirurgias_aghu:
        # A data do mapa é a referência operacional. A data/hora programada
        # pode pertencer a um agendamento anterior e permanece informativa.
        dia = _data_aghu(cirurgia_aghu.get("data"))
        if not dia:
            continue

        situacao = _situacao_aghu(cirurgia_aghu)
        chave_aghu = (
            _texto_normalizado(cirurgia_aghu.get("prontuario")),
            _texto_normalizado(cirurgia_aghu.get("procedimento")),
        )
        if situacao in SITUACOES_CANCELADAS and any(
            data_realizada > dia
            for data_realizada in realizacoes_posteriores.get(chave_aghu, [])
        ):
            # A visão mantém o cancelamento do agendamento original mesmo
            # quando a mesma cirurgia é reincluída e realizada depois. O
            # mapa operacional não o considera cancelamento efetivo.
            continue

        linha = por_dia.setdefault(dia, _linha_vazia(dia))
        linha["aghu_total"] += 1
        if situacao in SITUACOES_REALIZADAS:
            linha["aghu_realizadas"] += 1
        elif situacao in SITUACOES_CANCELADAS:
            linha["aghu_canceladas"] += 1

        prontuario = _texto_normalizado(cirurgia_aghu.get("prontuario"))
        procedimento = _texto_normalizado(cirurgia_aghu.get("procedimento"))
        giro = giros_por_chave.get((prontuario, dia, procedimento))
        if not giro:
            candidatos = giros_por_prontuario_data.get((prontuario, dia), [])
            if len(candidatos) == 1:
                giro = candidatos[0]

        rotulo_situacao, classe_situacao = _rotulo_situacao(situacao)
        detalhes_por_dia[dia].append(
            {
                "sala": cirurgia_aghu.get("sala"),
                "paciente": (
                    cirurgia_aghu.get("nome_paciente")
                    or cirurgia_aghu.get("paciente")
                ),
                "prontuario": cirurgia_aghu.get("prontuario"),
                "procedimento": cirurgia_aghu.get("procedimento"),
                "situacao": rotulo_situacao,
                "situacao_classe": classe_situacao,
                "aghu_prevista": cirurgia_aghu.get("data_inicio_cirurgia"),
                "aghu_inicio": cirurgia_aghu.get("data_inicio_real_aghu"),
                "aghu_fim": cirurgia_aghu.get("data_fim_real_aghu"),
                "giro_inicio": giro.dataInicioAnestesia if giro else None,
                "giro_fim": giro.dataFinalCirurgia if giro else None,
                "giro": giro,
            }
        )

    linhas = [por_dia[dia] for dia in sorted(por_dia)]
    for linha in linhas:
        linha["cirurgias"] = sorted(
            detalhes_por_dia.get(linha["data"], []),
            key=lambda item: (
                str(item["aghu_prevista"] or ""),
                str(item["sala"] or ""),
            ),
        )
    detalhes = [
        {
            "data": dia,
            "cirurgias": sorted(
                detalhes_por_dia[dia],
                key=lambda item: (
                    str(item["aghu_prevista"] or ""),
                    str(item["sala"] or ""),
                ),
            ),
        }
        for dia in sorted(detalhes_por_dia)
    ]

    totais = _linha_vazia(None)
    campos_totalizaveis = (
        "total",
        "inicio_manha", "inicio_tarde", "inicio_noite",
        "final_manha", "final_tarde", "final_noite",
        "aghu_total", "aghu_realizadas", "aghu_canceladas",
    )
    for linha in linhas:
        for campo in campos_totalizaveis:
            totais[campo] += linha[campo]

    totais["iniciadas"] = sum(totais[f"inicio_{faixa}"] for faixa in FAIXAS)
    totais["finalizadas"] = sum(totais[f"final_{faixa}"] for faixa in FAIXAS)
    totais["dias"] = len(linhas)

    return render(
        request,
        "centrocirurgico/relatorios/controle_giros.html",
        {
            "linhas": linhas,
            "detalhes": detalhes,
            "totais": totais,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )
