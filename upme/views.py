from django.shortcuts import render, redirect, get_object_or_404
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator

from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Especialidade, Procedimento, Kit, Material, Paciente, Cirurgia, CirurgiaMaterial, Kit_Material


import json
from django.db import transaction

import psycopg2
import logging

logger = logging.getLogger(__name__)

def relatorio_cirurgia(request, pk):
    # Busca a cirurgia
    cirurgia = get_object_or_404(Cirurgia, pk=pk)

    # Kits vinculados à cirurgia com seus materiais
    cirurgia_kits = (
        CirurgiaKit.objects.filter(cirurgia=cirurgia)
        .select_related('kit')
        .order_by('kit__nome')
    )

    kits = []
    for ck in cirurgia_kits:
        materiais = (
            CirurgiaMaterial.objects
            .filter(cirurgia_kit=ck)
            .select_related('material')
            .order_by('material__nome')
        )
        kits.append({
            'cirurgia_kit': ck,
            'kit': ck.kit,
            'materiais': materiais,
        })

    # calcula idade do paciente (se data de nascimento disponível)
    idade = None
    if cirurgia.paciente and getattr(cirurgia.paciente, 'nascimento', None):
        hoje = timezone.localdate()
        nasc = cirurgia.paciente.nascimento
        idade = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))

    context = {
        'cirurgia': cirurgia,
        'kits': kits,
        'idade': idade,
        # cabeçalho — você pode mover isso para settings se preferir
        'hospital_name': 'HOSPITAL UNIVERSITÁRIO – HUPD',
        'institution': 'HOSPITAL UNIVERSITÁRIO - UNIVERSIDADE FEDERAL DO MARANHÃO',
        'unit': 'UNIDADE DE PROCESSAMENTO DE MATERIAIS ESTERILIZADOS – UPME/UPD',
        'report_title': 'FORNECIMENTO DE MATERIAIS PROCESSADOS',
    }
    return render(request, 'upme/relatorio_cirurgia.html', context)

def cadastrar_procedimentos(request, id_procedimento=None):
    titulo = "Cadastro de Procedimentos"
    especialidades = Especialidade.objects.all().order_by("nome")
    especialidade_selecionada = request.GET.get("especialidade") or request.POST.get("especialidade")

    # Se for edição
    procedimento = None
    if id_procedimento:
        procedimento = get_object_or_404(Procedimento, pk=id_procedimento)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "incluir":
            especialidade_id = request.POST.get("especialidade")
            nome = request.POST.get("procedimento")
            if especialidade_id and nome:
                Procedimento.objects.create(
                    especialidade_id=especialidade_id,
                    nome=nome
                )
            return redirect("upme:cadastrar_procedimentos")

        elif action == "editar" and procedimento:
            procedimento.nome = request.POST.get("procedimento")
            procedimento.especialidade_id = request.POST.get("especialidade")
            procedimento.save()
            return redirect("upme:cadastrar_procedimentos")

        elif action == "excluir":
            id_excluir = request.POST.get("id")
            Procedimento.objects.filter(pk=id_excluir).delete()
            return redirect("upme:cadastrar_procedimentos")

    # Lista filtrada
    registros = Procedimento.objects.all().order_by("especialidade__nome", "nome")
    if especialidade_selecionada:
        registros = registros.filter(especialidade_id=especialidade_selecionada)

    # Paginação
    paginator = Paginator(registros, 10)
    page_number = request.GET.get("page")
    registros = paginator.get_page(page_number)

    context = {
        "titulo": titulo,
        "especialidades": especialidades,
        "especialidade_selecionada": int(especialidade_selecionada) if especialidade_selecionada else None,
        "procedimento": procedimento,
        "registros": registros,
    }
    return render(request, "upme/cadastrar_procedimentos.html", context)

def cadastrar_kits(request):
    especialidades = Especialidade.objects.all().order_by("nome")
    kits = []
    materiais_disponiveis = []
    materiais_kit = []
    especialidade_selecionada = None
    kit_selecionado = None

    if request.method == "POST":
        acao = request.POST.get("acao")

        # Criar novo kit
        if acao == "cadastrar_kit":
            especialidade_id = request.POST.get("especialidade")
            nome_kit = request.POST.get("nome_kit")

            if not especialidade_id or not nome_kit:
                messages.error(request, "Informe a especialidade e o nome do kit.")
            else:
                esp = Especialidade.objects.get(pk=especialidade_id)
                Kit.objects.create(nome=nome_kit, especialidade=esp)
                messages.success(request, f"Kit '{nome_kit}' cadastrado com sucesso!")
                return redirect("upme:cadastrar_kits")

        # Atualizar materiais do kit
        elif acao == "atualizar_materiais_kit":
            kit_id = request.POST.get("kit")
            materiais_ids = request.POST.getlist("materiais_selecionados")
            
            if not kit_id:
                messages.error(request, "Selecione um kit para atualizar os materiais.")
            else:
                kit = Kit.objects.get(pk=kit_id)
                # Remove materiais antigos
                Kit_Material.objects.filter(kit=kit).delete()
                
                # Cria vínculos novos
                for mat_id in materiais_ids:
                    #try:
                        material = Material.objects.get(pk=mat_id)
                        qtd = request.POST.get(f'quantidade_{mat_id}', 1)

                        Kit_Material.objects.create(
                            kit=kit,
                            material=material,
                            quantidade=int(qtd)
                        )
                        
                    #except Material.DoesNotExist:
                        #continue

                messages.success(request, "Materiais do kit atualizados com sucesso!")
                return redirect("upme:cadastrar_kits")

    # GET ou pós-submit → manter contexto
    especialidade_selecionada = request.GET.get("especialidade") or request.POST.get("especialidade")
    kit_selecionado = request.GET.get("kit") or request.POST.get("kit")

    if especialidade_selecionada:
        kits = Kit.objects.filter(especialidade_id=especialidade_selecionada).order_by("nome")

    if kit_selecionado:
        materiais_disponiveis = Material.objects.exclude(kit_material__kit_id=kit_selecionado).order_by("nome")
        materiais_kit = Kit_Material.objects.filter(kit_id=kit_selecionado).select_related("material").order_by("material__nome")

    context = {
        "especialidades": especialidades,
        "kits": kits,
        "materiais_disponiveis": materiais_disponiveis,
        "materiais_kit": materiais_kit,
        "especialidade_selecionada": int(especialidade_selecionada) if especialidade_selecionada else None,
        "kit_selecionado": int(kit_selecionado) if kit_selecionado else None,
    }
    return render(request, "upme/cadastrar_kits.html", context)


def cadastrar_kits2(request):

    if request.method == 'POST':

        especialidade_id = request.POST.get('especialidade')
        especialidade = Especialidade.objects.get(id = especialidade_id)
        nome_kit = request.POST.get('nome_kit')
        acao = request.POST.get('acao')

        if acao == 'cadastrar_kit':
            if especialidade:
                try:
                    kit = Kit.objects.get(especialidade = especialidade, nome = nome_kit)
                except Kit.DoesNotExist:                
                    Kit.objects.create(
                        especialidade = especialidade,
                        nome=nome_kit
                    )
        if acao == 'atualizar_materiais_kit':
            print(acao)

    especialidades = Especialidade.objects.all().order_by('nome')
    
    context = {
       #'kits' : Kit.objects.all().order_by('nome'),
       'especialidades' : especialidades,
    }
    
    return render(request, 'upme/cadastrar_kits.html', context)

def get_kits_por_especialidade(request):
    print('get_kits_por_especialidade')

    especialidade_id = request.GET.get('especialidade_id')

    if not especialidade_id:
        return JsonResponse({'error': 'ID da especialidade não fornecido'}, status=400)

    try:
        kits = Kit.objects.filter(especialidade_id=especialidade_id).values('id', 'nome')
        kits_list = list(kits)
        return JsonResponse({'kits': kits_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_materiais_por_kit(request):
    kit_id = request.GET.get('kit_id')

    if not kit_id:
        return JsonResponse({'error': 'ID do kit não fornecido'}, status=400)

    try:
        # Materiais já no kit
        materiais_kit = Kit_Material.objects.filter(kit_id=kit_id).select_related('material')
        
        materiais_kit_list = [
            {
                "id": mk.id,
                "material_id": mk.material.id,
                "nome": mk.material.nome,
                "quantidade": mk.quantidade
            }
            for mk in materiais_kit
        ]

        # Materiais disponíveis (todos que não estão no kit)
        materiais_no_kit_ids = materiais_kit.values_list("material_id", flat=True)
        materiais_disponiveis = Material.objects.exclude(id__in=materiais_no_kit_ids).order_by("nome")
        materiais_disponiveis_list = list(materiais_disponiveis.values("id", "nome"))

        materiais_kit_list.sort(key=lambda x: x["nome"])

        

        return JsonResponse({
            "kit": materiais_kit_list,
            "disponiveis": materiais_disponiveis_list
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def manutencao_generica(request, model_name):
    # Obtém o model dinamicamente
    
    
    model = apps.get_model('upme', model_name)


    # Campo a ser manipulado (descricao ou nome, dependendo do model)
    field_name = 'nome' if model_name == 'Material'  or model_name == 'Especialidade' or model_name == 'Procedimento'   else 'descricao'
    coluna_name = 'Nome' if model_name == 'Material' or model_name == 'Especialidade' or model_name == 'Procedimento'   else 'Descrição'

     # Mapeamento de model_name para url_name
    url_name_map = {
        'Material': 'material',
        'Especialidade': 'especialidade',
        'Procedimento': 'procedimento',
    }

    titulo_name_map = {
        'Material': 'Material',
        'Especialidade': 'Especialidade',
        'Procedimento': 'Procedimento',
    }
    
    # Dados para edição
    edit_id = None
    edit_value = ''

        # Nome da URL para este model
    url_name = url_name_map.get(model_name, model_name.lower())
    titulo_name = titulo_name_map.get(model_name, model_name.lower())
    
    if request.method == 'POST':
        action = request.POST.get('action')
        value = request.POST.get(field_name, '').strip()
        
        if action == 'incluir' and value:
            # Incluir novo registro
            model.objects.create(**{field_name: value})
            messages.success(request, f'{value} incluído com sucesso!')
            return HttpResponseRedirect(request.path)
        
        elif action == 'editar' and value:
            # Editar registro existente
            obj_id = request.POST.get('id')
            obj = get_object_or_404(model, id=obj_id)
            setattr(obj, field_name, value)
            obj.save()
            messages.success(request, f'{value} editado com sucesso!')
            return HttpResponseRedirect(request.path)
        
        elif action == 'excluir':
            # Excluir registro
            obj_id = request.POST.get('id')
            obj = get_object_or_404(model, id=obj_id)
            obj_value = getattr(obj, field_name)
            obj.delete()
            messages.success(request, f'{obj_value} excluído com sucesso!')
            return HttpResponseRedirect(request.path)
        
        elif action == 'carregar_editar':
            # Carregar dados para edição
            obj_id = request.POST.get('id')
            obj = get_object_or_404(model, id=obj_id)
            edit_id = obj_id
            edit_value = getattr(obj, field_name)
    
    
    # Lista todos os registros
    registros = model.objects.all().order_by(field_name)

    paginator = Paginator(registros, 5)  # 10 pacientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

      
    # Contexto para o template
    context = {
        'model_name': model_name,
        'field_name': field_name,
        'coluna_name': coluna_name,
        'registros': page_obj,
        'edit_id': edit_id,
        'edit_value': edit_value,
        'titulo':titulo_name,# model._meta.verbose_name_plural or model_name.replace('CamelCase', ' ').title(),
        'url_name': url_name,  # Adiciona o nome correto da URL
    }
    
    return render(request, 'upme/manutencao.html', context)

def cirurgia_form2(request):
    if request.method == 'POST':
        prontuario = request.POST['prontuario']
        nome = request.POST['nome']
        dt_nascimento = request.POST['dt_nascimento']
    
    context = {
        'especialidades': Especialidade.objects.all(),
        'procedimentos': Procedimento.objects.all(),
        'kits': Kit.objects.all(),
        'prontuario': prontuario,
        'nome': nome,
        'dt_nascimento': dt_nascimento
    }
    return render(request, 'upme/cirurgia_form.html', context)

def cirurgia_submit(request):
    # Esta view pode ser usada para redirecionar ou processar após submissão
    return redirect('upme:cirurgia_form')

def mapa_cirurgico_list(request):

    data_mapa = request.GET.get('data_mapa')
    dados = []
    if request.method == 'GET':
        if data_mapa:
            dados = buscar_mapa_cirurgico_aghu(data=data_mapa)

    for dado in dados:
        prontuario = dado['prontuario']
        procedimento = dado['procedimento']
        especialidade = dado['especialidade']

        paciente = Paciente.objects.filter(prontuario=prontuario).first()
        if paciente:
            cirurgia = Cirurgia.objects.filter(paciente = paciente, 
                                               procedimento = procedimento, 
                                               especialidade = especialidade)
            
            

    #paginator = Paginator(dados, 8)  # 10 pacientes por página
    #page_number = request.GET.get('page')
    #page_obj = paginator.get_page(page_number)

    context = {
        'mapa': dados,
    }

    return render(request, 'upme/mapa_cirurgico_listar.html', context)

def buscar_mapa_cirurgico_aghu(data=None):
    if not data:
        # Nenhum filtro informado, não executa consulta
        return []

    conexao = psycopg2.connect(
        dbname='dbaghu',
        user='ugen_integra',
        password='UFwHP9@a',
        host='10.16.1.4',
        port='6544',
        sslmode='disable'  # se necessário para evitar erro de TLS antigo
    )

    with conexao.cursor() as cursor:
        sql = """
        SELECT 
            data, 
            sala_nome as sala, 
            v_cir.prontuario, 
            nome_paciente, 
            esp_nome as especialidade, 
            proc_descr as procedimento, 
            nome_equipe as medico,
            aip.dt_nascimento as data_nascimento,
            v_cir.dthr_inicio_ordem as data_inicio_cirurgia
        FROM agh.v_lista_mbc_cirurgias  v_cir
          LEFT JOIN agh.aip_pacientes aip ON aip.prontuario = v_cir.prontuario
        WHERE v_cir.unf_seq = 118
        """

        parametros = []

        if data:
            sql += " AND v_cir.data = %s"
            parametros.append(data)

        sql += " ORDER BY data_inicio_cirurgia asc"

        cursor.execute(sql, parametros)

        colunas = [desc[0] for desc in cursor.description]
        resultados = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        return resultados


def buscar_pacientes_aghu(prontuario=None, item=None, nome=None):

    if not prontuario and not nome:
        # Nenhum filtro informado, não executa consulta
        return []

    conexao = psycopg2.connect(
        dbname='dbaghu',
        user='ugen_integra',
        password='UFwHP9@a',
        host='10.16.1.4',
        port='6544',
        sslmode='disable'  # se necessário para evitar erro de TLS antigo
    )

    with conexao.cursor() as cursor:
        sql = """
        SELECT  
            codigo,
            nome,
            prontuario,
            dt_nascimento,
            nome_mae
            
        from agh.aip_pacientes
            
        WHERE 1=1
        """

        parametros = []

        if prontuario:
            sql += " AND agh.aip_pacientes.prontuario = %s"
            parametros.append(prontuario)
        
        if nome:
            sql += " AND upper(agh.aip_pacientes.nome) LIKE upper(%s)"
            parametros.append(f"%{nome}%")
           

        sql += " ORDER BY agh.aip_pacientes.nome asc"

        cursor.execute(sql, parametros)

        colunas = [desc[0] for desc in cursor.description]
        resultados = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        

        return resultados


def paciente_list(request):

    prontuario = request.GET.get('prontuario')
    nome = request.GET.get('nome')

    dados=''
    paciente =''
    if request.method == 'GET':
        if prontuario or nome:
            dados = buscar_pacientes_aghu(prontuario=prontuario, nome=nome)
            if dados:
                paciente = dados[0]

    

    paginator = Paginator(dados, 8)  # 10 pacientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'pacientes': page_obj,
    }
    
    return render(request, 'upme/paciente_listar.html', context)

def cirurgia_form(request):
    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    dt_nascimento = request.POST.get('dt_nascimento', '')

    especialidades = Especialidade.objects.all().order_by('nome')
    procedimentos = Procedimento.objects.all().order_by('nome')  # Initial load, will be filtered by JS
    kits = Kit.objects.all()

    especialidade_selecionada = None
    procedimento_selecionado = None
    data_cirurgia = None
    hora_cirurgia = None
    sala = None
    medico = None

    materiais = Material.objects.all().order_by('nome')

    if request.method == 'POST':
        # Handle form submission (implement logic as needed)
        pass

    context = {
        'nome': nome,
        'prontuario': prontuario,
        'dt_nascimento': dt_nascimento,
        'especialidades': especialidades,
        #'procedimentos': procedimentos,
        'kits': kits,
        'especialidade_selecionada': especialidade_selecionada,
        'procedimento_selecionado': procedimento_selecionado,
        'data_cirurgia': data_cirurgia,
        'hora_cirurgia': hora_cirurgia,
        'sala': sala,
        'medico': medico,
        'materiais': materiais
    }
    return render(request, 'upme/cirurgia_form.html', context)


@require_POST
def fornecimento_material_extra(request):
    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    data_nascimento = request.POST.get('data_nascimento', '')
    
    especialidades = Especialidade.objects.all()
    kits = Kit.objects.all().order_by('nome')
    materiais = Material.objects.all()

    materiais_incluidos = []
    materiais_agrupados = {}  # Dicionário para agrupar materiais por kit
    if prontuario:
        try:
            paciente = Paciente.objects.get(prontuario=prontuario)
            cirurgia = Cirurgia.objects.filter(paciente=paciente).order_by('-data').first()
            if cirurgia:
                # Carregar materiais com relação kit_material
                materiais_incluidos = CirurgiaMaterial.objects.filter(cirurgia=cirurgia).select_related('material', 'kit_material__kit').order_by('-kit_material')
                nome = cirurgia.paciente.nome
                data_nascimento = cirurgia.paciente.nascimento.strftime('%d/%m/%Y') if cirurgia.paciente.nascimento else ''
                especialidade = cirurgia.especialidade or ''
                procedimento = cirurgia.procedimento or ''
                data_cirurgia = cirurgia.data.strftime('%d/%m/%Y') if cirurgia.data else ''
                hora_cirurgia = cirurgia.hora.strftime('%H:%M') if cirurgia.hora else ''
                medico = cirurgia.medico or ''
                sala = cirurgia.sala or ''

                # Agrupar materiais por kit
                for material in materiais_incluidos:
                    if material.kit_material:
                        kit_id = material.kit_material.kit.id
                        kit_nome = material.kit_material.kit.nome
                        if kit_id not in materiais_agrupados:
                            materiais_agrupados[kit_id] = {'nome': kit_nome, 'itens': []}
                        materiais_agrupados[kit_id]['itens'].append(material)
                    else:
                        # Materiais individuais
                        materiais_agrupados['individual'] = materiais_agrupados.get('individual', {'nome': 'Materiais Individuais', 'itens': []})
                        materiais_agrupados['individual']['itens'].append(material)
        except Paciente.DoesNotExist:
            pass

    context = {
        'nome': nome,
        'prontuario': prontuario,
        'data_nascimento': data_nascimento,
        'especialidades': especialidades,
        'kits': kits,
        'materiais': materiais,
        'materiais_agrupados': materiais_agrupados,  # Passar dados agrupados
        
    }
    return render(request, 'upme/fornecimento_material_extra.html', context)

@require_POST
def fornecimento_material(request):
    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    data_nascimento = request.POST.get('data_nascimento', '')
    especialidade = request.POST.get('especialidade', '')
    procedimento = request.POST.get('procedimento', '')
    data_cirurgia = request.POST.get('data_cirurgia', '')
    hora_cirurgia = request.POST.get('hora_cirurgia', '')
    medico = request.POST.get('medico', '')
    sala = request.POST.get('sala', '')

    especialidades = Especialidade.objects.all()
    kits = Kit.objects.all().order_by('nome')
    materiais = Material.objects.all().order_by('nome')

    materiais_incluidos = []
    materiais_agrupados = {}  # Dicionário para agrupar materiais por kit
    if prontuario:
        try:
            paciente = Paciente.objects.get(prontuario=prontuario)
            cirurgia = Cirurgia.objects.filter(paciente=paciente).order_by('-data').first()
            if cirurgia:
                # Carregar materiais com relação kit_material
                materiais_incluidos = CirurgiaMaterial.objects.filter(cirurgia=cirurgia).select_related('material', 'kit_material__kit').order_by('-kit_material')
                nome = cirurgia.paciente.nome
                data_nascimento = cirurgia.paciente.nascimento.strftime('%d/%m/%Y') if cirurgia.paciente.nascimento else ''
                especialidade = cirurgia.especialidade or ''
                procedimento = cirurgia.procedimento or ''
                data_cirurgia = cirurgia.data.strftime('%d/%m/%Y') if cirurgia.data else ''
                hora_cirurgia = cirurgia.hora.strftime('%H:%M') if cirurgia.hora else ''
                medico = cirurgia.medico or ''
                sala = cirurgia.sala or ''

                # Agrupar materiais por kit
                for material in materiais_incluidos:
                    if material.kit_material:
                        kit_id = material.kit_material.kit.id
                        kit_nome = material.kit_material.kit.nome
                        if kit_id not in materiais_agrupados:
                            materiais_agrupados[kit_id] = {'nome': kit_nome, 'itens': []}
                        materiais_agrupados[kit_id]['itens'].append(material)
                    else:
                        # Materiais individuais
                        materiais_agrupados['individual'] = materiais_agrupados.get('individual', {'nome': 'Materiais Individuais', 'itens': []})
                        materiais_agrupados['individual']['itens'].append(material)
        except Paciente.DoesNotExist:
            pass

    context = {
        'nome': nome,
        'prontuario': prontuario,
        'data_nascimento': data_nascimento,
        'especialidade': especialidade,
        'procedimento': procedimento,
        'data_cirurgia': data_cirurgia,
        'hora_cirurgia': hora_cirurgia,
        'especialidades': especialidades,
        'kits': kits,
        'materiais': materiais,
        'materiais_agrupados': materiais_agrupados,  # Passar dados agrupados
        'sala': sala,
        'medico': medico,
    }
    return render(request, 'upme/fornecimento_material.html', context)

@require_POST
def fornecimento_material_save(request):
    if request.method == 'POST' and request.POST.get('action') == 'salvar_cirurgia':
        nome = request.POST.get('nome', '').strip()
        prontuario = request.POST.get('prontuario', '').strip()
        data_nascimento = request.POST.get('data_nascimento', '').strip()
        especialidade = request.POST.get('especialidade', '').strip()
        procedimento = request.POST.get('procedimento', '').strip()
        data_cirurgia = request.POST.get('data_cirurgia', '').strip()
        hora_cirurgia = request.POST.get('hora_cirurgia', '').strip()
        medico = request.POST.get('medico', '').strip()
        sala = request.POST.get('sala', '').strip()

        # Converter datas
        if data_nascimento:
            try:
                data_nascimento = timezone.datetime.strptime(data_nascimento, '%d/%m/%Y').date()
            except ValueError:
                raise ValidationError('O valor da data de nascimento tem um formato inválido. Use DD/MM/YYYY.')
        if data_cirurgia:
            try:
                data_cirurgia = timezone.datetime.strptime(data_cirurgia, '%d/%m/%Y').date()
            except ValueError:
                raise ValidationError('O valor da data da cirurgia tem um formato inválido. Use DD/MM/YYYY.')
        else:
            raise ValidationError('A data da cirurgia não pode estar vazia.')

        with transaction.atomic():
            try:
                paciente, _ = Paciente.objects.get_or_create(
                    nome=nome,
                    prontuario=prontuario,
                    defaults={'nascimento': data_nascimento}
                )

                cirurgia, created = Cirurgia.objects.get_or_create(
                    paciente=paciente,
                    defaults={
                        'especialidade': especialidade,
                        'procedimento': procedimento,
                        'medico': medico,
                        'sala': sala,
                        'data': data_cirurgia,
                        'hora': hora_cirurgia
                    }
                )

                materiais_data = json.loads(request.POST.get('materiais', '[]'))
                for material in materiais_data:
                    quantidade = material.get('quantidade')
                    material_id = material.get('material_id')
                    is_kit = material.get('is_kit', False)
                    kit_id = material.get('kit_id')
                    kit_nome = material.get('kit_nome', '')

                    if not quantidade or not material_id:
                        raise ValidationError('Quantidade ou material_id ausente para um material.')

                    try:
                        mat = Material.objects.get(id=material_id)
                    except Material.DoesNotExist:
                        raise ValidationError(f'Material com ID {material_id} não encontrado.')

                    if is_kit:
                        kit_material = Kit_Material.objects.get(kit=kit_id, material=mat)

                        CirurgiaMaterial.objects.update_or_create(
                                                cirurgia=cirurgia,
                                                material=mat,
                                                kit_material=kit_material,
                                                defaults={'quantidade_solicitada': quantidade})
                    else:
                        CirurgiaMaterial.objects.update_or_create(
                                                cirurgia=cirurgia,
                                                material=mat,
                                                defaults={'quantidade_solicitada': quantidade, 'kit_material': None}
                                            )

                return JsonResponse({'success': True})
            except Exception as e:
                print("Error:", str(e))
                return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método ou ação inválida'})

@require_GET
def get_procedimentos(request):
    especialidade_id = request.GET.get('especialidade_id')
    if especialidade_id:
        procedimentos = Procedimento.objects.filter(especialidade_id=especialidade_id).values('id', 'nome')
    else:
        procedimentos = Procedimento.objects.none().values('id', 'nome')
    return JsonResponse(list(procedimentos), safe=False)

@require_GET
def get_kit_materials(request):
    kit_id = request.GET.get('kit_id')
    if kit_id:
        kit_materials = Kit_Material.objects.filter(kit_id=kit_id).select_related('material').values('material__id','material__nome', 'quantidade')
        return JsonResponse(list(kit_materials), safe=False)
    return JsonResponse([], safe=False)


def relatorio_formulario_pdf(request):
    context = {
        
    }
    return render(request, 'upme/relatorio_formulario.html', context)