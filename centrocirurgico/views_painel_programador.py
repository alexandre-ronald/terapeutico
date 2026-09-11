from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import GiroSala, ProgramacaoCirurgia, ProgramacaoNecessidade


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
        exibidas.append(programacao)
    return render(request, "centrocirurgico/programador/painel.html", {
        "programacoes": exibidas,
        "atualizado_em": timezone.localtime(),
        "intervalo_atualizacao": 60,
    })


@login_required
@permission_required("centrocirurgico.change_programacaonecessidade", raise_exception=True)
@require_POST
@transaction.atomic
def necessidade_alternar_atendimento(request, pk):
    item = get_object_or_404(
        ProgramacaoNecessidade.objects.select_for_update().select_related("programacao"),
        pk=pk,
        programacao__status=ProgramacaoCirurgia.ENVIADA,
    )
    item.atendida = not item.atendida
    item.atendida_por = request.user if item.atendida else None
    item.atendida_em = timezone.now() if item.atendida else None
    item.save(update_fields=("atendida", "atendida_por", "atendida_em"))
    messages.success(request, "Necessidade marcada como atendida." if item.atendida else "Necessidade reaberta como pendente.")
    return redirect("centrocirurgico:painel_programador")
