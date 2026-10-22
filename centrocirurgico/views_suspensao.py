from datetime import date, time
from urllib.parse import urlencode

from django.contrib import messages
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from .forms_suspensao import (
    MotivoSuspensaoForm,
    SuspensaoCirurgiaForm,
    TipoSuspensaoForm,
)
from .models import (
    Cirurgia,
    MotivoSuspensao,
    Paciente,
    ProgramacaoCirurgia,
    SuspensaoCirurgia,
    TipoSuspensao,
)


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
    tipo_id = request.POST.get("motivo-tipo")
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



def _renderizar_suspensao(request, cirurgia, form, token_cirurgia, status=200):
    return render(
        request,
        "centrocirurgico/suspensoes/nova.html",
        {
            "cirurgia": cirurgia,
            "paciente": cirurgia.paciente,
            "form": form,
            "token_cirurgia": token_cirurgia,
        },
        status=status,
    )


@login_required
@permission_required("centrocirurgico.add_suspensaocirurgia", raise_exception=True)
@require_POST
@transaction.atomic
def suspensao_nova(request):
    token_mapa = request.POST.get("mapa_token")
    token_cirurgia = request.POST.get("cirurgia_token")

    if token_mapa:
        try:
            dados = signing.loads(
                token_mapa,
                salt="centrocirurgico.suspensao.mapa",
                max_age=3600,
            )
        except (BadSignature, SignatureExpired):
            return HttpResponseBadRequest(
                "Os dados do Mapa Cirúrgico expiraram ou foram alterados. "
                "Atualize o mapa e tente novamente."
            )

        prontuario = (dados.get("prontuario") or "").strip()
        nome = (dados.get("nome") or "").strip()
        if not prontuario or not nome or not dados.get("data_cirurgia"):
            return HttpResponseBadRequest("Dados obrigatórios da cirurgia não informados.")

        nascimento = (
            date.fromisoformat(dados["data_nascimento"])
            if dados.get("data_nascimento")
            else None
        )
        data_cirurgia = date.fromisoformat(dados["data_cirurgia"])
        hora_cirurgia = (
            time.fromisoformat(dados["hora_cirurgia"])
            if dados.get("hora_cirurgia")
            else None
        )

        paciente, _ = Paciente.objects.get_or_create(
            prontuario=prontuario,
            defaults={"nome": nome, "nascimento": nascimento},
        )
        atualizacoes = []
        if paciente.nome != nome:
            paciente.nome = nome
            atualizacoes.append("nome")
        if nascimento and paciente.nascimento != nascimento:
            paciente.nascimento = nascimento
            atualizacoes.append("nascimento")
        if atualizacoes:
            paciente.save(update_fields=atualizacoes)

        cirurgia, _ = Cirurgia.objects.get_or_create(
            paciente=paciente,
            especialidade=dados.get("especialidade") or "",
            procedimento=dados.get("procedimento") or "",
            medico=dados.get("medico") or "",
            sala=dados.get("sala") or "",
            data=data_cirurgia,
            hora=hora_cirurgia,
        )

        if SuspensaoCirurgia.objects.filter(cirurgia=cirurgia).exists():
            messages.warning(request, "Esta cirurgia já possui uma suspensão registrada.")
            return redirect("centrocirurgico:mapa_cirurgico_list")

        token_cirurgia = signing.dumps(
            {"cirurgia_id": cirurgia.id},
            salt="centrocirurgico.suspensao.cirurgia",
        )
        return _renderizar_suspensao(
            request,
            cirurgia,
            SuspensaoCirurgiaForm(),
            token_cirurgia,
        )

    if not token_cirurgia:
        return HttpResponseBadRequest("Identificação da cirurgia não informada.")

    try:
        dados_token = signing.loads(
            token_cirurgia,
            salt="centrocirurgico.suspensao.cirurgia",
            max_age=3600,
        )
    except (BadSignature, SignatureExpired):
        return HttpResponseBadRequest(
            "A confirmação da suspensão expirou ou foi alterada. "
            "Retorne ao Mapa Cirúrgico."
        )

    cirurgia = get_object_or_404(
        Cirurgia.objects.select_related("paciente"),
        pk=dados_token.get("cirurgia_id"),
    )
    if SuspensaoCirurgia.objects.filter(cirurgia=cirurgia).exists():
        messages.warning(request, "Esta cirurgia já possui uma suspensão registrada.")
        return redirect("centrocirurgico:mapa_cirurgico_list")

    form = SuspensaoCirurgiaForm(request.POST)
    if form.is_valid():
        suspensao = form.save(commit=False)
        suspensao.cirurgia = cirurgia
        suspensao.registrado_por = request.user
        suspensao.full_clean()
        suspensao.save()
        ProgramacaoCirurgia.objects.filter(
            cirurgia=cirurgia,
            status=ProgramacaoCirurgia.ENVIADA,
        ).update(
            status=ProgramacaoCirurgia.RASCUNHO,
            enviado_em=None,
            atualizado_por=request.user,
            atualizado_em=timezone.now(),
        )
        messages.success(request, "Suspensão da cirurgia registrada com sucesso.")
        return redirect("centrocirurgico:mapa_cirurgico_list")

    messages.error(request, "Revise os dados da suspensão.")
    return _renderizar_suspensao(
        request,
        cirurgia,
        form,
        token_cirurgia,
        status=400,
    )


@login_required
@require_GET
def motivos_ativos_por_tipo(request, tipo_id):
    permissoes = (
        "centrocirurgico.add_suspensaocirurgia",
        "centrocirurgico.view_suspensaocirurgia",
        "centrocirurgico.change_suspensaocirurgia",
    )
    if not any(request.user.has_perm(permissao) for permissao in permissoes):
        raise PermissionDenied

    motivos = MotivoSuspensao.objects.filter(
        tipo_id=tipo_id,
        tipo__ativo=True,
        ativo=True,
    ).values("id", "nome")
    return JsonResponse({"motivos": list(motivos)})



@login_required
@permission_required("centrocirurgico.view_suspensaocirurgia", raise_exception=True)
@require_GET
def suspensoes_lista(request):
    hoje = timezone.localdate()
    inicio_padrao = hoje.replace(day=1)
    data_inicio = request.GET.get("data_inicio") or inicio_padrao.isoformat()
    data_fim = request.GET.get("data_fim") or hoje.isoformat()
    busca = request.GET.get("q", "").strip()
    tipo_id = request.GET.get("tipo")
    motivo_id = request.GET.get("motivo")
    especialidade = request.GET.get("especialidade", "").strip()
    sala = request.GET.get("sala", "").strip()

    suspensoes = SuspensaoCirurgia.objects.select_related(
        "cirurgia__paciente",
        "tipo",
        "motivo",
        "registrado_por",
        "atualizado_por",
    )

    try:
        inicio = date.fromisoformat(data_inicio)
        suspensoes = suspensoes.filter(cirurgia__data__gte=inicio)
    except ValueError:
        data_inicio = ""
    try:
        fim = date.fromisoformat(data_fim)
        suspensoes = suspensoes.filter(cirurgia__data__lte=fim)
    except ValueError:
        data_fim = ""

    if busca:
        suspensoes = suspensoes.filter(
            Q(cirurgia__paciente__nome__icontains=busca)
            | Q(cirurgia__paciente__prontuario__icontains=busca)
            | Q(cirurgia__procedimento__icontains=busca)
        )
    if tipo_id:
        suspensoes = suspensoes.filter(tipo_id=tipo_id)
    if motivo_id:
        suspensoes = suspensoes.filter(motivo_id=motivo_id)
    if especialidade:
        suspensoes = suspensoes.filter(
            cirurgia__especialidade__icontains=especialidade
        )
    if sala:
        suspensoes = suspensoes.filter(cirurgia__sala__icontains=sala)

    total_periodo = suspensoes.count()
    suspensoes_hoje = suspensoes.filter(cirurgia__data=hoje).count()
    distribuicao_tipos = list(
        suspensoes.values("tipo__nome")
        .annotate(total=Count("id"))
        .order_by("-total", "tipo__nome")[:5]
    )
    pagina = Paginator(suspensoes.order_by("-cirurgia__data", "-registrado_em"), 15)
    page_obj = pagina.get_page(request.GET.get("page"))

    return render(
        request,
        "centrocirurgico/suspensoes/lista.html",
        {
            "page_obj": page_obj,
            "total_periodo": total_periodo,
            "suspensoes_hoje": suspensoes_hoje,
            "distribuicao_tipos": distribuicao_tipos,
            "tipos": TipoSuspensao.objects.all(),
            "motivos": MotivoSuspensao.objects.filter(tipo_id=tipo_id)
            if tipo_id
            else MotivoSuspensao.objects.none(),
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "busca": busca,
            "tipo_id": str(tipo_id or ""),
            "motivo_id": str(motivo_id or ""),
            "especialidade": especialidade,
            "sala": sala,
        },
    )


@login_required
@permission_required("centrocirurgico.view_suspensaocirurgia", raise_exception=True)
@require_GET
def suspensao_detalhe(request, pk):
    suspensao = get_object_or_404(
        SuspensaoCirurgia.objects.select_related(
            "cirurgia__paciente",
            "tipo",
            "motivo",
            "registrado_por",
            "atualizado_por",
        ),
        pk=pk,
    )
    return render(
        request,
        "centrocirurgico/suspensoes/detalhe.html",
        {"suspensao": suspensao},
    )


@login_required
@permission_required("centrocirurgico.change_suspensaocirurgia", raise_exception=True)
def suspensao_editar(request, pk):
    suspensao = get_object_or_404(
        SuspensaoCirurgia.objects.select_related("cirurgia__paciente"),
        pk=pk,
    )
    form = SuspensaoCirurgiaForm(
        request.POST or None,
        instance=suspensao,
    )
    if request.method == "POST" and form.is_valid():
        registro = form.save(commit=False)
        registro.atualizado_por = request.user
        registro.atualizado_em = timezone.now()
        registro.full_clean()
        registro.save()
        messages.success(request, "Suspensão atualizada com sucesso.")
        return redirect("centrocirurgico:suspensao_detalhe", pk=registro.pk)

    return render(
        request,
        "centrocirurgico/suspensoes/editar.html",
        {"suspensao": suspensao, "form": form},
        status=400 if request.method == "POST" else 200,
    )
