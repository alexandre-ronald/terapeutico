from datetime import datetime
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms_programador import ProgramacaoCirurgiaForm
from .models import Cirurgia, GiroSala, NecessidadeCirurgica, Paciente, ProgramacaoCirurgia, ProgramacaoNecessidade
from .views import buscar_mapa_cirurgico_aghu

SALT = "centrocirurgico.programador.mapa"


def _texto(valor):
    return str(valor or "").strip()


def _normalizar_sala(valor):
    texto = _texto(valor)
    numeros = re.findall(r"(?<!\\d)([1-9])(?!\\d)", texto)
    return numeros[-1] if numeros else ""


def _token(dado):
    inicio = dado.get("data_inicio_cirurgia")
    return signing.dumps({
        "prontuario": _texto(dado.get("prontuario")), "nome": _texto(dado.get("nome_paciente")),
        "data_nascimento": dado.get("data_nascimento").strftime("%Y-%m-%d") if dado.get("data_nascimento") else "",
        "especialidade": _texto(dado.get("especialidade")), "procedimento": _texto(dado.get("procedimento")),
        "medico": _texto(dado.get("medico")), "sala": _texto(dado.get("sala")),
        "leito": _texto(dado.get("leito")),
        "data_cirurgia": inicio.strftime("%Y-%m-%d") if inicio else "", "hora_cirurgia": inicio.strftime("%H:%M:%S") if inicio else "",
    }, salt=SALT)


def _suspensao_token(dado):
    inicio = dado.get("data_inicio_cirurgia")
    return signing.dumps({
        "prontuario": _texto(dado.get("prontuario")), "nome": _texto(dado.get("nome_paciente")),
        "data_nascimento": dado.get("data_nascimento").strftime("%Y-%m-%d") if dado.get("data_nascimento") else "",
        "especialidade": _texto(dado.get("especialidade")), "procedimento": _texto(dado.get("procedimento")),
        "medico": _texto(dado.get("medico")), "sala": _texto(dado.get("sala")),
        "leito": _texto(dado.get("leito")),
        "data_cirurgia": inicio.strftime("%Y-%m-%d") if inicio else "", "hora_cirurgia": inicio.strftime("%H:%M:%S") if inicio else "",
    }, salt="centrocirurgico.suspensao.mapa")


def _dados_token(valor):
    try:
        return signing.loads(valor, salt=SALT, max_age=60 * 60 * 12)
    except (BadSignature, SignatureExpired):
        return None


def _obter_cirurgia(dados):
    nascimento = datetime.strptime(dados["data_nascimento"], "%Y-%m-%d").date() if dados.get("data_nascimento") else None
    data = datetime.strptime(dados["data_cirurgia"], "%Y-%m-%d").date()
    hora = datetime.strptime(dados["hora_cirurgia"], "%H:%M:%S").time() if dados.get("hora_cirurgia") else None
    paciente, _ = Paciente.objects.get_or_create(prontuario=dados["prontuario"], defaults={"nome": dados["nome"], "nascimento": nascimento})
    cirurgia, _ = Cirurgia.objects.get_or_create(
        paciente=paciente, data=data, hora=hora, sala=dados["sala"], procedimento=dados["procedimento"],
        defaults={"especialidade": dados["especialidade"], "medico": dados["medico"]},
    )
    return cirurgia


@login_required
@permission_required("centrocirurgico.view_programacaocirurgia", raise_exception=True)
def programador_mapa(request):
    data_mapa = request.GET.get("data_mapa")
    dados = buscar_mapa_cirurgico_aghu(data_mapa) if data_mapa else []
    for item in dados:
        item["programacao_token"] = _token(item)
        item["suspensao_token"] = _suspensao_token(item)
        inicio = item.get("data_inicio_cirurgia")
        item["ja_programada"] = ProgramacaoCirurgia.objects.filter(
            cirurgia__paciente__prontuario=_texto(item.get("prontuario")), cirurgia__data=inicio.date() if inicio else None,
            cirurgia__hora=inicio.time() if inicio else None, cirurgia__sala=_texto(item.get("sala")),
        ).first()
    return render(request, "centrocirurgico/programador/mapa.html", {"mapa": dados})


@login_required
@permission_required("centrocirurgico.add_programacaocirurgia", raise_exception=True)
@require_POST
def programacao_abrir(request):
    dados = _dados_token(request.POST.get("mapa_token", ""))
    if not dados:
        messages.error(request, "Os dados do Mapa Cirúrgico expiraram ou são inválidos. Consulte novamente.")
        return redirect("centrocirurgico:programador_mapa")
    cirurgia = _obter_cirurgia(dados)
    programacao, criada = ProgramacaoCirurgia.objects.get_or_create(
        cirurgia=cirurgia,
        defaults={
            "sala_painel": _normalizar_sala(cirurgia.sala),
            "hora_painel": cirurgia.hora,
            "leito_paciente": dados.get("leito", ""),
            "criado_por": request.user,
            "atualizado_por": request.user,
        },
    )
    if not criada and programacao.leito_paciente != dados.get("leito", ""):
        programacao.leito_paciente = dados.get("leito", "")
        programacao.atualizado_por = request.user
        programacao.save(update_fields=("leito_paciente", "atualizado_por", "atualizado_em"))
    return redirect("centrocirurgico:programacao_editar", pk=programacao.pk)


def _salvar_necessidades(request, programacao):
    selecionadas = set(request.POST.getlist("necessidades"))
    catalogo = NecessidadeCirurgica.objects.filter(pk__in=selecionadas)
    erros = []
    for necessidade in catalogo:
        complemento = _texto(request.POST.get(f"complemento_{necessidade.pk}"))
        if necessidade.complemento_obrigatorio and not complemento:
            erros.append(f"Informe o complemento de {necessidade.nome}.")
    if erros:
        return erros
    programacao.necessidades.exclude(necessidade_id__in=selecionadas).delete()
    for necessidade in catalogo:
        atendida = request.POST.get(f"atendida_{necessidade.pk}") == "1"
        vinculo, _ = ProgramacaoNecessidade.objects.get_or_create(
            programacao=programacao, necessidade=necessidade
        )
        vinculo.complemento = _texto(request.POST.get(f"complemento_{necessidade.pk}"))
        if vinculo.atendida != atendida:
            vinculo.atendida = atendida
            vinculo.atendida_por = request.user if atendida else None
            vinculo.atendida_em = timezone.now() if atendida else None
        vinculo.save()
    return []


@login_required
@permission_required("centrocirurgico.change_programacaocirurgia", raise_exception=True)
@require_http_methods(["GET", "POST"])
def programacao_editar(request, pk):
    programacao = get_object_or_404(ProgramacaoCirurgia.objects.select_related("cirurgia__paciente"), pk=pk)
    form = ProgramacaoCirurgiaForm(request.POST or None, instance=programacao)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            programacao = form.save(commit=False)
            programacao.atualizado_por = request.user
            programacao.save()
            erros = _salvar_necessidades(request, programacao)
            if erros:
                transaction.set_rollback(True)
                for erro in erros: messages.error(request, erro)
            else:
                messages.success(request, "Programação salva como rascunho.")
                return redirect("centrocirurgico:programacao_editar", pk=pk)
    vinculadas = {item.necessidade_id: item for item in programacao.necessidades.all()}
    necessidades = [(item, vinculadas.get(item.pk)) for item in NecessidadeCirurgica.objects.filter(ativo=True)]
    return render(request, "centrocirurgico/programador/formulario.html", {"programacao": programacao, "form": form, "necessidades": necessidades})


@login_required
@permission_required("centrocirurgico.change_programacaocirurgia", raise_exception=True)
@require_POST
@transaction.atomic
def programacao_enviar(request, pk):
    programacao = get_object_or_404(ProgramacaoCirurgia.objects.select_for_update().select_related("cirurgia"), pk=pk)
    pendentes = list(
        programacao.necessidades.filter(atendida=False)
        .values_list("necessidade__nome", flat=True)
    )
    if pendentes:
        messages.error(request, "Confirme todas as necessidades antes do envio: " + ", ".join(pendentes) + ".")
        return redirect("centrocirurgico:programacao_editar", pk=pk)
    sala = programacao.sala_painel
    ocupantes = ProgramacaoCirurgia.objects.select_for_update().filter(
        status=ProgramacaoCirurgia.ENVIADA,
        sala_painel=sala,
    ).exclude(pk=pk)
    bloqueio = None
    for atual in ocupantes.select_related("cirurgia__paciente"):
        giro = GiroSala.objects.filter(cirurgia=atual.cirurgia).first()
        if giro and giro.dataFinalCirurgia:
            atual.status = ProgramacaoCirurgia.FINALIZADA
            atual.save(update_fields=("status", "atualizado_em"))
        else:
            bloqueio = atual
            break
    if bloqueio:
        messages.error(request, f"A sala {sala} está ocupada pela cirurgia de {bloqueio.cirurgia.paciente.nome}. O envio foi bloqueado.")
        return redirect("centrocirurgico:programacao_editar", pk=pk)
    programacao.status = ProgramacaoCirurgia.ENVIADA
    programacao.enviado_em = timezone.now()
    programacao.atualizado_por = request.user
    programacao.save(update_fields=("status", "enviado_em", "atualizado_por", "atualizado_em"))
    messages.success(request, "Cirurgia enviada ao Painel Programador.")
    return redirect("centrocirurgico:programacao_editar", pk=pk)
