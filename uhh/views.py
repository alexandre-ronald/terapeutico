from django.shortcuts import render, redirect, get_object_or_404
from .models import (
    SolicitacaoHemocomponente,
    ProvaCruzada,
    LiberacaoBolsa,
    BolsaSangue,
    Paciente,
    ItemSolicitacaoHemocomponente,
    RetornoSolicitacao,
)

from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models import Q

# LISTA SOLICITAÇÕES
def lista_solicitacoes2(request):

    solicitacoes = SolicitacaoHemocomponente.objects.all().order_by('-data_solicitacao')

    return render(request, 'uhh/solicitacoes/lista.html', {
        'solicitacoes': solicitacoes
    })


# NOVA SOLICITAÇÃO
def nova_solicitacao2(request):

    if request.method == 'POST':

        hemocomponente = request.POST.get('hemocomponente')
        grupo = request.POST.get('grupo')
        rh = request.POST.get('rh')
        quantidade = request.POST.get('quantidade')
        justificativa = request.POST.get('justificativa')
        solicitante = request.POST.get('solicitante')

        SolicitacaoHemocomponente.objects.create(
            hemocomponente=hemocomponente,
            grupo_sanguineo=grupo,
            fator_rh=rh,
            quantidade=quantidade,
            justificativa=justificativa,
            solicitante=solicitante
        )

        return redirect('lista_solicitacoes')

    return render(request, 'uhh/solicitacoes/nova.html')

def lista_provas(request):

    provas = ProvaCruzada.objects.select_related('paciente','bolsa').all()

    return render(request, 'uhh/provas/lista.html', {
        'provas': provas
    })

from django.utils import timezone

def nova_prova(request):

    pacientes = Paciente.objects.all()
    bolsas = BolsaSangue.objects.filter(status='estoque')

    #bolsas = BolsaSangue.objects.filter(
    ##    status='estoque',
    #    data_validade__gte=timezone.now().date()
    #)

    if request.method == 'POST':

        paciente_id = request.POST.get('paciente')
        bolsa_id = request.POST.get('bolsa')
        resultado = request.POST.get('resultado')
        realizado_por = request.POST.get('realizado_por')

        ProvaCruzada.objects.create(
            paciente_id=paciente_id,
            bolsa_id=bolsa_id,
            resultado=resultado,
            realizado_por=realizado_por
        )

        return redirect('lista_provas')

    return render(request, 'uhh/provas/nova.html',{
        'pacientes': pacientes,
        'bolsas': bolsas
    })

def lista_liberacoes(request):

    liberacoes = LiberacaoBolsa.objects.select_related(
        'prova_cruzada',
        'prova_cruzada__bolsa',
        'prova_cruzada__paciente'
    ).all()

    return render(request, 'uhh/liberacoes/lista.html',{
        'liberacoes': liberacoes
    })


def nova_liberacao(request):

    provas = ProvaCruzada.objects.filter(resultado='compativel')

    if request.method == 'POST':

        prova_id = request.POST.get('prova')
        setor = request.POST.get('setor')
        liberado_por = request.POST.get('liberado_por')

        prova = ProvaCruzada.objects.get(id=prova_id)

        LiberacaoBolsa.objects.create(
            prova_cruzada=prova,
            setor_destino=setor,
            liberado_por=liberado_por
        )

        bolsa = prova.bolsa
        bolsa.status = 'liberada'
        bolsa.save()

        return redirect('lista_liberacoes')

    return render(request,'uhh/liberacoes/nova.html',{
        'provas': provas
    })

from django.shortcuts import render, redirect, get_object_or_404
from .models import DevolucaoBolsa, BolsaSangue, LiberacaoBolsa

def nova_devolucao(request):

    liberacoes = LiberacaoBolsa.objects.all()

    if request.method == "POST":

        liberacao_id = request.POST.get("liberacao")
        devolvido_por = request.POST.get("devolvido_por")
        setor_origem = request.POST.get("setor_origem")
        condicao = request.POST.get("condicao_bolsa")
        status = request.POST.get("status")
        observacoes = request.POST.get("observacoes")

        liberacao = get_object_or_404(LiberacaoBolsa, id=liberacao_id)

        devolucao = DevolucaoBolsa.objects.create(
            bolsa=liberacao.prova_cruzada.bolsa,
            liberacao=liberacao,
            devolvido_por=devolvido_por,
            setor_origem=setor_origem,
            condicao_bolsa=condicao,
            status=status,
            observacoes=observacoes
        )

        return redirect("uhh:lista_devolucoes")

    context = {
        "liberacoes": liberacoes
    }

    return render(
        request,
        "uhh/devolucoes/form.html",
        context
    )

from .models import DevolucaoBolsa

def lista_devolucoes(request):

    devolucoes = DevolucaoBolsa.objects.all().order_by("-data_devolucao")

    context = {
        "devolucoes": devolucoes
    }

    return render(
        request,
        "uhh/devolucoes/lista.html",
        context
    )



# =============================
# LISTA DE SOLICITAÇÕES
# =============================
def lista_solicitacoes(request):

    solicitacoes = SolicitacaoHemocomponente.objects.all().order_by("-data_solicitacao")

    context = {
        "solicitacoes": solicitacoes
    }

    return render(
        request,
        "uhh/solicitacoes/lista.html",
        context
    )


# =============================
# NOVA SOLICITAÇÃO
# =============================

from django.shortcuts import render, redirect
from django.db import transaction
from .models import SolicitacaoHemocomponente, ItemSolicitacaoHemocomponente


def nova_solicitacao(request):

    if request.method == "POST":

        solicitante = request.POST.get("solicitante")
        observacoes = request.POST.get("observacoes")

        hemocomponentes = request.POST.getlist("hemocomponente[]")
        grupos = request.POST.getlist("grupo[]")
        rhs = request.POST.getlist("rh[]")
        mls = request.POST.getlist("ml[]")
        quantidades = request.POST.getlist("quantidade[]")

        with transaction.atomic():

            solicitacao = SolicitacaoHemocomponente.objects.create(
                solicitante=solicitante,
                observacoes=observacoes
            )

            for i in range(len(hemocomponentes)):

                if hemocomponentes[i]:

                    # 🔒 tratamento seguro do ml
                    try:
                        ml = int(mls[i]) if mls[i] else None
                    except (ValueError, TypeError):
                        ml = None

                    # 🔒 quantidade segura
                    try:
                        quantidade = int(quantidades[i]) if quantidades[i] else 0
                    except (ValueError, TypeError):
                        quantidade = 0

                    ItemSolicitacaoHemocomponente.objects.create(
                        solicitacao=solicitacao,
                        hemocomponente=hemocomponentes[i],
                        grupo_sanguineo=grupos[i],
                        fator_rh=rhs[i],
                        ml=ml,
                        quantidade=quantidade
                    )

        return redirect("uhh:lista_solicitacoes")

    return render(request, "uhh/solicitacoes/form_inline.html")

from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from .models import SolicitacaoHemocomponente, ItemSolicitacaoHemocomponente


def editar_solicitacao(request, solicitacao_id):

    solicitacao = get_object_or_404(SolicitacaoHemocomponente, id=solicitacao_id)
    itens = solicitacao.itens.all()

    if request.method == "POST":

        solicitacao.solicitante = request.POST.get("solicitante")
        solicitacao.observacoes = request.POST.get("observacoes")
        solicitacao.save()

        hemocomponentes = request.POST.getlist("hemocomponente[]")
        grupos = request.POST.getlist("grupo[]")
        rhs = request.POST.getlist("rh[]")
        mls = request.POST.getlist("ml[]")
        quantidades = request.POST.getlist("quantidade[]")
        ids = request.POST.getlist("item_id[]")  # 👈 importante

        with transaction.atomic():

            itens_existentes = {str(i.id): i for i in itens}

            itens_processados = []

            for i in range(len(hemocomponentes)):

                if not hemocomponentes[i]:
                    continue

                # tratamento seguro
                try:
                    ml = int(mls[i]) if mls[i] else None
                except:
                    ml = None

                try:
                    quantidade = int(quantidades[i]) if quantidades[i] else 0
                except:
                    quantidade = 0

                item_id = ids[i]

                if item_id:  # 🔄 UPDATE
                    item = itens_existentes.get(item_id)

                    if item:
                        item.hemocomponente = hemocomponentes[i]
                        item.grupo_sanguineo = grupos[i]
                        item.fator_rh = rhs[i]
                        item.ml = ml
                        item.quantidade = quantidade
                        item.save()

                        itens_processados.append(item.id)

                else:  # ➕ NOVO ITEM
                    novo = ItemSolicitacaoHemocomponente.objects.create(
                        solicitacao=solicitacao,
                        hemocomponente=hemocomponentes[i],
                        grupo_sanguineo=grupos[i],
                        fator_rh=rhs[i],
                        ml=ml,
                        quantidade=quantidade
                    )
                    itens_processados.append(novo.id)

            # ❌ REMOVER itens apagados na tela
            for item in itens:
                if item.id not in itens_processados:
                    item.delete()

        return redirect("uhh:lista_solicitacoes")

    return render(request, "uhh/solicitacoes/form_inline.html", {
        "solicitacao": solicitacao,
        "itens": itens,
        "modo": "editar"
    })

# =============================
# ITENS DA SOLICITAÇÃO
# =============================
def itens_solicitacao(request, solicitacao_id):

    solicitacao = get_object_or_404(
        SolicitacaoHemocomponente,
        id=solicitacao_id
    )

    if request.method == "POST":

        hemocomponente = request.POST.get("hemocomponente")
        grupo = request.POST.get("grupo")
        rh = request.POST.get("rh")
        quantidade = request.POST.get("quantidade")

        ItemSolicitacaoHemocomponente.objects.create(
            solicitacao=solicitacao,
            hemocomponente=hemocomponente,
            grupo_sanguineo=grupo,
            fator_rh=rh,
            quantidade=quantidade
        )

        return redirect(
            "uhh:itens_solicitacao",
            solicitacao.id
        )

    itens = ItemSolicitacaoHemocomponente.objects.filter(
        solicitacao=solicitacao
    )

    context = {
        "solicitacao": solicitacao,
        "itens": itens
    }

    return render(
        request,
        "uhh/solicitacoes/itens.html",
        context
    )


# =============================
# LISTA DE RETORNOS
# =============================
def lista_retornos(request):

    retornos = RetornoSolicitacao.objects.all().order_by("-data_registro")

    context = {
        "retornos": retornos
    }

    return render(
        request,
        "uhh/retornos/lista.html",
        context
    )


# =============================
# REGISTRAR RETORNO
# =============================
def registrar_retorno(request, solicitacao_id):

    solicitacao = get_object_or_404(
        SolicitacaoHemocomponente,
        id=solicitacao_id
    )

    itens = ItemSolicitacaoHemocomponente.objects.filter(
        solicitacao=solicitacao
    )

    bolsas = BolsaSangue.objects.all()

    if request.method == "POST":

        for item in itens:

            bolsa_id = request.POST.get(f"bolsa_{item.id}")
            recebido = request.POST.get(f"recebido_{item.id}")

            bolsa = None

            if bolsa_id:
                bolsa = BolsaSangue.objects.get(id=bolsa_id)

            RetornoSolicitacao.objects.create(
                item_solicitacao=item,
                bolsa=bolsa,
                recebido=True if recebido else False
            )

        return redirect("uhh:lista_retornos")

    context = {
        "solicitacao": solicitacao,
        "itens": itens,
        "bolsas": bolsas
    }

    return render(
        request,
        "uhh/retornos/form.html",
        context
    )

# Bolsas


def lista_bolsas(request):
    busca = request.GET.get('busca', '')
    status = request.GET.get('status', '')

    bolsas = BolsaSangue.objects.all().order_by('-data_criacao')

    if busca:
        bolsas = bolsas.filter(
            Q(numero_bolsa__icontains=busca) |
            Q(numero_macarrao__icontains=busca)
        )

    if status:
        bolsas = bolsas.filter(status=status)

    # 🔢 TOTAIS (ANTES DA PAGINAÇÃO)
    totais = BolsaSangue.objects.aggregate(
        total=Count('id'),
        estoque=Count('id', filter=Q(status='estoque')),
        reservada=Count('id', filter=Q(status='reservada')),
        liberada=Count('id', filter=Q(status='liberada')),
        transfundida=Count('id', filter=Q(status='transfundida')),
        descartada=Count('id', filter=Q(status='descartada')),
    )

    paginator = Paginator(bolsas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'uhh/bolsas/lista.html', {
        'bolsas': page_obj,
        'page_obj': page_obj,
        'totais': totais,
        'busca': busca,
        'status_filtro': status,
    })

def nova_bolsa(request):
    if request.method == "POST":
        BolsaSangue.objects.create(
            numero_bolsa=request.POST.get("numero_bolsa"),
            numero_macarrao=request.POST.get("numero_macarrao"),
            hemocomponente=request.POST.get("hemocomponente"),
            grupo_sanguineo=request.POST.get("grupo_sanguineo"),
            fator_rh=request.POST.get("fator_rh"),
            volume_ml=request.POST.get("volume_ml"),
            data_coleta=request.POST.get("data_coleta"),
            data_validade=request.POST.get("data_validade"),
            status=request.POST.get("status"),
            observacoes=request.POST.get("observacoes"),
            recebimento_id=request.POST.get("recebimento")  # importante
        )

        return redirect('uhh:lista_bolsas')

    return render(request, 'uhh/bolsas/form.html', {
        'modo': 'novo'
    })

from django.shortcuts import render, get_object_or_404, redirect
from .models import BolsaSangue


def editar_bolsa(request, bolsa_id):
    bolsa = get_object_or_404(BolsaSangue, id=bolsa_id)

    if request.method == "POST":
        bolsa.numero_bolsa = request.POST.get("numero_bolsa")
        bolsa.numero_macarrao = request.POST.get("numero_macarrao")
        bolsa.hemocomponente = request.POST.get("hemocomponente")
        bolsa.grupo_sanguineo = request.POST.get("grupo_sanguineo")
        bolsa.fator_rh = request.POST.get("fator_rh")
        bolsa.volume_ml = request.POST.get("volume_ml")
        bolsa.data_coleta = request.POST.get("data_coleta")
        bolsa.data_validade = request.POST.get("data_validade")
        bolsa.status = request.POST.get("status")
        bolsa.observacoes = request.POST.get("observacoes")

        bolsa.save()

        return redirect(request.META.get('HTTP_REFERER', 'uhh:lista_bolsas'))

    return render(request, "uhh/bolsas/form.html", {
        "bolsa": bolsa,
        "modo": "editar"
    })

def relatorio_solicitacao(request, solicitacao_id):

    solicitacao = SolicitacaoHemocomponente.objects.get(id=solicitacao_id)
    itens = solicitacao.itens.all()

    # organizar por tipo + grupo + rh
    mapa = {}

    for item in itens:
        chave = (item.hemocomponente, item.grupo_sanguineo, item.fator_rh)

        if chave not in mapa:
            mapa[chave] = {
                "quantidade": 0,
                "ml": item.ml
            }

        mapa[chave]["quantidade"] += item.quantidade or 0

    grupos_sanguineos = [
        ("O", "+"),
        ("A", "+"),
        ("B", "+"),
        ("AB", "+"),
        ("O", "-"),
        ("A", "-"),
        ("B", "-"),
        ("AB", "-"),
    ]

    context = {
        "solicitacao": solicitacao,
        "mapa": mapa,
        "grupos_sanguineos": grupos_sanguineos
    }

    return render(request, "uhh/solicitacoes/relatorio_hemomar.html", context)