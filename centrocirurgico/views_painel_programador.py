from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import GiroSala, ProgramacaoCirurgia


def etapa_giro(giro):
    if not giro:
        return "Aguardando registro no Giro", "secondary"
    etapas = (
        ("dataSalaLiberada", "Sala liberada", "success"),
        ("dataFinalLimpeza", "Limpeza concluída", "info"),
        ("dataInicioLimpeza", "Limpeza em andamento", "info"),
        ("dataFinalDesmontagemSala", "Desmontagem concluída", "warning"),
        ("dataInicioDesmontagemSala", "Desmontagem em andamento", "warning"),
        ("dataSaidaSala", "Paciente saiu da sala", "primary"),
        ("dataFinalCirurgia", "Cirurgia finalizada", "primary"),
        ("dataInicioCirurgia", "Cirurgia em andamento", "danger"),
    )
    for campo, descricao, cor in etapas:
        if getattr(giro, campo):
            return descricao, cor
    return "Aguardando início da cirurgia", "secondary"


@login_required
@permission_required("centrocirurgico.view_programacaocirurgia", raise_exception=True)
@require_GET
def painel_programador(request):
    programacoes = list(
        ProgramacaoCirurgia.objects.filter(status=ProgramacaoCirurgia.ENVIADA)
        .select_related("cirurgia__paciente")
        .prefetch_related("necessidades__necessidade")
        .order_by("sala_painel", "hora_painel")
    )
    giros = {
        giro.cirurgia_id: giro
        for giro in GiroSala.objects.filter(
            cirurgia_id__in=[item.cirurgia_id for item in programacoes]
        ).order_by("cirurgia_id", "pk")
    }
    exibidas = []
    for programacao in programacoes:
        giro = giros.get(programacao.cirurgia_id)
        if giro and giro.dataSalaLiberada:
            programacao.status = ProgramacaoCirurgia.FINALIZADA
            programacao.atualizado_em = timezone.now()
            programacao.save(update_fields=("status", "atualizado_em"))
            continue
        programacao.etapa_giro, programacao.etapa_cor = etapa_giro(giro)
        if giro and giro.dataFinalCirurgia:
            programacao.status_painel = "Cirurgia finalizada"
            programacao.status_classe = "status-finalizada"
        elif giro and giro.dataInicioCirurgia:
            programacao.status_painel = "Cirurgia iniciada"
            programacao.status_classe = "status-iniciada"
        else:
            programacao.status_painel = "Sala sendo preparada"
            programacao.status_classe = "status-preparacao"
        exibidas.append(programacao)
    por_sala = {item.sala_painel: item for item in exibidas}
    salas = [
        {"numero": str(numero), "rotulo": f"{numero:02d}", "programacao": por_sala.get(str(numero))}
        for numero in range(1, 10)
    ]
    return render(request, "centrocirurgico/programador/painel.html", {
        "programacoes": exibidas,
        "salas": salas,
        "atualizado_em": timezone.localtime(),
        "intervalo_atualizacao": 60,
    })
