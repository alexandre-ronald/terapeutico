from datetime import datetime
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
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
    data_mapa = request.GET.get("data_mapa") or timezone.localdate().isoformat()
    dados = buscar_mapa_cirurgico_aghu(data_mapa)
    for item in dados:
        item["programacao_token"] = _token(item)
        item["suspensao_token"] = _suspensao_token(item)
        inicio = item.get("data_inicio_cirurgia")
        programacao = ProgramacaoCirurgia.objects.filter(
            cirurgia__paciente__prontuario=_texto(item.get("prontuario")), cirurgia__data=inicio.date() if inicio else None,
            cirurgia__hora=inicio.time() if inicio else None, cirurgia__sala=_texto(item.get("sala")),
        ).first()
        item["ja_programada"] = programacao
        leito = _texto(item.get("leito"))
        if programacao and leito and programacao.leito_paciente != leito:
            programacao.leito_paciente = leito
            programacao.atualizado_por = request.user
            programacao.save(update_fields=("leito_paciente", "atualizado_por", "atualizado_em"))
    programacoes_painel = (
        ProgramacaoCirurgia.objects.filter(status=ProgramacaoCirurgia.ENVIADA)
        .select_related("cirurgia__paciente")
        .order_by("sala_painel", "hora_painel", "cirurgia__paciente__nome")
    )
    return render(request, "centrocirurgico/programador/mapa.html", {
        "mapa": dados,
        "programacoes_painel": programacoes_painel,
        "salas_painel": range(1, 10),
        "data_mapa": data_mapa,
        "data_mapa_exibicao": datetime.strptime(data_mapa, "%Y-%m-%d").strftime("%d/%m/%Y"),
    })


@login_required
@permission_required("centrocirurgico.change_programacaocirurgia", raise_exception=True)
@require_POST
@transaction.atomic
def programacao_retirar_painel(request):
    acao = request.POST.get("acao")
    programacoes = ProgramacaoCirurgia.objects.select_for_update().filter(
        status=ProgramacaoCirurgia.ENVIADA
    )

    if acao == "sala":
        sala = request.POST.get("sala")
        if sala not in {str(numero) for numero in range(1, 10)}:
            messages.error(request, "Selecione uma sala válida.")
            return redirect("centrocirurgico:programador_mapa")
        programacoes = programacoes.filter(sala_painel=sala)
        descricao = f"a sala {sala}"
    elif acao == "paciente":
        programacao_id = request.POST.get("programacao", "")
        if not programacao_id.isdigit():
            messages.error(request, "Selecione um paciente válido.")
            return redirect("centrocirurgico:programador_mapa")
        programacoes = programacoes.filter(pk=int(programacao_id))
        descricao = "o paciente selecionado"
    elif acao == "todos":
        descricao = "todas as cirurgias"
    else:
        messages.error(request, "Opção de retirada inválida.")
        return redirect("centrocirurgico:programador_mapa")

    quantidade = programacoes.update(
        status=ProgramacaoCirurgia.RASCUNHO,
        enviado_em=None,
        atualizado_por=request.user,
        atualizado_em=timezone.now(),
    )
    if quantidade:
        messages.success(request, f"Foram retiradas do painel: {descricao}.")
    else:
        messages.warning(request, "Nenhuma cirurgia enviada foi encontrada para a opção informada.")
    return redirect("centrocirurgico:programador_mapa")

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


def _redirecionar_apos_envio(request, pk):
    if request.POST.get("voltar_mapa") == "1":
        data_mapa = request.POST.get("data_mapa") or timezone.localdate().isoformat()
        url = reverse("centrocirurgico:programador_mapa")
        return redirect(f"{url}?{urlencode({'data_mapa': data_mapa})}")
    return redirect("centrocirurgico:programacao_editar", pk=pk)


@login_required
@permission_required("centrocirurgico.change_programacaocirurgia", raise_exception=True)
@require_POST
@transaction.atomic
def programacao_enviar(request, pk):
    programacao = get_object_or_404(ProgramacaoCirurgia.objects.select_for_update().select_related("cirurgia"), pk=pk)
    if programacao.tipo_cirurgia not in dict(ProgramacaoCirurgia.TIPOS_CIRURGIA):
        messages.error(request, "Informe o tipo da cirurgia antes de enviar ao painel.")
        return _redirecionar_apos_envio(request, pk)
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
        return _redirecionar_apos_envio(request, pk)
    programacao.status = ProgramacaoCirurgia.ENVIADA
    programacao.enviado_em = timezone.now()
    programacao.atualizado_por = request.user
    programacao.save(update_fields=("status", "enviado_em", "atualizado_por", "atualizado_em"))
    messages.success(request, "Cirurgia enviada ao Painel de Cirurgias.")
    return _redirecionar_apos_envio(request, pk)
