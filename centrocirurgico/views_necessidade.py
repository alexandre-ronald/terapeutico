from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms_necessidade import NecessidadeCirurgicaForm
from .models import NecessidadeCirurgica


def _url(**params):
    query = {key: value for key, value in params.items() if value}
    base = "/centrocirurgico/necessidades/"
    return f"{base}?{urlencode(query)}" if query else base


@login_required
@permission_required("centrocirurgico.view_necessidadecirurgica", raise_exception=True)
@require_GET
def necessidade_lista(request):
    busca = request.GET.get("q", "").strip()
    status = request.GET.get("status", "ativos")
    necessidades = NecessidadeCirurgica.objects.all()
    if status == "ativos":
        necessidades = necessidades.filter(ativo=True)
    elif status == "inativos":
        necessidades = necessidades.filter(ativo=False)
    if busca:
        necessidades = necessidades.filter(
            Q(nome__icontains=busca)
            | Q(descricao__icontains=busca)
            | Q(dica_complemento__icontains=busca)
        )
    edicao = None
    if request.GET.get("editar"):
        edicao = get_object_or_404(NecessidadeCirurgica, pk=request.GET["editar"])
    return render(request, "centrocirurgico/necessidades/lista.html", {
        "necessidades": necessidades,
        "form": NecessidadeCirurgicaForm(instance=edicao),
        "edicao": edicao,
        "busca": busca,
        "status": status,
    })


@login_required
@require_POST
def necessidade_salvar(request):
    pk = request.POST.get("id")
    permission = "centrocirurgico.change_necessidadecirurgica" if pk else "centrocirurgico.add_necessidadecirurgica"
    if not request.user.has_perm(permission):
        raise PermissionDenied
    instance = get_object_or_404(NecessidadeCirurgica, pk=pk) if pk else None
    form = NecessidadeCirurgicaForm(request.POST, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, "Necessidade salva com sucesso.")
        return redirect(_url(status="todos"))
    necessidades = NecessidadeCirurgica.objects.all()
    messages.error(request, "Revise os dados da necessidade.")
    return render(request, "centrocirurgico/necessidades/lista.html", {
        "necessidades": necessidades,
        "form": form,
        "edicao": instance,
        "status": "todos",
    }, status=400)


@login_required
@permission_required("centrocirurgico.change_necessidadecirurgica", raise_exception=True)
@require_POST
def necessidade_alternar(request, pk):
    necessidade = get_object_or_404(NecessidadeCirurgica, pk=pk)
    necessidade.ativo = not necessidade.ativo
    necessidade.save(update_fields=("ativo", "atualizado_em"))
    messages.success(request, "Situação da necessidade atualizada.")
    return redirect(_url(status="todos"))


@login_required
@permission_required("centrocirurgico.delete_necessidadecirurgica", raise_exception=True)
@require_POST
def necessidade_excluir(request, pk):
    necessidade = get_object_or_404(NecessidadeCirurgica, pk=pk)
    try:
        necessidade.delete()
        messages.success(request, "Necessidade excluída.")
    except ProtectedError:
        messages.error(request, "Esta necessidade já foi utilizada. Desative-a.")
    return redirect(_url(status="todos"))
