from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms_suspensao import MotivoSuspensaoForm, TipoSuspensaoForm
from .models import MotivoSuspensao, TipoSuspensao


def _config_url(tipo_id=None, **params):
    query = {}
    if tipo_id:
        query["tipo"] = tipo_id
    query.update({key: value for key, value in params.items() if value})
    url = "/centrocirurgico/suspensoes/configuracoes/"
    return f"{url}?{urlencode(query)}" if query else url


def _filtrar_status(queryset, status):
    if status == "ativos":
        return queryset.filter(ativo=True)
    if status == "inativos":
        return queryset.filter(ativo=False)
    return queryset


@login_required
@permission_required(
    (
        "centrocirurgico.view_tiposuspensao",
        "centrocirurgico.view_motivosuspensao",
    ),
    raise_exception=True,
)
@require_GET
def configuracoes_suspensao(request):
    busca = request.GET.get("q", "").strip()
    status = request.GET.get("status", "ativos")
    tipos = _filtrar_status(TipoSuspensao.objects.all(), status)
    if busca:
        tipos = tipos.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))

    tipo_selecionado = None
    tipo_id = request.GET.get("tipo")
    if tipo_id:
        tipo_selecionado = get_object_or_404(TipoSuspensao, pk=tipo_id)
    elif tipos.exists():
        tipo_selecionado = tipos.first()

    motivos = MotivoSuspensao.objects.none()
    if tipo_selecionado:
        motivos = _filtrar_status(tipo_selecionado.motivos.all(), status)
        if busca:
            motivos = motivos.filter(
                Q(nome__icontains=busca) | Q(descricao__icontains=busca)
            )

    tipo_edicao = None
    motivo_edicao = None
    if request.GET.get("editar_tipo"):
        tipo_edicao = get_object_or_404(
            TipoSuspensao, pk=request.GET["editar_tipo"]
        )
    if request.GET.get("editar_motivo"):
        motivo_edicao = get_object_or_404(
            MotivoSuspensao, pk=request.GET["editar_motivo"]
        )

    tipo_form = TipoSuspensaoForm(instance=tipo_edicao, prefix="tipo")
    motivo_form = MotivoSuspensaoForm(
        instance=motivo_edicao,
        initial={"tipo": tipo_selecionado},
        prefix="motivo",
    )

    return render(
        request,
        "centrocirurgico/suspensoes/configuracoes.html",
        {
            "tipos": tipos,
            "motivos": motivos,
            "tipo_selecionado": tipo_selecionado,
            "tipo_form": tipo_form,
            "motivo_form": motivo_form,
            "tipo_edicao": tipo_edicao,
            "motivo_edicao": motivo_edicao,
            "busca": busca,
            "status": status,
        },
    )


@login_required
@require_POST
def tipo_salvar(request):
    pk = request.POST.get("id")
    permission = (
        "centrocirurgico.change_tiposuspensao"
        if pk
        else "centrocirurgico.add_tiposuspensao"
    )
    if not request.user.has_perm(permission):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    instance = get_object_or_404(TipoSuspensao, pk=pk) if pk else None
    form = TipoSuspensaoForm(request.POST, instance=instance, prefix="tipo")
    if form.is_valid():
        tipo = form.save()
        messages.success(request, "Tipo de suspensão salvo com sucesso.")
        return redirect(_config_url(tipo.id))

    messages.error(request, "Revise os dados do tipo de suspensão.")
    return render(
        request,
        "centrocirurgico/suspensoes/configuracoes.html",
        {
            "tipos": TipoSuspensao.objects.all(),
            "motivos": instance.motivos.all() if instance else MotivoSuspensao.objects.none(),
            "tipo_selecionado": instance,
            "tipo_form": form,
            "motivo_form": MotivoSuspensaoForm(initial={"tipo": instance}, prefix="motivo"),
            "tipo_edicao": instance,
            "status": "todos",
        },
        status=400,
    )


@login_required
@require_POST
def motivo_salvar(request):
    pk = request.POST.get("id")
    permission = (
        "centrocirurgico.change_motivosuspensao"
        if pk
        else "centrocirurgico.add_motivosuspensao"
    )
    if not request.user.has_perm(permission):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    instance = get_object_or_404(MotivoSuspensao, pk=pk) if pk else None
    form = MotivoSuspensaoForm(request.POST, instance=instance, prefix="motivo")
    tipo_id = request.POST.get("tipo")
    if form.is_valid():
        motivo = form.save()
        messages.success(request, "Motivo de suspensão salvo com sucesso.")
        return redirect(_config_url(motivo.tipo_id))

    messages.error(request, "Revise os dados do motivo de suspensão.")
    tipo = TipoSuspensao.objects.filter(pk=tipo_id).first()
    return render(
        request,
        "centrocirurgico/suspensoes/configuracoes.html",
        {
            "tipos": TipoSuspensao.objects.all(),
            "motivos": tipo.motivos.all() if tipo else MotivoSuspensao.objects.none(),
            "tipo_selecionado": tipo,
            "tipo_form": TipoSuspensaoForm(prefix="tipo"),
            "motivo_form": form,
            "motivo_edicao": instance,
            "status": "todos",
        },
        status=400,
    )


@login_required
@permission_required("centrocirurgico.change_tiposuspensao", raise_exception=True)
@require_POST
@transaction.atomic
def tipo_alternar(request, pk):
    tipo = get_object_or_404(TipoSuspensao.objects.select_for_update(), pk=pk)
    tipo.ativo = not tipo.ativo
    tipo.save(update_fields=("ativo", "atualizado_em"))
    if not tipo.ativo:
        tipo.motivos.filter(ativo=True).update(ativo=False)
        messages.info(request, "Tipo e seus motivos foram desativados.")
    else:
        messages.success(request, "Tipo ativado. Os motivos permanecem desativados.")
    return redirect(_config_url(tipo.id, status="todos"))


@login_required
@permission_required("centrocirurgico.change_motivosuspensao", raise_exception=True)
@require_POST
def motivo_alternar(request, pk):
    motivo = get_object_or_404(MotivoSuspensao, pk=pk)
    if not motivo.ativo and not motivo.tipo.ativo:
        messages.error(request, "Ative o tipo antes de ativar este motivo.")
        return redirect(_config_url(motivo.tipo_id, status="todos"))
    motivo.ativo = not motivo.ativo
    motivo.save(update_fields=("ativo", "atualizado_em"))
    messages.success(request, "Situação do motivo atualizada.")
    return redirect(_config_url(motivo.tipo_id, status="todos"))


@login_required
@permission_required("centrocirurgico.delete_tiposuspensao", raise_exception=True)
@require_POST
def tipo_excluir(request, pk):
    tipo = get_object_or_404(TipoSuspensao, pk=pk)
    try:
        tipo.delete()
        messages.success(request, "Tipo de suspensão excluído.")
    except ProtectedError:
        messages.error(
            request,
            "Este tipo possui motivos ou utilizações e não pode ser excluído. Desative-o.",
        )
    return redirect(_config_url(status="todos"))


@login_required
@permission_required("centrocirurgico.delete_motivosuspensao", raise_exception=True)
@require_POST
def motivo_excluir(request, pk):
    motivo = get_object_or_404(MotivoSuspensao, pk=pk)
    tipo_id = motivo.tipo_id
    try:
        motivo.delete()
        messages.success(request, "Motivo de suspensão excluído.")
    except ProtectedError:
        messages.error(
            request,
            "Este motivo já foi utilizado e não pode ser excluído. Desative-o.",
        )
    return redirect(_config_url(tipo_id, status="todos"))
