# opme/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import transaction
from .models import Consignacao, ConsignacaoItem, Caixa, Produto, CaixaItem, ConsignacaoFoto, Empresa
from django.db import models
from django.contrib.auth.decorators import login_required


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Consignacao

import logging

logger = logging.getLogger(__name__)


def buscar_produtos(request):

    termo = request.GET.get("q", "")
    

    produtos = Produto.objects.filter(
        descricao__icontains=termo
    ).order_by("descricao")[:20]
    data = []
    for p in produtos:
        data.append({
            "id": p.id,
            "descricao": p.descricao,
            "codigo": p.referencia,
            "referencia": p.referencia
        })
    return JsonResponse(data, safe=False)


@login_required
def consignacao_relatorio(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)

    # Itens com diferenças/consumo (via método do modelo)
    consumidos = consignacao.get_itens_consumidos()  # assume que retorna lista de dicts com 'produto', 'esperado', 'recebido', 'devolvido', 'consumido', 'observacao'

    # Total esperado = soma da composição PADRÃO da caixa
    total_esperado = sum(
        item.quantidade_esperada
        for item in consignacao.caixa.itens_padrao.all()
    )

    # Total recebido (considerando conferência e removidos)
    total_recebido = sum(
        (item.quantidade_recebida if item.quantidade_recebida is not None else item.caixa_item.quantidade_esperada)
        if not item.removido_na_chegada else 0
        for item in consignacao.itens.all()
    )

    total_reposto  = sum(
        (item.quantidade_reposta if item.quantidade_reposta is not None else item.caixa_item.quantidade_esperada)
        if not item.removido_na_chegada else 0
        for item in consignacao.itens.all()
    )

    # Total devolvido (somente itens não removidos na chegada)
    total_devolvido = sum(
        item.quantidade_devolvida or 0
        for item in consignacao.itens.all()
        if not item.removido_na_chegada
    )

    # Total consumido/perdido (somando do método consumidos)
    total_consumido = sum(item.get('consumido', 0) for item in consumidos)

    # Percentual de devolução
    percentual_devolucao = 0.0
    if total_recebido > 0:
        percentual_devolucao = (total_devolvido / total_recebido) * 100

    # Context para o template
    context = {
        'emprestimo': consignacao,  # compatibilidade com seu template (você usa emprestimo.caixa, etc.)
        'consignacao': consignacao,  # também passo consignacao para consistência
        'consumidos': consumidos,
        'total_esperado': total_esperado,
        'total_recebido': total_recebido,
        'total_reposto': total_reposto,
        'total_consumido': total_consumido,
        'total_devolvido': total_devolvido,
        'percentual_devolucao': round(percentual_devolucao, 1),
        'now': timezone.now(),
        'status_display': consignacao.get_status_display() if hasattr(consignacao, 'get_status_display') else consignacao.status,
    }

    return render(request, 'opme/consignacao_relatorio.html', context)


def consignacao_list(request):
    queryset = Consignacao.objects.all().order_by('-data_consignacao')
    
    # Filtro simples por status (opcional)
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
    
    # Paginação: 15 empréstimos por página
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'consignacoes_emprestados': Consignacao.objects.filter(status='CONSIGNADO').count(),
        'consignacoes_devolvidos': Consignacao.objects.filter(status__in=['DEVOLVIDO', 'DEVOLVIDO_PARCIAL']).count(),
    }
    return render(request, 'opme/consignacao_list.html', context)


@login_required
def consignacao_create(request):
    caixas = Caixa.objects.all()

    if request.method == 'POST':
        caixa_id = request.POST.get('caixa')
        observacao = request.POST.get('observacao', '')

        print("DEBUG POST DATA:", request.POST)  # <--- LOG IMPORTANTE: veja no terminal do servidor
        print("DEBUG FILES:", request.FILES)

        if not caixa_id:
            return render(request, 'opme/consignacao_form.html', {
                'error': 'Selecione uma caixa / kit.',
                'caixas': caixas,
                'editando': False,
            })

        try:
            caixa = Caixa.objects.get(id=caixa_id)
        except Caixa.DoesNotExist:
            return render(request, 'opme/consignacao_form.html', {
                'error': 'Caixa não encontrada.',
                'caixas': caixas,
                'editando': False,
            })

        # Cria a consignação
        consignacao = Consignacao.objects.create(
            caixa=caixa,
            observacao=observacao,
            responsavel_entrega=request.user,
        )

        # 1. Cria os itens base e mapeia por ID do CaixaItem
        itens_por_caixa_id = {}
        for item_padrao in caixa.itens_padrao.all():
            item = ConsignacaoItem.objects.create(
                consignacao=consignacao,
                caixa_item=item_padrao,
            )
            itens_por_caixa_id[item_padrao.id] = item
            print(f"DEBUG: Criado ConsignacaoItem ID {item.id} para CaixaItem {item_padrao.id}")

        # 2. Processa TODOS os campos enviados
        # Quantidade recebida
        for key in request.POST:
            if key.startswith('item_') and '_quantidade_recebida' in key:
                try:
                    caixa_item_id = int(key.split('_')[1])
                    if caixa_item_id in itens_por_caixa_id:
                        valor = request.POST.get(key, '').strip()
                        item = itens_por_caixa_id[caixa_item_id]
                        item.quantidade_recebida = int(valor) if valor.isdigit() else None
                        item.save()
                        print(f"DEBUG: Atualizado quantidade_recebida = {item.quantidade_recebida} para item {caixa_item_id}")
                except Exception as e:
                    print(f"Erro ao processar quantidade_recebida {key}: {e}")

        # Removido na chegada (checkbox só aparece se marcado)
        for key in request.POST:
            if key.startswith('item_') and '_removido_na_chegada' in key:
                try:
                    caixa_item_id = int(key.split('_')[1])
                    if caixa_item_id in itens_por_caixa_id:
                        item = itens_por_caixa_id[caixa_item_id]
                        item.removido_na_chegada = True
                        item.save()
                        print(f"DEBUG: Marcado removido_na_chegada = True para item {caixa_item_id}")
                except Exception as e:
                    print(f"Erro ao processar removido_na_chegada {key}: {e}")

        # Observação
        for key in request.POST:
            if key.startswith('item_') and '_observacao' in key:
                try:
                    caixa_item_id = int(key.split('_')[1])
                    if caixa_item_id in itens_por_caixa_id:
                        valor = request.POST.get(key, '').strip()
                        item = itens_por_caixa_id[caixa_item_id]
                        item.observacao = valor or None
                        item.save()
                        print(f"DEBUG: Atualizado observacao = '{valor}' para item {caixa_item_id}")
                except Exception as e:
                    print(f"Erro ao processar observacao {key}: {e}")

        # Fotos (já está funcionando)
        fotos_chegada = request.FILES.getlist('fotos_chegada')
        for foto in fotos_chegada:
            ConsignacaoFoto.objects.create(
                consignacao=consignacao,
                tipo='CHEGADA',
                imagem=foto,
                uploaded_by=request.user,
            )

        return redirect('opme:consignacao_detail', pk=consignacao.pk)

    return render(request, 'opme/consignacao_form.html', {
        'caixas': caixas,
        'editando': False,
    })

def consignacao_detail(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)
    
    # Calcula aqui os querysets filtrados (evita erro no template)
    fotos_chegada = consignacao.fotos.filter(tipo='CHEGADA')
    fotos_devolucao = consignacao.fotos.filter(tipo='DEVOLUCAO')
    consumidos = consignacao.get_itens_consumidos()

    context = {
        'consignacao': consignacao,
        'fotos_chegada': fotos_chegada,
        'fotos_devolucao': fotos_devolucao,
        'consumidos': consumidos,
    }
    return render(request, 'opme/consignacao_detail.html', context)

@transaction.atomic
def consignacao_reposicao(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)

    #if consignacao.status != 'EMPRESTADO':
    #    return redirect('opme:consignacao_detail', pk=pk)

    if request.method == 'POST':
        for item in consignacao.itens.all():

            prefix = f'item_{item.id}_'
            qtd_reposicao_str = request.POST.get(f'{prefix}reposicao')
            #observacao_item = request.POST.get(f'{prefix}observacao', '')

            if qtd_reposicao_str:
                item.quantidade_reposta = item.quantidade_reposta  + int(qtd_reposicao_str)
                item.save()
          

        return redirect('opme:consignacao_detail', pk=pk)

    return render(request, 'opme/consignacao_reposicao.html', {
        'consignacao': consignacao,
        'itens': consignacao.itens.select_related('caixa_item__produto').all()
    })


@transaction.atomic
def consignacao_conferencia(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)

    #if consignacao.status != 'EMPRESTADO':
    #    return redirect('opme:consignacao_detail', pk=pk)

    if request.method == 'POST':
        for item in consignacao.itens.all():
            prefix = f'item_{item.id}_'
            qtd_recebida_str = request.POST.get(f'{prefix}quantidade_recebida')
            removido = request.POST.get(f'{prefix}removido_na_chegada') == 'on'
            observacao_item = request.POST.get(f'{prefix}observacao', '')

            if qtd_recebida_str and qtd_recebida_str.isdigit():
                item.quantidade_recebida = int(qtd_recebida_str)
            else:
                item.quantidade_recebida = None

            item.removido_na_chegada = removido
            item.observacao = observacao_item
            item.save()

        return redirect('opme:consignacao_detail', pk=pk)

    return render(request, 'opme/consignacao_conferencia.html', {
        'consignacao': consignacao,
        'itens': consignacao.itens.select_related('caixa_item__produto').all()
    })

@login_required
@transaction.atomic
def consignacao_update(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)
    caixas = Caixa.objects.all()
    
    if request.method == 'POST':
        observacao = request.POST.get('observacao', '')
        consignacao.observacao = observacao
        consignacao.save()

        # Salva novas fotos de chegada (se enviadas)
        fotos_chegada = request.FILES.getlist('fotos_chegada')
        for foto in fotos_chegada:
            ConsignacaoFoto.objects.create(
                consignacao=consignacao,
                tipo='CHEGADA',
                imagem=foto,
                uploaded_by=request.user,
            )

        return redirect('opme:consignacao_detail', pk=consignacao.pk)

    return render(request, 'opme/consignacao_form.html', {
        'consignacao': consignacao,
        'caixas': caixas,
        'editando': True,
    })

@transaction.atomic
@login_required
def consignacao_devolucao(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)

    # Fotos existentes de devolução
    fotos_devolucao_existentes = consignacao.fotos.filter(tipo="DEVOLUCAO")
    qtd_fotos_devolucao = fotos_devolucao_existentes.count()

    # Itens da consignação
    itens = consignacao.itens.all()

    if request.method == 'POST':
        observacao_devolucao = request.POST.get('observacao_devolucao', '')

        # Atualiza data de devolução (agora sim!)
        consignacao.data_devolucao = timezone.now()

        # Atualiza observação geral de devolução (se o modelo tiver o campo)
        consignacao.observacao_devolucao = observacao_devolucao.strip() or None

        

        consignacao.save()

        # Atualiza itens com dados de devolução
        for item in itens:
            key_qtd_dev = f"item_{item.caixa_item.id}_quantidade_devolvida"
            key_obs_dev = f"item_{item.caixa_item.id}_observacao_devolucao"

            # Quantidade devolvida
            qtd_dev = request.POST.get(key_qtd_dev, '').strip()
            if qtd_dev.isdigit():
                item.quantidade_devolvida = int(qtd_dev)
            else:
                item.quantidade_devolvida = 0  # ou None, conforme seu modelo

            # Observação de devolução por item
            obs_dev = request.POST.get(key_obs_dev, '').strip()
            item.observacao_devolucao = obs_dev or None
        
            item.save()

        # Adiciona novas fotos de devolução
        fotos_novas = request.FILES.getlist('fotos_devolucao')
        for foto in fotos_novas:
            ConsignacaoFoto.objects.create(
                consignacao=consignacao,
                tipo='DEVOLUCAO',
                imagem=foto,
                uploaded_by=request.user,
            )

        return redirect('opme:consignacao_detail', pk=consignacao.pk)

    context = {
        'consignacao': consignacao,
        'itens': itens,
        'fotos_devolucao_existentes': fotos_devolucao_existentes,
        'qtd_fotos_devolucao': qtd_fotos_devolucao,
    }

    return render(request, 'opme/consignacao_devolucao.html', context)


def empresa_list(request):
    empresas = Empresa.objects.all().order_by('nome')
    return render(request, 'opme/empresa_list.html', {
        'empresas': empresas
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Caixa, Consignacao, ConsignacaoItem, ConsignacaoFoto


@login_required
def consignacao_edit(request, pk):
    consignacao = get_object_or_404(Consignacao, pk=pk)
    caixas = Caixa.objects.all()

    # Fotos existentes de chegada
    fotos_chegada_existentes = consignacao.fotos.filter(tipo="CHEGADA")
    qtd_fotos_chegada = fotos_chegada_existentes.count()

    # Itens já criados
    itens = consignacao.itens.all()  # ConsignacaoItem relacionados

    if request.method == 'POST':
        observacao = request.POST.get('observacao', '')

        # Atualiza observação geral
        consignacao.observacao = observacao
        consignacao.save()

        # Atualiza os itens existentes
        for item in itens:
            key_qtd = f"item_{item.caixa_item.id}_quantidade_recebida"
            key_rem = f"item_{item.caixa_item.id}_removido_na_chegada"
            key_obs = f"item_{item.caixa_item.id}_observacao"

            # Quantidade recebida
            qtd = request.POST.get(key_qtd, '').strip()
            item.quantidade_recebida = int(qtd) if qtd.isdigit() else None

            # Removido na chegada
            item.removido_na_chegada = key_rem in request.POST  # checkbox só aparece se marcado

            # Observação
            obs = request.POST.get(key_obs, '').strip()
            item.observacao = obs or None

            item.save()

        # Adiciona novas fotos (se enviadas)
        fotos_novas = request.FILES.getlist('fotos_chegada')
        for foto in fotos_novas:
            ConsignacaoFoto.objects.create(
                consignacao=consignacao,
                tipo='CHEGADA',
                imagem=foto,
                uploaded_by=request.user,
            )

        return redirect('opme:consignacao_detail', pk=consignacao.pk)

    # GET: preenche o form com dados existentes
    return render(request, 'opme/consignacao_form.html', {
        'caixas': caixas,
        'consignacao': consignacao,
        'itens': itens,
        'editando': True,
        'fotos_chegada_existentes': fotos_chegada_existentes,
        'qtd_fotos_chegada': qtd_fotos_chegada,
    })

@transaction.atomic
def empresa_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()

        errors = {}
        if not nome:
            errors['nome'] = "O nome da empresa é obrigatório."

        if errors:
            return render(request, 'opme/empresa_form.html', {
                'errors': errors,
                'nome': nome,
            })

        Empresa.objects.create(nome=nome)
        return redirect('opme:empresa_list')

    return render(request, 'opme/empresa_form.html', {})


@transaction.atomic
def empresa_update(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()

        errors = {}
        if not nome:
            errors['nome'] = "O nome da empresa é obrigatório."

        if errors:
            return render(request, 'opme/empresa_form.html', {
                'errors': errors,
                'nome': nome,
                'empresa': empresa,
                'editando': True,
            })

        empresa.nome = nome
        empresa.save()
        return redirect('opme:empresa_list')

    return render(request, 'opme/empresa_form.html', {
        'empresa': empresa,
        'nome': empresa.nome,
        'editando': True,
    })


def empresa_delete(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        empresa.delete()
        return redirect('opme:empresa_list')

    return render(request, 'opme/empresa_confirm_delete.html', {
        'empresa': empresa
    })


from django.db.models import Count, Q

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

def produto_list(request):
    queryset = Produto.objects.all().order_by('descricao')
    
    # Filtros de busca
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(
            Q(descricao__icontains=q) |
            Q(referencia__icontains=q) |
            Q(fabricante__icontains=q)
        )
    
    unidade = request.GET.get('unidade')
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    
    # Paginação: 20 itens por página (ajuste conforme necessário)
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        produtos = paginator.page(page_number)
    except PageNotAnInteger:
        produtos = paginator.page(1)
    except EmptyPage:
        produtos = paginator.page(paginator.num_pages)
    
    context = {
        'produtos': produtos,                     # page_obj
        'page_obj': produtos,                     # para usar page_obj no template
        'paginator': paginator,
        'produtos_ativos': queryset.count(),      # ou ajuste se tiver campo ativo
        'fabricantes_unicos': queryset.values('fabricante').distinct().count(),
        'unidades_unicas': Produto.objects.values_list('unidade', flat=True).distinct().order_by('unidade'),
    }
    return render(request, 'opme/produto_list.html', context)


@transaction.atomic
def produto_create(request):
    if request.method == 'POST':
        descricao = request.POST.get('descricao', '').strip()
        referencia = request.POST.get('referencia', '').strip()
        fabricante = request.POST.get('fabricante', '').strip()
        unidade = request.POST.get('unidade', 'un').strip()

        errors = {}
        if not descricao:
            errors['descricao'] = "A descrição é obrigatória."

        if errors:
            return render(request, 'opme/produto_form.html', {
                'errors': errors,
                'descricao': descricao,
                'referencia': referencia,
                'fabricante': fabricante,
                'unidade': unidade,
            })

        Produto.objects.create(
            descricao=descricao,
            referencia=referencia,
            fabricante=fabricante,
            unidade=unidade,
        )
        return redirect('opme:produto_list')

    return render(request, 'opme/produto_form.html', {})


@transaction.atomic
def produto_update(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    if request.method == 'POST':
        descricao = request.POST.get('descricao', '').strip()
        referencia = request.POST.get('referencia', '').strip()
        fabricante = request.POST.get('fabricante', '').strip()
        unidade = request.POST.get('unidade', 'un').strip()

        errors = {}
        if not descricao:
            errors['descricao'] = "A descrição é obrigatória."

        if errors:
            return render(request, 'opme/produto_form.html', {
                'errors': errors,
                'descricao': descricao,
                'referencia': referencia,
                'fabricante': fabricante,
                'unidade': unidade,
                'editando': True,
                'produto': produto,
            })

        produto.descricao = descricao
        produto.referencia = referencia
        produto.fabricante = fabricante
        produto.unidade = unidade
        produto.save()
        return redirect('opme:produto_list')

    return render(request, 'opme/produto_form.html', {
        'produto': produto,
        'descricao': produto.descricao,
        'referencia': produto.referencia,
        'fabricante': produto.fabricante,
        'unidade': produto.unidade,
        'editando': True,
    })


def produto_delete(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        produto.delete()
        return redirect('opme:produto_list')
    return render(request, 'opme/produto_confirm_delete.html', {'produto': produto})


def caixa_list(request):
    queryset = Caixa.objects.all().order_by('identificador')
    
    # Filtro simples por busca (opcional)
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(
            models.Q(identificador__icontains=q) | 
            models.Q(descricao__icontains=q) |
            models.Q(empresa__nome__icontains=q)
        )
    
    # Filtro por empresa (opcional)
    empresa_id = request.GET.get('empresa')
    if empresa_id:
        queryset = queryset.filter(empresa_id=empresa_id)
    
    context = {
        'caixas': queryset,
        'empresas': Empresa.objects.all(),  # para o select de filtro
        'caixas_ativas': queryset.count(),  # ajuste conforme sua lógica de "ativo"
        'caixas_com_itens': queryset.filter(itens_padrao__isnull=False).distinct().count(),
    }
    return render(request, 'opme/caixa_list.html', context)


@transaction.atomic
def caixa_create(request):
    empresas = Empresa.objects.all()
    produtos = Produto.objects.all().order_by('descricao')
               

    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        empresa_id = request.POST.get('empresa')
        descricao = request.POST.get('descricao', '').strip()

        errors = {}
        if not identificador:
            errors['identificador'] = "Identificador é obrigatório."
        if not empresa_id:
            errors['empresa'] = "Selecione uma empresa."

        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            errors['empresa'] = "Empresa inválida."

        if errors:
            return render(request, 'opme/caixa_form.html', {
                'errors': errors,
                'empresas': empresas,
                'produtos': produtos,
                'identificador': identificador,
                'descricao': descricao,
                'empresa_id': empresa_id,
            })

        caixa = Caixa.objects.create(
            identificador=identificador,
            empresa=empresa,
            descricao=descricao,
        )

        # Processa itens padrão enviados
        i = 0
        while True:
            produto_id_key = f'itens_{i}_produto'
            qtd_key = f'itens_{i}_quantidade'
            if produto_id_key not in request.POST:
                break

            produto_id = request.POST.get(produto_id_key)
            qtd = request.POST.get(qtd_key, '1')

            if produto_id and qtd.isdigit() and int(qtd) > 0:
                try:
                    produto = Produto.objects.get(id=produto_id)
                    CaixaItem.objects.create(
                        caixa=caixa,
                        produto=produto,
                        quantidade_esperada=int(qtd)
                    )
                except Produto.DoesNotExist:
                    pass  # ignora se produto inválido

            i += 1

        return redirect('opme:caixa_list')

    return render(request, 'opme/caixa_form.html', {
        'empresas': empresas,
        'produtos': produtos,
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

@transaction.atomic
def caixa_update(request, pk):
    caixa = get_object_or_404(Caixa, pk=pk)

    empresas = Empresa.objects.all()
    produtos = Produto.objects.all().order_by('descricao')

    if request.method == 'POST':

        identificador = request.POST.get('identificador', '').strip()
        empresa_id = request.POST.get('empresa')
        descricao = request.POST.get('descricao', '').strip()

        errors = {}

        if not identificador:
            errors['identificador'] = "Identificador é obrigatório."

        if not empresa_id:
            errors['empresa'] = "Selecione uma empresa."

        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except:
            errors['empresa'] = "Empresa inválida."

        if errors:
            return render(request, 'opme/caixa_form.html', {
                'errors': errors,
                'caixa': caixa,
                'empresas': empresas,
                'produtos': produtos,
                'editando': True,
            })

        # Atualiza dados da caixa
        caixa.identificador = identificador
        caixa.empresa = empresa
        caixa.descricao = descricao
        caixa.save()

        # =========================
        # LER ITENS DO FORMULÁRIO
        # =========================

        itens_post = []

        i = 0
        while True:

            produto_key = f'itens_{i}_produto'
            qtd_key = f'itens_{i}_quantidade'

            if produto_key not in request.POST:
                break

            produto_id = request.POST.get(produto_key)
            qtd = request.POST.get(qtd_key, '1')

            if produto_id and qtd.isdigit() and int(qtd) > 0:
                itens_post.append({
                    "produto_id": int(produto_id),
                    "quantidade": int(qtd)
                })

            i += 1

        # =========================
        # ITENS EXISTENTES
        # =========================

        itens_existentes = list(caixa.itens_padrao.all())

        # =========================
        # ATUALIZA OU REMOVE
        # =========================

        for item in itens_existentes:

            encontrado = False

            for novo in itens_post:

                if item.produto_id == novo["produto_id"]:

                    encontrado = True

                    # Atualiza quantidade se mudou
                    if item.quantidade_esperada != novo["quantidade"]:
                        item.quantidade_esperada = novo["quantidade"]
                        item.save()

                    break

            # remover se não estiver mais no formulário
            if not encontrado:

                if not item.consignacaoitem_set.exists():
                    item.delete()
                else:
                    messages.warning(
                        request,
                        f"O item '{item.produto}' não foi removido porque já foi usado em consignação."
                    )

        # =========================
        # CRIAR NOVOS ITENS
        # =========================

        produtos_existentes = set(
            caixa.itens_padrao.values_list("produto_id", flat=True)
        )

        for novo in itens_post:

            if novo["produto_id"] not in produtos_existentes:

                produto = Produto.objects.get(id=novo["produto_id"])

                CaixaItem.objects.create(
                    caixa=caixa,
                    produto=produto,
                    quantidade_esperada=novo["quantidade"]
                )

        messages.success(request, "Caixa atualizada com sucesso.")

        return redirect('opme:caixa_list')

    return render(request, 'opme/caixa_form.html', {
        'caixa': caixa,
        'empresas': empresas,
        'produtos': produtos,
        'editando': True,
    })

def caixa_update2(request, pk):
    caixa = get_object_or_404(Caixa, pk=pk)
    empresas = Empresa.objects.all()
    produtos = Produto.objects.all().order_by('descricao')

    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        empresa_id = request.POST.get('empresa')
        descricao = request.POST.get('descricao', '').strip()

        errors = {}
        if not identificador:
            errors['identificador'] = "Identificador é obrigatório."
        if not empresa_id:
            errors['empresa'] = "Selecione uma empresa."

        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except:
            errors['empresa'] = "Empresa inválida."

        if errors:
            return render(request, 'opme/caixa_form.html', {
                'errors': errors,
                'caixa': caixa,
                'empresas': empresas,
                'produtos': produtos,
                'editando': True,
            })

        caixa.identificador = identificador
        caixa.empresa = empresa
        caixa.descricao = descricao
        caixa.save()

        # Remove itens existentes e recria (simples para este caso)
        # caixa.itens_padrao.all().delete()

        for item in caixa.itens_padrao.all():
            if not item.consignacaoitem_set.exists():
                item.delete()

        i = 0
        while True:
            produto_id_key = f'itens_{i}_produto'
            qtd_key = f'itens_{i}_quantidade'
            if produto_id_key not in request.POST:
                break

            produto_id = request.POST.get(produto_id_key)
            qtd = request.POST.get(qtd_key, '1')

            if produto_id and qtd.isdigit() and int(qtd) > 0:
                try:
                    produto = Produto.objects.get(id=produto_id)
                    CaixaItem.objects.create(
                        caixa=caixa,
                        produto=produto,
                        quantidade_esperada=int(qtd)
                    )
                except:
                    pass

            i += 1

        return redirect('opme:caixa_list')

    return render(request, 'opme/caixa_form.html', {
        'caixa': caixa,
        'empresas': empresas,
        'produtos': produtos,
        'editando': True,
    })


def caixa_delete(request, pk):
    caixa = get_object_or_404(Caixa, pk=pk)
    if request.method == 'POST':
        caixa.delete()
        return redirect('opme:caixa_list')
    return render(request, 'opme/caixa_confirm_delete.html', {'caixa': caixa})

from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
@login_required
def get_itens_caixa(request):
    caixa_id = request.GET.get('caixa_id')
    if not caixa_id:
        return JsonResponse({'error': 'Caixa não informada'}, status=400)

    try:
        caixa = Caixa.objects.get(id=caixa_id)
        itens = []
        for item_padrao in caixa.itens_padrao.all():

            logger.error(f"Produto: {item_padrao.produto}")
            logger.error(f"Produto Referencia: {item_padrao.produto.referencia}")
            #logger.error(f"Referencia: {item_padrao.referencia}")

            itens.append({
                'id': item_padrao.id,  # ID do CaixaItem (para usar no name dos inputs)
                'produto': str(item_padrao.produto),
                'codigo': str(item_padrao.produto.referencia),
                'quantidade_esperada': item_padrao.quantidade_esperada,
            })
        return JsonResponse({'itens': itens})
    except Caixa.DoesNotExist:
        return JsonResponse({'error': 'Caixa não encontrada'}, status=404)