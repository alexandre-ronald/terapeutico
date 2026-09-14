# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.core import signing
from datetime import date
from django.utils import timezone
from datetime import datetime
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Paciente, Cirurgia, GiroSala, LimpezaTerminal
from django.db import models
from datetime import timedelta


from django.http import HttpResponse
from django.db.models import Avg, Min, Max, Count, Sum, ExpressionWrapper, DurationField,  F, Q
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors



from django.db.models.functions import Coalesce

from .services.giro_sala_service import GiroSalaService

import json
from django.db import transaction

import psycopg2
import logging

import calendar

logger = logging.getLogger(__name__)


ETAPAS_GIRO = (
    ("dataInicioAnestesia", "Início da anestesia"),
    ("dataInicioCirurgia", "Início da cirurgia"),
    ("dataFinalCirurgia", "Final da cirurgia"),
    ("dataSaidaSala", "Saída da sala"),
    ("dataInicioDesmontagemSala", "Início da desmontagem"),
    ("dataFinalDesmontagemSala", "Final da desmontagem"),
    ("dataInicioLimpeza", "Início da limpeza"),
    ("dataFinalLimpeza", "Final da limpeza"),
    ("dataSalaLiberada", "Sala liberada"),
)


def _validar_horario_etapa(giro, campo, momento):
    campos = [item[0] for item in ETAPAS_GIRO]
    if campo not in campos:
        return "Etapa inválida para registro."

    indice = campos.index(campo)
    for campo_anterior, descricao_anterior in ETAPAS_GIRO[:indice]:
        valor_anterior = getattr(giro, campo_anterior)
        if not valor_anterior:
            return f"Registre '{descricao_anterior}' antes desta etapa."
        if momento < valor_anterior:
            return (
                f"O horário não pode ser anterior a '{descricao_anterior}', "
                f"registrada em {timezone.localtime(valor_anterior).strftime('%d/%m/%Y %H:%M')}."
            )

    for campo_posterior, descricao_posterior in ETAPAS_GIRO[indice + 1:]:
        valor_posterior = getattr(giro, campo_posterior)
        if valor_posterior and momento > valor_posterior:
            return (
                f"O horário não pode ser posterior a '{descricao_posterior}', "
                f"registrada em {timezone.localtime(valor_posterior).strftime('%d/%m/%Y %H:%M')}."
            )
    return None


def _registrar_etapa_agora(request, pk, campo, descricao, extras=None):
    giro = get_object_or_404(GiroSala, pk=pk)
    momento = timezone.now()
    erro = _validar_horario_etapa(giro, campo, momento)
    if erro:
        messages.error(request, erro)
    else:
        setattr(giro, campo, momento)
        campos = [campo]
        for nome, valor in (extras or {}).items():
            setattr(giro, nome, valor)
            campos.append(nome)
        giro.save(update_fields=campos)
        messages.success(request, f"{descricao} registrado com sucesso.")

    paciente = get_object_or_404(Paciente, pk=giro.paciente.id)
    return render(request, 'centrocirurgico/giro_sala_novo.html', {
        "paciente": paciente,
        "giro": giro
    })


### begin novo para teste

@login_required
def registrar_etapa_manual(request, pk):

    giro = get_object_or_404(GiroSala, pk=pk)

    paciente = get_object_or_404(
        Paciente,
        pk=giro.paciente.id
    )

    contexto = {
        "paciente": paciente,
        "giro": giro
    }

    if request.method != "POST":
        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            contexto
        )

    etapa = request.POST.get("etapa")
    data_hora = request.POST.get("data_hora")
    tipo_limpeza = request.POST.get("tipo_limpeza")


    # ==========================================================
    # ORDEM CRONOLÓGICA DAS ETAPAS
    # ==========================================================

    etapas = list(ETAPAS_GIRO)


    # ==========================================================
    # CAMPOS PERMITIDOS
    # ==========================================================

    campos_permitidos = dict(etapas)


    # ==========================================================
    # VALIDA ETAPA
    # ==========================================================

    if etapa not in campos_permitidos:

        messages.error(
            request,
            "Etapa inválida para registro."
        )

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            contexto
        )


    # ==========================================================
    # VALIDA DATA/HORA
    # ==========================================================

    if not data_hora:

        messages.error(
            request,
            "Informe a data e o horário da etapa."
        )

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            contexto
        )


    # ==========================================================
    # CONVERTE DATA/HORA
    # ==========================================================

    try:

        data_hora_obj = datetime.fromisoformat(data_hora)

        if timezone.is_naive(data_hora_obj):

            data_hora_obj = timezone.make_aware(
                data_hora_obj,
                timezone.get_current_timezone()
            )

    except (ValueError, TypeError):

        messages.error(
            request,
            "A data e o horário informados são inválidos."
        )

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            contexto
        )


    erro_cronologia = _validar_horario_etapa(giro, etapa, data_hora_obj)
    if erro_cronologia:
        messages.error(request, erro_cronologia)
        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            contexto
        )


    # ==========================================================
    # LOCALIZA A POSIÇÃO DA ETAPA
    # ==========================================================

    indice_etapa = next(
        i
        for i, (campo, descricao) in enumerate(etapas)
        if campo == etapa
    )


    # ==========================================================
    # VALIDA ETAPAS ANTERIORES
    # ==========================================================
    #
    # A data informada não pode ser MENOR que nenhuma
    # etapa anterior já registrada.
    #
    # ==========================================================

    for campo_anterior, descricao_anterior in etapas[:indice_etapa]:

        valor_anterior = getattr(
            giro,
            campo_anterior
        )

        if valor_anterior and data_hora_obj < valor_anterior:

            data_formatada = timezone.localtime(
                valor_anterior
            ).strftime("%d/%m/%Y %H:%M")

            messages.error(
                request,
                (
                    f"{campos_permitidos[etapa]} não pode ser registrado "
                    f"em {timezone.localtime(data_hora_obj).strftime('%d/%m/%Y %H:%M')}, "
                    f"pois a etapa '{descricao_anterior}' já ocorreu em "
                    f"{data_formatada}."
                )
            )

            return render(
                request,
                "centrocirurgico/giro_sala_novo.html",
                contexto
            )


    # ==========================================================
    # VALIDA ETAPAS POSTERIORES
    # ==========================================================
    #
    # Isso também protege a edição de etapas antigas.
    #
    # Exemplo:
    #
    # início cirurgia = 10:30
    # final cirurgia  = 10:00
    #
    # Não pode permitir.
    #
    # ==========================================================

    for campo_posterior, descricao_posterior in etapas[indice_etapa + 1:]:

        valor_posterior = getattr(
            giro,
            campo_posterior
        )

        if valor_posterior and data_hora_obj > valor_posterior:

            data_formatada = timezone.localtime(
                valor_posterior
            ).strftime("%d/%m/%Y %H:%M")

            messages.error(
                request,
                (
                    f"{campos_permitidos[etapa]} não pode ser registrado "
                    f"em {timezone.localtime(data_hora_obj).strftime('%d/%m/%Y %H:%M')}, "
                    f"pois a etapa '{descricao_posterior}' já está registrada em "
                    f"{data_formatada}."
                )
            )

            return render(
                request,
                "centrocirurgico/giro_sala_novo.html",
                contexto
            )


    # ==========================================================
    # GRAVA O HORÁRIO DA ETAPA
    # ==========================================================

    setattr(
        giro,
        etapa,
        data_hora_obj
    )


    # ==========================================================
    # TIPO DE LIMPEZA
    # ==========================================================

    if etapa == "dataInicioLimpeza" and tipo_limpeza:

        giro.tipoLimpeza = tipo_limpeza


    # ==========================================================
    # SALVA
    # ==========================================================

    campos_atualizados = [etapa]

    if etapa == "dataInicioLimpeza" and tipo_limpeza:
        campos_atualizados.append("tipoLimpeza")

    giro.save(
        update_fields=campos_atualizados
    )


    # ==========================================================
    # MENSAGEM
    # ==========================================================

    messages.success(
        request,
        f"{campos_permitidos[etapa]} registrado com sucesso."
    )


    # ==========================================================
    # VOLTA PARA A MESMA TELA
    # ==========================================================

    return render(
        request,
        "centrocirurgico/giro_sala_novo.html",
        {
            "paciente": paciente,
            "giro": giro
        }
    )
def registrar_etapa_manual2(request, pk):

    giro = get_object_or_404(GiroSala, pk=pk)

    paciente = get_object_or_404(
        Paciente,
        pk=giro.paciente.id
    )

    if request.method != "POST":

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            {
                "paciente": paciente,
                "giro": giro
            }
        )

    etapa = request.POST.get("etapa")
    data_hora = request.POST.get("data_hora")

    # Tipo da limpeza
    tipo_limpeza = request.POST.get("tipo_limpeza")


    # ==========================================================
    # CAMPOS PERMITIDOS PARA REGISTRO MANUAL
    # ==========================================================

    campos_permitidos = {

        "dataInicioCirurgia":
            "Início da cirurgia",

        "dataFinalCirurgia":
            "Final da cirurgia",

        "dataSaidaSala":
            "Saída da sala",

        "dataInicioDesmontagemSala":
            "Início da desmontagem",

        "dataFinalDesmontagemSala":
            "Final da desmontagem",

        "dataInicioLimpeza":
            "Início da limpeza",

        "dataFinalLimpeza":
            "Final da limpeza",

        "dataSalaLiberada":
            "Sala liberada",
    }


    # ==========================================================
    # VALIDA ETAPA
    # ==========================================================

    if etapa not in campos_permitidos:

        messages.error(
            request,
            "Etapa inválida para registro."
        )

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            {
                "paciente": paciente,
                "giro": giro
            }
        )


    # ==========================================================
    # VALIDA DATA/HORA
    # ==========================================================

    if not data_hora:

        messages.error(
            request,
            "Informe a data e o horário da etapa."
        )

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            {
                "paciente": paciente,
                "giro": giro
            }
        )


    # ==========================================================
    # CONVERTE DATA/HORA
    # ==========================================================

    try:

        data_hora_obj = datetime.fromisoformat(
            data_hora
        )

        if timezone.is_naive(data_hora_obj):

            data_hora_obj = timezone.make_aware(
                data_hora_obj,
                timezone.get_current_timezone()
            )

    except ValueError:

        messages.error(
            request,
            "A data e o horário informados são inválidos."
        )

        return render(
            request,
            "centrocirurgico/giro_sala_novo.html",
            {
                "paciente": paciente,
                "giro": giro
            }
        )


    # ==========================================================
    # GRAVA O HORÁRIO DA ETAPA
    # ==========================================================

    setattr(
        giro,
        etapa,
        data_hora_obj
    )


    # ==========================================================
    # TIPO DE LIMPEZA
    # ==========================================================

    # Somente a etapa de início da limpeza possui
    # informação sobre o tipo de limpeza.

    if etapa == "dataInicioLimpeza" and tipo_limpeza:

        giro.tipoLimpeza = tipo_limpeza


    # ==========================================================
    # SALVA
    # ==========================================================

    campos_atualizados = [etapa]

    if etapa == "dataInicioLimpeza" and tipo_limpeza:
        campos_atualizados.append("tipoLimpeza")

    giro.save(
        update_fields=campos_atualizados
    )


    # ==========================================================
    # MENSAGEM
    # ==========================================================

    messages.success(
        request,
        f"{campos_permitidos[etapa]} "
        f"registrado com sucesso."
    )


    # ==========================================================
    # VOLTA PARA A MESMA TELA
    # ==========================================================

    return render(
        request,
        "centrocirurgico/giro_sala_novo.html",
        {
            "paciente": paciente,
            "giro": giro
        }
    )


def relatorio_lavagens(request):

    # ==========================================================
    # FILTROS
    # ==========================================================

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    sala = request.GET.get("sala")

    # Se não informar as datas, utilizar o mês atual
    if not data_inicio and not data_fim:

        hoje = date.today()

        data_inicio = hoje.replace(day=1)

        ultimo_dia = calendar.monthrange(
            hoje.year,
            hoje.month
        )[1]

        data_fim = hoje.replace(day=ultimo_dia)


    # ==========================================================
    # QUERY BASE
    # ==========================================================

    queryset = GiroSala.objects.all()


    # ==========================================================
    # FILTRO DATA INICIAL
    # ==========================================================

    if data_inicio:

        queryset = queryset.filter(
            cirurgia__data__gte=data_inicio
        )


    # ==========================================================
    # FILTRO DATA FINAL
    # ==========================================================

    if data_fim:

        queryset = queryset.filter(
            cirurgia__data__lte=data_fim
        )


    # ==========================================================
    # FILTRO SALA
    # ==========================================================

    if sala:

        queryset = queryset.filter(
            cirurgia__sala=sala
        )


    # ==========================================================
    # RELATÓRIO
    # ==========================================================

    relatorio = (
        queryset
        .filter(
            tipoLimpeza__isnull=False
        )
        .values(
            "cirurgia__data",
            "cirurgia__sala"
        )
        .annotate(

            concorrente=Count(
                "id",
                filter=Q(
                    tipoLimpeza__iexact="C"
                )
            ),

            terminal=Count(
                "id",
                filter=Q(
                    tipoLimpeza__iexact="T"
                )
            ),

            total=Count("id"),
        )
        .order_by(
            "cirurgia__data",
            "cirurgia__sala"
        )
    )


    # ==========================================================
    # LISTA DE SALAS PARA O FILTRO
    # ==========================================================

    salas = (
        GiroSala.objects
        .values_list(
            "cirurgia__sala",
            flat=True
        )
        .distinct()
        .order_by(
            "cirurgia__sala"
        )
    )


    # ==========================================================
    # TOTAL GERAL
    # ==========================================================

    totais = queryset.filter(
        tipoLimpeza__isnull=False
    ).aggregate(

        concorrente=Count(
            "id",
            filter=Q(
                tipoLimpeza__iexact="C"
            )
        ),

        terminal=Count(
            "id",
            filter=Q(
                tipoLimpeza__iexact="T"
            )
        ),

        total=Count("id"),
    )


    # ==========================================================
    # RENDER
    # ==========================================================

    return render(
        request,
        "centrocirurgico/relatorio_lavagens.html",
        {
            "relatorio": relatorio,
            "salas": salas,

            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "sala_selecionada": sala,

            "totais": totais,
        }
    )

@login_required
def mapa_cirurgico_list_novo(request):
    data_mapa = request.GET.get("data_mapa")
    dados = []

    if data_mapa:
        dados = buscar_mapa_cirurgico_aghu(data=data_mapa)

    def serializar_data(valor, formato):
        return valor.strftime(formato) if valor else ""

    for dado in dados:
        inicio = dado.get("data_inicio_cirurgia")
        dado["suspensao_token"] = signing.dumps(
            {
                "prontuario": str(dado.get("prontuario") or ""),
                "nome": dado.get("nome_paciente") or "",
                "data_nascimento": serializar_data(
                    dado.get("data_nascimento"), "%Y-%m-%d"
                ),
                "especialidade": dado.get("especialidade") or "",
                "procedimento": dado.get("procedimento") or "",
                "medico": dado.get("medico") or "",
                "sala": dado.get("sala") or "",
                "data_cirurgia": serializar_data(inicio, "%Y-%m-%d"),
                "hora_cirurgia": serializar_data(inicio, "%H:%M:%S"),
            },
            salt="centrocirurgico.suspensao.mapa",
        )

    return render(
        request,
        "centrocirurgico/mapa_cirurgico_listar_novo.html",
        {"mapa": dados},
    )

def giro_sala_novo(request):

    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    data_nascimento = request.POST.get('data_nascimento', '')
    especialidade = request.POST.get('especialidade', '')
    procedimento = request.POST.get('procedimento', '')
    data_cirurgia = request.POST.get('data_cirurgia', '')
    hora_cirurgia = request.POST.get('hora_cirurgia', '')
    medico = request.POST.get('medico', '')
    sala = request.POST.get('sala', '')

    if data_nascimento:
        data_nascimento = timezone.datetime.strptime(data_nascimento, '%d/%m/%Y').date()

    if data_cirurgia:
        data_cirurgia = timezone.datetime.strptime(data_cirurgia, '%d/%m/%Y').date()

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

    giro, created = GiroSala.objects.get_or_create(paciente=paciente, cirurgia=cirurgia)

    return render(request, 'centrocirurgico/giro_sala_novo.html', {
        "paciente": paciente,
        "giro": giro,
        'data': data_cirurgia,
        'hora': hora_cirurgia
    })



### end novo

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
            v_cir.lto_lto_id as leito,
            situacao,
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
    

def giro_sala_view(request, paciente_id):

    paciente = Paciente.objects.get(id=paciente_id)

    giro, created = GiroSala.objects.get_or_create(paciente=paciente)

    return render(request, 'centrocirurgico/registrar_giro.html', {
        "paciente": paciente,
        "giro": giro
    })
def registrar_giro_novo(request):

    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    data_nascimento = request.POST.get('data_nascimento', '')
    especialidade = request.POST.get('especialidade', '')
    procedimento = request.POST.get('procedimento', '')
    data_cirurgia = request.POST.get('data_cirurgia', '')
    hora_cirurgia = request.POST.get('hora_cirurgia', '')
    medico = request.POST.get('medico', '')
    sala = request.POST.get('sala', '')

    if data_nascimento:
        data_nascimento = timezone.datetime.strptime(data_nascimento, '%d/%m/%Y').date()

    if data_cirurgia:
        data_cirurgia = timezone.datetime.strptime(data_cirurgia, '%d/%m/%Y').date()

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

    giro, created = GiroSala.objects.get_or_create(paciente=paciente, cirurgia=cirurgia)

    return render(request, 'centrocirurgico/registrar_giro_novo.html', {
        "paciente": paciente,
        "giro": giro
    })

def registrar_giro(request):

    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    data_nascimento = request.POST.get('data_nascimento', '')
    especialidade = request.POST.get('especialidade', '')
    procedimento = request.POST.get('procedimento', '')
    data_cirurgia = request.POST.get('data_cirurgia', '')
    hora_cirurgia = request.POST.get('hora_cirurgia', '')
    medico = request.POST.get('medico', '')
    sala = request.POST.get('sala', '')

    if data_nascimento:
        data_nascimento = timezone.datetime.strptime(data_nascimento, '%d/%m/%Y').date()

    if data_cirurgia:
        data_cirurgia = timezone.datetime.strptime(data_cirurgia, '%d/%m/%Y').date()

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

    print(paciente)

    giro, created = GiroSala.objects.get_or_create(paciente=paciente, cirurgia=cirurgia)

    return render(request, 'centrocirurgico/registrar_giro.html', {
        "paciente": paciente,
        "giro": giro
    })



def registrar_giro2(request, pk):
    giro = get_object_or_404(GiroSala, pk=pk)

    return render(request, 'centrocirurgico/registrar_giro.html', {
        'giro': giro,
    })

def registrar_etapa(request, pk, etapa):
    giro = get_object_or_404(GiroSala, pk=pk)

    # Confirma se a etapa realmente existe no modelo
    if hasattr(giro, etapa):
        setattr(giro, etapa, timezone.now())
        giro.save()
    else:
        raise ValueError(f"Etapa inválida: {etapa}")

    # Sempre volta para a mesma tela
    return redirect('centrocirurgico:registrar_giro', pk=pk)

@login_required
def mapa_cirurgico_list(request):
    data_mapa = request.GET.get("data_mapa")
    dados = []

    if data_mapa:
        dados = buscar_mapa_cirurgico_aghu(data=data_mapa)

    def serializar_data(valor, formato):
        return valor.strftime(formato) if valor else ""

    for dado in dados:
        inicio = dado.get("data_inicio_cirurgia")
        dado["suspensao_token"] = signing.dumps(
            {
                "prontuario": str(dado.get("prontuario") or ""),
                "nome": dado.get("nome_paciente") or "",
                "data_nascimento": serializar_data(
                    dado.get("data_nascimento"), "%Y-%m-%d"
                ),
                "especialidade": dado.get("especialidade") or "",
                "procedimento": dado.get("procedimento") or "",
                "medico": dado.get("medico") or "",
                "sala": dado.get("sala") or "",
                "data_cirurgia": serializar_data(inicio, "%Y-%m-%d"),
                "hora_cirurgia": serializar_data(inicio, "%H:%M:%S"),
            },
            salt="centrocirurgico.suspensao.mapa",
        )

    return render(
        request,
        "centrocirurgico/mapa_cirurgico_listar.html",
        {"mapa": dados},
    )

def registrar_inicio_anestesia(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataInicioAnestesia", "Início da anestesia"
    )
def registrar_inicio_cirurgia(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataInicioCirurgia", "Início da cirurgia"
    )
def registrar_final_cirurgia(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataFinalCirurgia", "Final da cirurgia"
    )
def registrar_saida_sala(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataSaidaSala", "Saída da sala"
    )
def registrar_inicio_desmontagem(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataInicioDesmontagemSala", "Início da desmontagem"
    )
def registrar_final_desmontagem(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataFinalDesmontagemSala", "Final da desmontagem"
    )
def registrar_inicio_limpeza_tipo(request, tipo, pk):
    return _registrar_etapa_agora(
        request, pk, "dataInicioLimpeza", "Início da limpeza",
        extras={"tipoLimpeza": tipo},
    )
def registrar_inicio_limpeza(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataInicioLimpeza", "Início da limpeza",
        extras={"tipoLimpeza": "C"},
    )
def registrar_inicio_limpeza_terminal(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataInicioLimpeza", "Início da limpeza terminal",
        extras={"tipoLimpeza": "T"},
    )
def registrar_final_limpeza(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataFinalLimpeza", "Final da limpeza"
    )
def registrar_sala_liberada(request, pk):
    return _registrar_etapa_agora(
        request, pk, "dataSalaLiberada", "Sala liberada"
    )
def giro(request):

    data_mapa = timezone.now().date().strftime("%Y-%m-%d")

    data = timezone.now().date().strftime("%d/%m/%Y")

    dados = []
    mapa = []
    if request.method == 'GET':
        if data_mapa:
            dados = buscar_mapa_cirurgico_aghu(data=data_mapa)

        mapa = []

    if dados:
        sala_liberada = 'N'
        for d in dados:

            prontuario = d['prontuario']
            procedimento = d['procedimento']
            situacao = d['situacao']
            if situacao == 'CANC':
                situacao = 'CANCELADA'

            if situacao == 'RZDA':
                situacao = 'REALIZADA'

            if situacao ==  'AGND':
                situacao = 'AGENDADA'
            # Buscar o paciente correspondente
            paciente = Paciente.objects.filter(prontuario=prontuario).first()

            # Verificar existência no GiroSala
            existe = False
            if paciente:
                existe = GiroSala.objects.filter(
                    paciente=paciente,
                    cirurgia__procedimento=procedimento
                ).exists()

                sala_liberada = GiroSala.objects.filter(
                    paciente=paciente,
                    cirurgia__procedimento=procedimento,
                    dataSalaLiberada__isnull=False
                ).exists()



            # Criar novo dict inserindo 'existe'
            registro = {
                **d,  # copia todos os campos originais
                'situacao': situacao,
                'existe': 'S' if existe else 'N',
                'salaLiberada': 'S' if sala_liberada else 'N'
            }

            # Adiciona ao mapa
            mapa.append(registro)

    context = {
        'mapa': mapa,
        'data':data,
        
    }

    return render(request, 'centrocirurgico/pacientes.html', context)
    

def giro_sala(request):

    nome = request.POST.get('nome', '')
    prontuario = request.POST.get('prontuario', '')
    data_nascimento = request.POST.get('data_nascimento', '')
    especialidade = request.POST.get('especialidade', '')
    procedimento = request.POST.get('procedimento', '')
    data_cirurgia = request.POST.get('data_cirurgia', '')
    hora_cirurgia = request.POST.get('hora_cirurgia', '')
    medico = request.POST.get('medico', '')
    sala = request.POST.get('sala', '')

    if data_nascimento:
        data_nascimento = timezone.datetime.strptime(data_nascimento, '%d/%m/%Y').date()

    if data_cirurgia:
        data_cirurgia = timezone.datetime.strptime(data_cirurgia, '%d/%m/%Y').date()

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

    giro, created = GiroSala.objects.get_or_create(paciente=paciente, cirurgia=cirurgia)

    return render(request, 'centrocirurgico/giro_sala.html', {
        "paciente": paciente,
        "giro": giro
    })


# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import LimpezaTerminal
from datetime import datetime, timedelta


@login_required
def limpeza_dashboard(request):
    hoje = datetime.today().date()
    ultimos_7_dias = hoje - timedelta(days=7)

    total_limpezas = LimpezaTerminal.objects.count()
    concluidas = LimpezaTerminal.objects.filter(
        usuario_enfermagem__isnull=False, 
        usuario_higienizacao__isnull=False
    ).count()
    
    hoje_limpezas = LimpezaTerminal.objects.filter(data=hoje).count()

    context = {
        'total_limpezas': total_limpezas,
        'concluidas': concluidas,
        'hoje_limpezas': hoje_limpezas,
        'taxa_conclusao': round((concluidas / total_limpezas * 100), 1) if total_limpezas > 0 else 0,
    }
    return render(request, 'centrocirurgico/limpeza/limpeza_dashboard.html', context)


@login_required
def limpeza_list(request):
    limpezas = LimpezaTerminal.objects.all()

    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    centro = request.GET.get('centro_cirurgico')
    status = request.GET.get('status')

    if data_inicio:
        limpezas = limpezas.filter(data__gte=data_inicio)
    if data_fim:
        limpezas = limpezas.filter(data__lte=data_fim)
    if centro:
        limpezas = limpezas.filter(centro_cirurgico=centro)

    # Filtro por Status (corrigido)
    if status == 'concluida':
        limpezas = limpezas.filter(
            fim_enfermagem__isnull=False,
            fim_higienizacao__isnull=False
        )
    elif status == 'andamento':
        limpezas = limpezas.filter(
            models.Q(inicio_enfermagem__isnull=False) | 
            models.Q(inicio_higienizacao__isnull=False)
        ).exclude(
            fim_enfermagem__isnull=False,
            fim_higienizacao__isnull=False
        )
    elif status == 'pendente':
        limpezas = limpezas.filter(
            inicio_enfermagem__isnull=True,
            inicio_higienizacao__isnull=True
        )

    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(limpezas.order_by('-data', '-criado_em'), 20)
    page_number = request.GET.get('page')
    limpezas_page = paginator.get_page(page_number)

    context = {
        'limpezas': limpezas_page,   # ← Use este nome no template
        'centros': LimpezaTerminal.CENTRO_CIRURGICO_CHOICES,
    }
    return render(request, 'centrocirurgico/limpeza/limpeza_list.html', context)


@login_required
def limpeza_delete(request, pk):
    limpeza = get_object_or_404(LimpezaTerminal, pk=pk)
    if request.method == 'POST':
        limpeza.delete()
        messages.success(request, 'Registro excluído com sucesso!')
        return redirect('centrocirurgico:limpeza-list')
    
    return render(request, 'centrocirurgico/limpeza/limpeza_confirm_delete.html', {'limpeza': limpeza})

@login_required
def limpeza_create(request):
    if request.method == 'POST':
        try:
            acao = request.POST.get('acao')      # enfermagem ou higienizacao
            tipo = request.POST.get('tipo')      # inicio ou fim

            limpeza = LimpezaTerminal.objects.create(
                data=date.today(),
                centro_cirurgico=request.POST.get('centro_cirurgico'),
                sala=request.POST.get('sala'),
                criado_por=request.user
            )

            agora = timezone.now()

            if acao == 'enfermagem':
                if tipo == 'inicio':
                    limpeza.inicio_enfermagem = agora
                    limpeza.usuario_inicio_enfermagem = request.user
                    msg = 'Início da limpeza da Enfermagem registrado!'
                else:  # fim
                    limpeza.fim_enfermagem = agora
                    limpeza.usuario_fim_enfermagem = request.user
                    msg = 'Fim da limpeza da Enfermagem registrado!'

            elif acao == 'higienizacao':
                if tipo == 'inicio':
                    limpeza.inicio_higienizacao = agora
                    limpeza.usuario_inicio_higienizacao = request.user
                    msg = 'Início da limpeza da Higienização registrado!'
                else:  # fim
                    limpeza.fim_higienizacao = agora
                    limpeza.usuario_fim_higienizacao = request.user
                    msg = 'Fim da limpeza da Higienização registrado!'

            limpeza.save()
            messages.success(request, msg)
            return redirect('centrocirurgico:limpeza-list')

        except Exception as e:
            messages.error(request, f'Erro ao registrar: {str(e)}')

    # GET
    centros = LimpezaTerminal.CENTRO_CIRURGICO_CHOICES
    return render(request, 'centrocirurgico/limpeza/limpeza_form.html', {
        'centros': centros,
        'hoje': date.today()
    })


@login_required
def limpeza_update(request, pk):
    limpeza = get_object_or_404(LimpezaTerminal, pk=pk)

    if request.method == 'POST':
        try:
            acao = request.POST.get('acao')
            tipo = request.POST.get('tipo')
            agora = timezone.now()

            if acao == 'enfermagem':
                if tipo == 'inicio' and not limpeza.inicio_enfermagem:
                    limpeza.inicio_enfermagem = agora
                    limpeza.usuario_inicio_enfermagem = request.user
                elif tipo == 'fim' and limpeza.inicio_enfermagem and not limpeza.fim_enfermagem:
                    limpeza.fim_enfermagem = agora
                    limpeza.usuario_fim_enfermagem = request.user

            elif acao == 'higienizacao':
                if tipo == 'inicio' and not limpeza.inicio_higienizacao:
                    limpeza.inicio_higienizacao = agora
                    limpeza.usuario_inicio_higienizacao = request.user
                elif tipo == 'fim' and limpeza.inicio_higienizacao and not limpeza.fim_higienizacao:
                    limpeza.fim_higienizacao = agora
                    limpeza.usuario_fim_higienizacao = request.user

            limpeza.save()
            messages.success(request, 'Registro atualizado com sucesso!')
            return redirect('centrocirurgico:limpeza-detail', pk=limpeza.pk)

        except Exception as e:
            messages.error(request, f'Erro ao atualizar: {str(e)}')

    centros = LimpezaTerminal.CENTRO_CIRURGICO_CHOICES
    return render(request, 'centrocirurgico/limpeza/limpeza_form_update.html', {
        'limpeza': limpeza,
        'centros': centros,
        'hoje': limpeza.data
    })

@login_required
def limpeza_detail(request, pk):
    limpeza = get_object_or_404(LimpezaTerminal, pk=pk)
    return render(request, 'centrocirurgico/limpeza/limpeza_detail.html', {'limpeza': limpeza})


@login_required
def lista_pedidos_cirurgia(request):
    return render( request, "centrocirurgico/cirurgia/lista.html" )


@login_required
def novo_pedido_cirurgia(request):
    return render( request,"centrocirurgico/cirurgia/create.html" )

def salvar_observacao_giro(request, pk):
    giro = get_object_or_404(GiroSala, pk=pk)
    giro.observacao = request.POST.get('observacao')
    giro.save()
    paciente = get_object_or_404(Paciente, pk=giro.paciente.id)
    messages.success(request, "Observação registrada com sucesso.")
    return render(request, 'centrocirurgico/giro_sala.html', {
        "paciente": paciente,
        "giro": giro
    })


def indicador_giro_sala(request):

    data_inicio = timezone.now() - timedelta(days=30)

    queryset = GiroSala.objects.filter(

        dataInicioCirurgia__gte=data_inicio,

        dataSaidaSala__isnull=False,

        dataSalaLiberada__isnull=False,

        dataSalaLiberada__gt=F("dataSaidaSala"),

    )

    context = GiroSalaService.calcular(queryset)

    return render(

        request,

        "centrocirurgico/indicadores/indicador_giro_sala.html",

        context,

    )

from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Max,
    Min,
)

from django.db.models.functions import Extract

def detalhe_giro_sala(request, sala):

    inicio = timezone.now() - timedelta(days=30)

    qs = (
        GiroSala.objects
        .select_related("cirurgia", "paciente")
        .filter(
            cirurgia__sala=sala,
            dataInicioCirurgia__gte=inicio,
            dataSaidaSala__isnull=False,
            dataSalaLiberada__isnull=False,
            dataSalaLiberada__gt=F("dataSaidaSala"),
        )
        .annotate(
            giro=ExpressionWrapper(
                F("dataSalaLiberada") - F("dataSaidaSala"),
                output_field=DurationField()
            ),

            desmontagem=ExpressionWrapper(
                F("dataFinalDesmontagemSala") - F("dataInicioDesmontagemSala"),
                output_field=DurationField()
            ),

            espera_limpeza=ExpressionWrapper(
                F("dataInicioLimpeza") - F("dataFinalDesmontagemSala"),
                output_field=DurationField()
            ),

            limpeza=ExpressionWrapper(
                F("dataFinalLimpeza") - F("dataInicioLimpeza"),
                output_field=DurationField()
            ),

            liberacao=ExpressionWrapper(
                F("dataSalaLiberada") - F("dataFinalLimpeza"),
                output_field=DurationField()
            ),
        )
    )

    resumo = qs.annotate(
        giro_min=Extract("giro", "epoch") / 60
    ).aggregate(
        media=Avg("giro_min"),
        melhor=Min("giro_min"),
        pior=Max("giro_min"),
        total=Count("id")
    )

    ####################################################
    # Especialidades
    ####################################################

    especialidades = list(
        qs.values("cirurgia__especialidade")
        .annotate(
            quantidade=Count("id")
        )
        .order_by("-quantidade")
    )

    ####################################################
    # Cirurgiões
    ####################################################

    medicos = list(
        qs.values("cirurgia__medico")
        .annotate(
            quantidade=Count("id")
        )
        .order_by("-quantidade")
    )

    ####################################################
    # Evolução diária
    ####################################################

    tendencia = list(
        qs.annotate(
            giro_min=Extract("giro", "epoch") / 60
        )
        .values("dataInicioCirurgia__date")
        .annotate(
            media=Avg("giro_min")
        )
        .order_by("dataInicioCirurgia__date")
    )

    ####################################################
    # Tempo médio de cada etapa
    ####################################################
    etapas = qs.annotate(
        desmontagem_min=Extract("desmontagem", "epoch") / 60,
        espera_min=Extract("espera_limpeza", "epoch") / 60,
        limpeza_min=Extract("limpeza", "epoch") / 60,
        liberacao_min=Extract("liberacao", "epoch") / 60,
    ).aggregate(
        desmontagem=Avg("desmontagem_min"),
        espera=Avg("espera_min"),
        limpeza=Avg("limpeza_min"),
        liberacao=Avg("liberacao_min"),
    )

    ####################################################
    # Lista das cirurgias
    ####################################################

    cirurgias = []
    for item in qs.order_by("-dataInicioCirurgia"):
        giro = round(
            (item.dataSalaLiberada-item.dataSaidaSala).total_seconds()/60, 1
        )
        if giro <= 20:
            status = "Excelente"
            cor = "success"
        elif giro <= 30:
            status = "Bom"
            cor = "primary"
        else:
            status = "Crítico"
            cor = "danger"

        cirurgias.append({
            "data": item.dataInicioCirurgia.strftime("%d/%m/%Y"),
            "hora": item.dataInicioCirurgia.strftime("%H:%M"),
            "paciente": str(item.paciente),
            "procedimento": item.cirurgia.procedimento,
            "especialidade": item.cirurgia.especialidade,
            "medico": item.cirurgia.medico,
            "saida": item.dataSaidaSala.strftime("%H:%M"),
            "liberada": item.dataSalaLiberada.strftime("%H:%M"),
            "giro": giro,
            "status": status,
            "cor": cor
        })

    return JsonResponse({
        "resumo":{
            "media":round(resumo["media"] or 0,1),
            "melhor":round(resumo["melhor"] or 0,1),
            "pior":round(resumo["pior"] or 0,1),
            "total":resumo["total"]
        },
        "etapas":{
            "desmontagem":round(etapas["desmontagem"] or 0,1),
            "espera":round(etapas["espera"] or 0,1),
            "limpeza":round(etapas["limpeza"] or 0,1),
            "liberacao":round(etapas["liberacao"] or 0,1)
        },
        "especialidades":especialidades,
        "medicos":medicos,
        "tendencia":tendencia,
        "cirurgias":cirurgias
    })

def indicador_tempo_sala(request):
    MINUTOS_DIA_SALA = 690  # 07:30 às 19:00 = 11h30m = 690 minutos
    
    # Define o limite de 30 dias atrás
    trinta_dias_atras = timezone.now() - timedelta(days=30)

    # Filtra os dados de GiroSala dos últimos 30 dias com base na data de início da cirurgia
    salas_qs = (
        GiroSala.objects.filter(
            dataInicioCirurgia__gte=trinta_dias_atras,
            dataInicioCirurgia__isnull=False,
            dataSalaLiberada__isnull=False
        )
        .values('cirurgia__sala')
        .annotate(
            total_cirurgias=Count('id'),
            tempo_total_utilizado=Sum(
                ExpressionWrapper(
                    F('dataSalaLiberada') - F('dataInicioCirurgia'),
                    output_field=DurationField()
                )
            ),
            dias_unicos=Count('cirurgia__data', distinct=True)
        )
    )

    dados_salas = []
    soma_percentuais = 0
    total_salas = 0

    for s in salas_qs:
        sala_nome = s['cirurgia__sala']
        total_cirurgias = s['total_cirurgias']
        
        # Converte o timedelta acumulado para minutos totais
        duration = s['tempo_total_utilizado'] or timedelta(0)
        minutos_utilizados = duration.total_seconds() / 60

        # Tempo disponível baseado nos dias únicos que a sala operou nos últimos 30 dias
        dias = s['dias_unicos'] or 0
        minutos_disponiveis = dias * MINUTOS_DIA_SALA

        # Percentual de ocupação da sala
        percentual = (minutos_utilizados / minutos_disponiveis * 100) if minutos_disponiveis > 0 else 0

        soma_percentuais += percentual
        total_salas += 1

        if percentual <= 40:
            badge = "warning"
        elif percentual <= 70:
            badge = "primary"
        elif percentual <= 100:
            badge = "success"
        else :
            badge = "danger"

        dados_salas.append({
            'sala': sala_nome,
            'cirurgias': total_cirurgias,
            'minutos_utilizados': round(minutos_utilizados, 1),
            'horas_utilizadas': round(minutos_utilizados / 60, 1),
            'minutos_disponiveis': minutos_disponiveis,
            'percentual': round(percentual, 1),
            'badge': badge #'success' if percentual <= 85 else ('warning' if percentual <= 100 else 'danger')
        })

    # Média geral de ocupação entre as salas
    media_geral_percentual = round(soma_percentuais / total_salas, 1) if total_salas > 0 else 0

    context = {
        'salas': dados_salas,
        'media_geral_percentual': media_geral_percentual,
    }
    return render(request, 'centrocirurgico/indicadores/tempo_sala.html', context)


from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, ExpressionWrapper, DurationField, Count, F
from .models import GiroSala

def api_tempo_sala(request, sala_nome):
    trinta_dias_atras = timezone.now() - timedelta(days=30)
    MINUTOS_DIA_SALA = 690

    # Filtra os registros da sala específica nos últimos 30 dias
    registros = GiroSala.objects.filter(
        cirurgia__sala=sala_nome,
        dataInicioCirurgia__gte=trinta_dias_atras,
        dataInicioCirurgia__isnull=False,
        dataSalaLiberada__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente')

    total_cirurgias = registros.count()
    
    # Cálculo do tempo total utilizado
    tempo_total = timedelta(0)
    cirurgias_data = []

    for reg in registros:
        # Tempo da cirurgia atual (dataSalaLiberada - dataInicioCirurgia)
        duracao = reg.dataSalaLiberada - reg.dataInicioCirurgia
        minutos_cirurgia = duracao.total_seconds() / 60
        tempo_total += duracao

        cirurgias_data.append({
            'data': reg.cirurgia.data.strftime('%d/%m/%Y') if reg.cirurgia.data else '',
            'procedimento': reg.cirurgia.procedimento or '-',
            'medico': reg.cirurgia.medico or '-',
            'especialidade': reg.cirurgia.especialidade or '-',
            'duracao_horas': round(minutos_cirurgia / 60, 1),
            'duracao_minutos': round(minutos_cirurgia, 1)
        })

    minutos_utilizados = tempo_total.total_seconds() / 60
    
    # Dias únicos em que houve cirurgia nesta sala no período
    dias_unicos = registros.values('cirurgia__data').distinct().count()
    minutos_disponiveis = dias_unicos * MINUTOS_DIA_SALA
    
    percentual = (minutos_utilizados / minutos_disponiveis * 100) if minutos_disponiveis > 0 else 0
    badge = 'success' if percentual <= 85 else ('warning' if percentual <= 100 else 'danger')

    data = {
        'resumo': {
            'total_cirurgias': total_cirurgias,
            'horas_utilizadas': round(minutos_utilizados / 60, 1),
            'minutos_utilizados': round(minutos_utilizados, 1),
            'percentual': round(percentual, 1),
            'badge': badge
        },
        'cirurgias': cirurgias_data
    }
    return JsonResponse(data)

def indicador_tempo_cirurgia(request):
    trinta_dias_atras = timezone.now() - timedelta(days=30)

    # Captura os filtros da requisição GET
    filtro_medico = request.GET.get('medico', '')
    filtro_especialidade = request.GET.get('especialidade', '')
    filtro_procedimento = request.GET.get('procedimento', '')

    # Query base dos últimos 30 dias com tempos de início e fim válidos
    queryset = GiroSala.objects.filter(
        dataInicioCirurgia__gte=trinta_dias_atras,
        dataInicioCirurgia__isnull=False,
        dataFinalCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente')

    # Aplica os filtros opcionais
    if filtro_medico:
        queryset = queryset.filter(cirurgia__medico__icontains=filtro_medico)
    if filtro_especialidade:
        queryset = queryset.filter(cirurgia__especialidade__icontains=filtro_especialidade)
    if filtro_procedimento:
        queryset = queryset.filter(cirurgia__procedimento__icontains=filtro_procedimento)

    # Agrupamento principal por Procedimento
    procedimentos_agrupados = (
        queryset.values('cirurgia__procedimento')
        .annotate(
            total_cirurgias=Count('id'),
            tempo_medio_duration=Avg(
                ExpressionWrapper(
                    F('dataFinalCirurgia') - F('dataInicioCirurgia'),
                    output_field=DurationField()
                )
            )
        )
        .order_by('cirurgia__procedimento')
        #.order_by('-total_cirurgias')
    )

    dados_procedimentos = []
    soma_total_minutos = 0
    total_geral_cirurgias = 0

    for p in procedimentos_agrupados:
        proc_nome = p['cirurgia__procedimento'] or 'Não informado'
        total = p['total_cirurgias']
        
        duration = p['tempo_medio_duration'] or timedelta(0)
        media_minutos = duration.total_seconds() / 60

        soma_total_minutos += (media_minutos * total)
        total_geral_cirurgias += total

        dados_procedimentos.append({
            'procedimento': proc_nome,
            'quantidade': total,
            'media_minutos': round(media_minutos, 1),
            'media_horas': round(media_minutos / 60, 1),
        })

    # Média geral ponderada do período
    media_geral_minutos = round(soma_total_minutos / total_geral_cirurgias, 1) if total_geral_cirurgias > 0 else 0

    # Listas distintas para alimentar os selects do filtro
    medicos_disponiveis = GiroSala.objects.filter(dataInicioCirurgia__gte=trinta_dias_atras).values_list('cirurgia__medico', flat=True).distinct().exclude(cirurgia__medico__isnull=True).order_by('cirurgia__medico')
    especialidades_disponiveis = GiroSala.objects.filter(dataInicioCirurgia__gte=trinta_dias_atras).values_list('cirurgia__especialidade', flat=True).distinct().exclude(cirurgia__especialidade__isnull=True).order_by('cirurgia__especialidade')
    procedimentos_disponiveis = GiroSala.objects.filter(dataInicioCirurgia__gte=trinta_dias_atras).values_list('cirurgia__procedimento', flat=True).distinct().exclude(cirurgia__procedimento__isnull=True).order_by('cirurgia__procedimento')

    context = {
        'procedimentos': dados_procedimentos,
        'total_cirurgias': total_geral_cirurgias,
        'media_geral_minutos': media_geral_minutos,
        'media_geral_horas': round(media_geral_minutos / 60, 1),
        'medicos': medicos_disponiveis,
        'especialidades': especialidades_disponiveis,
        'procedimentos_lista': procedimentos_disponiveis,
        'filtro_medico': filtro_medico,
        'filtro_especialidade': filtro_especialidade,
        'filtro_procedimento': filtro_procedimento,
    }
    
    return render(request, 'centrocirurgico/indicadores/tempo_cirurgia.html', context)


def api_tempo_cirurgia_por_procedimento(request, procedimento_nome):
    trinta_dias_atras = timezone.now() - timedelta(days=30)
    
    # Captura os filtros opcionais passados na query string da requisição fetch
    filtro_medico = request.GET.get('medico', '')
    filtro_especialidade = request.GET.get('especialidade', '')

    # Query base filtrando pelo procedimento e período
    registros = GiroSala.objects.filter(
        cirurgia__procedimento=procedimento_nome,
        dataInicioCirurgia__gte=trinta_dias_atras,
        dataInicioCirurgia__isnull=False,
        dataFinalCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente').order_by('-cirurgia__data')

    # Aplica os filtros adicionais caso tenham sido informados
    if filtro_medico:
        registros = registros.filter(cirurgia__medico__icontains=filtro_medico)
    if filtro_especialidade:
        registros = registros.filter(cirurgia__especialidade__icontains=filtro_especialidade)

    cirurgias_data = []
    soma = timedelta(0)

    for reg in registros:
        duracao = reg.dataFinalCirurgia - reg.dataInicioCirurgia
        minutos = duracao.total_seconds() / 60
        soma += duracao

        cirurgias_data.append({
            'data': reg.cirurgia.data.strftime('%d/%m/%Y') if reg.cirurgia.data else '',
            'paciente': reg.paciente.nome if reg.paciente else '-',
            'medico': reg.cirurgia.medico or '-',
            'especialidade': reg.cirurgia.especialidade or '-',
            'sala': reg.cirurgia.sala or '-',
            'duracao_minutos': round(minutos, 1),
            'duracao_horas': round(minutos / 60, 1)
        })

    total = registros.count()
    media_min = (soma.total_seconds() / 60 / total) if total > 0 else 0

    return JsonResponse({
        'resumo': {
            'total': total,
            'media': round(media_min, 1),
            'horas': round(media_min / 60, 1)
        },
        'cirurgias': cirurgias_data
    })


def exportar_relatorio_tempo_cirurgia_pdf(request):
    # Configuração da resposta HTTP para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_tempo_cirurgia.pdf"'

    # Criação do documento (Padrão Letter, margens de 36pt)
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elementos = []

    # Estilos
    styles = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1f2937'), alignment=1)
    subtitulo_estilo = ParagraphStyle('SubTitulo', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#6b7280'), alignment=1)
    cabecalho_tabela = ParagraphStyle('CabTabela', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')
    texto_celula = ParagraphStyle('TxtCel', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#374151'))
    texto_celula_bold = ParagraphStyle('TxtCelBold', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#111827'), fontName='Helvetica-Bold')

    # Captura de Filtros da Requisição
    filtro_medico = request.GET.get('medico', '')
    filtro_especialidade = request.GET.get('especialidade', '')
    filtro_procedimento = request.GET.get('procedimento', '')

    trinta_dias_atras = timezone.now() - timedelta(days=30)
    queryset = GiroSala.objects.filter(
        dataInicioCirurgia__gte=trinta_dias_atras,
        dataInicioCirurgia__isnull=False,
        dataFinalCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente')

    if filtro_medico:
        queryset = queryset.filter(cirurgia__medico__icontains=filtro_medico)
    if filtro_especialidade:
        queryset = queryset.filter(cirurgia__especialidade__icontains=filtro_especialidade)
    if filtro_procedimento:
        queryset = queryset.filter(cirurgia__procedimento__icontains=filtro_procedimento)

    # Dados Agrupados por Procedimento
    procedimentos_agrupados = (
        queryset.values('cirurgia__procedimento')
        .annotate(
            total_cirurgias=Count('id'),
            tempo_medio_duration=Avg(
                ExpressionWrapper(
                    F('dataFinalCirurgia') - F('dataInicioCirurgia'),
                    output_field=DurationField()
                )
            )
        )
        .order_by('-total_cirurgias')
    )

    # Cabeçalho do Relatório
    elementos.append(Paragraph("Relatório de Tempo Médio de Cirurgia por Procedimento", titulo_estilo))
    elementos.append(Paragraph("Período de referência: Últimos 30 dias", subtitulo_estilo))
    
    # Informações de Filtros Aplicados (se houver)
    filtros_texto = []
    if filtro_medico: filtros_texto.append(f"Médico: {filtro_medico}")
    if filtro_especialidade: filtros_texto.append(f"Especialidade: {filtro_especialidade}")
    if filtro_procedimento: filtros_texto.append(f"Procedimento: {filtro_procedimento}")
    
    if filtros_texto:
        elementos.append(Spacer(1, 4))
        elementos.append(Paragraph(f"<b>Filtros aplicados:</b> {' | '.join(filtros_texto)}", subtitulo_estilo))

    elementos.append(Spacer(1, 15))

    # Montagem da Tabela PDF
    dados_tabela = [[
        Paragraph("Procedimento", cabecalho_tabela),
        Paragraph("Qtd. Cirurgias", cabecalho_tabela),
        Paragraph("Tempo Médio", cabecalho_tabela)
    ]]

    soma_total_minutos = 0
    total_geral_cirurgias = 0

    for p in procedimentos_agrupados:
        proc_nome = p['cirurgia__procedimento'] or 'Não informado'
        total = p['total_cirurgias']
        duration = p['tempo_medio_duration'] or timedelta(0)
        media_minutos = duration.total_seconds() / 60

        soma_total_minutos += (media_minutos * total)
        total_geral_cirurgias += total

        dados_tabela.append([
            Paragraph(proc_nome, texto_celula_bold),
            Paragraph(str(total), texto_celula),
            Paragraph(f"{round(media_minutos, 1)} min ({round(media_minutos / 60, 1)}h)", texto_celula)
        ])

    media_geral = round(soma_total_minutos / total_geral_cirurgias, 1) if total_geral_cirurgias > 0 else 0

    tabela = Table(dados_tabela, colWidths=[340, 100, 100])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 15))

    # Bloco de Resumo Geral ao final
    resumo_texto = f"<b>Total Geral de Cirurgias:</b> {total_geral_cirurgias} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tempo Médio Geral:</b> {media_geral} min ({round(media_geral/60, 1)}h)"
    elementos.append(Paragraph(resumo_texto, styles['Normal']))

    # Construção do PDF
    doc.build(elementos)
    return response


def exportar_relatorio_giro_sala_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_giro_sala.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elementos = []

    styles = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1f2937'), alignment=1)
    subtitulo_estilo = ParagraphStyle('SubTitulo', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#6b7280'), alignment=1)
    cabecalho_tabela = ParagraphStyle('CabTabela', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')
    texto_celula = ParagraphStyle('TxtCel', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#374151'))
    texto_celula_bold = ParagraphStyle('TxtCelBold', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#111827'), fontName='Helvetica-Bold')

    trinta_dias_atras = timezone.now() - timedelta(days=30)
    
    # Query base dos últimos 30 dias para Giro de Sala (dataSaidaSala e dataInicioDesmontagemSala ou dados equivalentes do seu fluxo)
    # Ajuste os campos conforme a regra do seu indicador de giro de sala principal
    queryset = GiroSala.objects.filter(
        dataInicioCirurgia__gte=trinta_dias_atras,
        dataSaidaSala__isnull=False,
        dataSalaLiberada__isnull=False
    ).select_related('cirurgia')

    salas_agrupadas = (
        queryset.values('cirurgia__sala')
        .annotate(
            quantidade=Count('id'),
            media_duration=Avg(
                ExpressionWrapper(
                    F('dataSalaLiberada') - F('dataSaidaSala'),
                    output_field=DurationField()
                )
            )
        )
        .order_by('cirurgia__sala')
    )

    elementos.append(Paragraph("Relatório do Indicador de Giro de Sala", titulo_estilo))
    elementos.append(Paragraph("Período de referência: Últimos 30 dias | Tempo médio entre saída do paciente e liberação da sala", subtitulo_estilo))
    elementos.append(Spacer(1, 15))

    dados_tabela = [[
        Paragraph("Sala", cabecalho_tabela),
        Paragraph("Qtd. Cirurgias", cabecalho_tabela),
        Paragraph("Giro Médio", cabecalho_tabela)
    ]]

    total_geral_cirurgias = 0
    soma_medias = 0
    total_salas = 0

    for s in salas_agrupadas:
        sala_nome = s['cirurgia__sala'] or 'Não informada'
        qtd = s['quantidade']
        duration = s['media_duration'] or timedelta(0)
        media_minutos = duration.total_seconds() / 60

        total_geral_cirurgias += qtd
        soma_medias += media_minutos
        total_salas += 1

        dados_tabela.append([
            Paragraph(sala_nome, texto_celula_bold),
            Paragraph(str(qtd), texto_celula),
            Paragraph(f"{round(media_minutos, 1)} min", texto_celula)
        ])

    media_geral = round(soma_medias / total_salas, 1) if total_salas > 0 else 0

    tabela = Table(dados_tabela, colWidths=[240, 130, 130])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 15))

    resumo_texto = f"<b>Total Geral de Cirurgias:</b> {total_geral_cirurgias} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Giro Médio Geral:</b> {media_geral} min"
    elementos.append(Paragraph(resumo_texto, styles['Normal']))

    doc.build(elementos)
    return response

def exportar_relatorio_tempo_sala_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_tempo_sala.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elementos = []

    styles = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1f2937'), alignment=1)
    subtitulo_estilo = ParagraphStyle('SubTitulo', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#6b7280'), alignment=1)
    cabecalho_tabela = ParagraphStyle('CabTabela', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')
    texto_celula = ParagraphStyle('TxtCel', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#374151'))
    texto_celula_bold = ParagraphStyle('TxtCelBold', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#111827'), fontName='Helvetica-Bold')

    trinta_dias_atras = timezone.now() - timedelta(days=30)
    MINUTOS_DIA_SALA = 690  # 07:30 às 19:00 = 690 minutos

    salas_qs = (
        GiroSala.objects.filter(
            dataInicioCirurgia__gte=trinta_dias_atras,
            dataInicioCirurgia__isnull=False,
            dataSalaLiberada__isnull=False
        )
        .values('cirurgia__sala')
        .annotate(
            total_cirurgias=Count('id'),
            tempo_total_utilizado=Sum(
                ExpressionWrapper(
                    F('dataSalaLiberada') - F('dataInicioCirurgia'),
                    output_field=DurationField()
                )
            ),
            dias_unicos=Count('cirurgia__data', distinct=True)
        )
    )

    elementos.append(Paragraph("Relatório de Taxa de Ocupação e Tempo de Sala", titulo_estilo))
    elementos.append(Paragraph("Período de referência: Últimos 30 dias | Janela diária: 07:30 às 19:00 (690 min)", subtitulo_estilo))
    elementos.append(Spacer(1, 15))

    dados_tabela = [[
        Paragraph("Sala", cabecalho_tabela),
        Paragraph("Qtd. Cirurgias", cabecalho_tabela),
        Paragraph("Tempo Utilizado", cabecalho_tabela),
        Paragraph("Ocupação", cabecalho_tabela)
    ]]

    soma_percentuais = 0
    total_salas = 0

    for s in salas_qs:
        sala_nome = s['cirurgia__sala'] or 'Não informada'
        total_cirurgias = s['total_cirurgias']
        
        duration = s['tempo_total_utilizado'] or timedelta(0)
        minutos_utilizados = duration.total_seconds() / 60
        horas_utilizadas = round(minutos_utilizados / 60, 1)

        dias = s['dias_unicos'] or 0
        minutos_disponiveis = dias * MINUTOS_DIA_SALA
        percentual = (minutos_utilizados / minutos_disponiveis * 100) if minutos_disponiveis > 0 else 0

        soma_percentuais += percentual
        total_salas += 1

        dados_tabela.append([
            Paragraph(sala_nome, texto_celula_bold),
            Paragraph(str(total_cirurgias), texto_celula),
            Paragraph(f"{horas_utilizadas}h ({round(minutos_utilizados, 1)} min)", texto_celula),
            Paragraph(f"{round(percentual, 1)}%", texto_celula)
        ])

    media_geral = round(soma_percentuais / total_salas, 1) if total_salas > 0 else 0

    tabela = Table(dados_tabela, colWidths=[180, 100, 150, 110])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 15))

    resumo_texto = f"<b>Taxa Média de Ocupação Geral:</b> {media_geral}%"
    elementos.append(Paragraph(resumo_texto, styles['Normal']))

    doc.build(elementos)
    return response

from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render
from .models import GiroSala, Cirurgia

from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render
from .models import GiroSala, Cirurgia

def _calcular_atraso_minutos(data_cirurgia, hora_planejada, data_real_inicio):
    """Função auxiliar blindada que converte para o horário local antes de calcular"""
    if not data_cirurgia or not hora_planejada or not data_real_inicio:
        return 0, "--", "--"
        
    # 1. Converte o DateTime do banco para o fuso horário local configurado no Django (ex: -0300)
    data_real_local = timezone.localtime(data_real_inicio)

    # 2. Combina a data e a hora planejada da cirurgia
    dt_planejado = datetime.combine(data_cirurgia, hora_planejada)
    
    # Se o Django usa timezone ativo, tornamos o planejado consciente no mesmo fuso local
    if timezone.is_aware(data_real_local):
        dt_planejado = timezone.make_aware(dt_planejado, data_real_local.tzinfo)

    # 3. Remove os objetos de fuso apenas para a matemática de subtração de relógio (evita conflitos de tz)
    diferenca = (data_real_local.replace(tzinfo=None) - dt_planejado.replace(tzinfo=None)).total_seconds() / 60
    atraso_minutos = max(0, diferenca)

    # Retorna o atraso e os horários locais formatados perfeitamente (ex: 08:03)
    return atraso_minutos, dt_planejado.strftime('%H:%M'), data_real_local.strftime('%H:%M')


def indicador_atraso_primeira_cirurgia(request):
    trinta_dias_atras = timezone.now() - timedelta(days=30)
    
    cirurgias_periodo = Cirurgia.objects.filter(
        data__gte=trinta_dias_atras.date(),
        hora__isnull=False
    )

    primeiras_cirurgias_ids = []
    datas_salas = cirurgias_periodo.values('sala', 'data').distinct()
    
    for ds in datas_salas:
        primeira = cirurgias_periodo.filter(
            sala=ds['sala'],
            data=ds['data']
        ).order_by('hora').first()
        
        if primeira:
            primeiras_cirurgias_ids.append(primeira.id)

    registros_primeiras = GiroSala.objects.filter(
        cirurgia_id__in=primeiras_cirurgias_ids,
        dataInicioCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente')

    total_primeiras = registros_primeiras.count()
    ate_30 = 0
    ate_60 = 0
    acima_60 = 0
    salas_dict = {}

    # Dicionário para acumular atrasos por dia da semana (0 = Segunda, ..., 4 = Sexta)
    # Vamos armazenar [soma_atrasos, quantidade] para calcular a média

    dias_semana_stats = {
        0: {'nome': 'Segunda-feira', 'ate_30': 0, 'ate_60': 0, 'acima_60': 0, 'total': 0},
        1: {'nome': 'Terça-feira', 'ate_30': 0, 'ate_60': 0, 'acima_60': 0, 'total': 0},
        2: {'nome': 'Quarta-feira', 'ate_30': 0, 'ate_60': 0, 'acima_60': 0, 'total': 0},
        3: {'nome': 'Quinta-feira', 'ate_30': 0, 'ate_60': 0, 'acima_60': 0, 'total': 0},
        4: {'nome': 'Sexta-feira', 'ate_30': 0, 'ate_60': 0, 'acima_60': 0, 'total': 0},
        5: {'nome': 'Sexta-feira', 'ate_30': 0, 'ate_60': 0, 'acima_60': 0, 'total': 0},
    }

    for reg in registros_primeiras:
        sala = reg.cirurgia.sala or 'Não informada'
        if sala not in salas_dict:
            salas_dict[sala] = {'sala': sala, 'total': 0, 'ate_30': 0, 'ate_60': 0, 'acima_60': 0}

        atraso, _, _ = _calcular_atraso_minutos(reg.cirurgia.data, reg.cirurgia.hora, reg.dataInicioCirurgia)

        salas_dict[sala]['total'] += 1

        # Classificação por faixa
        if atraso <= 30:
            ate_30 += 1
            salas_dict[sala]['ate_30'] += 1
            faixa_key = 'ate_30'
        elif atraso <= 60:
            ate_60 += 1
            salas_dict[sala]['ate_60'] += 1
            faixa_key = 'ate_60'
        else:
            acima_60 += 1
            salas_dict[sala]['acima_60'] += 1
            faixa_key = 'acima_60'

        # Identifica o dia da semana (0 a 4, Seg a Sex)
        dia_idx = reg.cirurgia.data.weekday()
        if dia_idx in dias_semana_stats:
            dias_semana_stats[dia_idx][faixa_key] += 1
            dias_semana_stats[dia_idx]['total'] += 1

    # Monta a lista estruturada para o template
    atraso_por_dia = []
    for idx in range(6):
        d = dias_semana_stats[idx]
        atraso_por_dia.append({
            'dia': d['nome'],
            'ate_30': d['ate_30'],
            'ate_60': d['ate_60'],
            'acima_60': d['acima_60'],
            'total': d['total']
        })

    p_ate_30 = round((ate_30 / total_primeiras * 100), 1) if total_primeiras > 0 else 0
    p_ate_60 = round((ate_60 / total_primeiras * 100), 1) if total_primeiras > 0 else 0
    p_acima_60 = round((acima_60 / total_primeiras * 100), 1) if total_primeiras > 0 else 0

    lista_salas = []
    for s_nome, dados in salas_dict.items():
        tot = dados['total']
        p_sala_critico = round((dados['acima_60'] / tot * 100), 1) if tot > 0 else 0
        lista_salas.append({
            'sala': s_nome,
            'total': tot,
            'ate_30': dados['ate_30'],
            'ate_60': dados['ate_60'],
            'acima_60': dados['acima_60'],
            'percentual_critico': p_sala_critico,
            'badge': 'success' if p_sala_critico <= 10 else ('warning' if p_sala_critico <= 30 else 'danger')
        })

    context = {
        'total_primeiras': total_primeiras,
        'ate_30': ate_30,
        'p_ate_30': p_ate_30,
        'ate_60': ate_60,
        'p_ate_60': p_ate_60,
        'acima_60': acima_60,
        'p_acima_60': p_acima_60,
        'salas': lista_salas,
        'atraso_por_dia': atraso_por_dia,  # <--- Dados para o gráfico
    }
    return render(request, 'centrocirurgico/indicadores/atraso_primeira_cirurgia.html', context)


def api_detalhe_atraso_faixa(request, faixa):
    trinta_dias_atras = timezone.now() - timedelta(days=30)
    
    cirurgias_periodo = Cirurgia.objects.filter(data__gte=trinta_dias_atras.date(), hora__isnull=False)
    primeiras_cirurgias_ids = []
    for ds in cirurgias_periodo.values('sala', 'data').distinct():
        primeira = cirurgias_periodo.filter(sala=ds['sala'], data=ds['data']).order_by('hora').first()
        if primeira: primeiras_cirurgias_ids.append(primeira.id)

    registros = GiroSala.objects.filter(
        cirurgia_id__in=primeiras_cirurgias_ids,
        dataInicioCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente')

    cirurgias_filtradas = []

    for reg in registros:
        atraso, planejado_str, real_str = _calcular_atraso_minutos(reg.cirurgia.data, reg.cirurgia.hora, reg.dataInicioCirurgia)

        incluir = False
        if faixa == 'ate-30' and atraso <= 30:
            incluir = True
        elif faixa == 'ate-60' and 30 < atraso <= 60:
            incluir = True
        elif faixa == 'acima-60' and atraso > 60:
            incluir = True

        if incluir:
            cirurgias_filtradas.append({
                'data': reg.cirurgia.data.strftime('%d/%m/%Y'),
                'sala': reg.cirurgia.sala or '-',
                'paciente': reg.paciente.nome if reg.paciente else '-',
                'procedimento': reg.cirurgia.procedimento or '-',
                'medico': reg.cirurgia.medico or '-',
                'planejado': reg.cirurgia.hora.strftime('%H:%M'),
                'real': reg.dataInicioCirurgia.strftime('%H:%M'),
                'atraso_minutos': round(atraso, 1)
            })
            

    return JsonResponse({'cirurgias': cirurgias_filtradas})


def api_detalhe_atraso_sala(request, sala_nome):
    trinta_dias_atras = timezone.now() - timedelta(days=30)
    
    cirurgias_periodo = Cirurgia.objects.filter(data__gte=trinta_dias_atras.date(), hora__isnull=False, sala=sala_nome)
    primeiras_cirurgias_ids = []
    for data_unica in cirurgias_periodo.values_list('data', flat=True).distinct():
        primeira = cirurgias_periodo.filter(data=data_unica).order_by('hora').first()
        if primeira: primeiras_cirurgias_ids.append(primeira.id)

    registros = GiroSala.objects.filter(
        cirurgia_id__in=primeiras_cirurgias_ids,
        dataInicioCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente').order_by('-cirurgia__data')

    cirurgias_data = []
    for reg in registros:
        #atraso = _calcular_atraso_minutos(reg.cirurgia.data, reg.cirurgia.hora, reg.dataInicioCirurgia)
        atraso, planejado_str, real_str = _calcular_atraso_minutos(reg.cirurgia.data, reg.cirurgia.hora, reg.dataInicioCirurgia)

        if atraso <= 30: 
            faixa_badge, faixa_txt = 'success', 'Até 30 min'
        elif atraso <= 60: 
            faixa_badge, faixa_txt = 'warning text-dark', 'Até 60 min'
        else: 
            faixa_badge, faixa_txt = 'danger', 'Acima de 60 min'

        cirurgias_data.append({
            'data': reg.cirurgia.data.strftime('%d/%m/%Y'),
            'paciente': reg.paciente.nome if reg.paciente else '-',
            'procedimento': reg.cirurgia.procedimento or '-',
            'medico': reg.cirurgia.medico or '-',
            'planejado': planejado_str,  # <-- Agora exibe o horário correto ajustado
            'real': real_str,            # <-- Agora exibe o horário real correto
            'atraso_minutos': round(atraso, 1),
            'faixa_txt': faixa_txt,
            'faixa_badge': faixa_badge
        })

    return JsonResponse({'cirurgias': cirurgias_data})

def exportar_relatorio_atraso_primeira_cirurgia_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_atraso_primeira_cirurgia.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elementos = []

    styles = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1f2937'), alignment=1)
    subtitulo_estilo = ParagraphStyle('SubTitulo', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#6b7280'), alignment=1)
    cabecalho_tabela = ParagraphStyle('CabTabela', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')
    texto_celula = ParagraphStyle('TxtCel', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#374151'))
    texto_celula_bold = ParagraphStyle('TxtCelBold', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#111827'), fontName='Helvetica-Bold')

    trinta_dias_atras = timezone.now() - timedelta(days=30)
    
    cirurgias_periodo = Cirurgia.objects.filter(
        data__gte=trinta_dias_atras.date(),
        hora__isnull=False
    )

    primeiras_cirurgias_ids = []
    datas_salas = cirurgias_periodo.values('sala', 'data').distinct()
    
    for ds in datas_salas:
        primeira = cirurgias_periodo.filter(
            sala=ds['sala'],
            data=ds['data']
        ).order_by('hora').first()
        
        if primeira:
            primeiras_cirurgias_ids.append(primeira.id)

    registros_primeiras = GiroSala.objects.filter(
        cirurgia_id__in=primeiras_cirurgias_ids,
        dataInicioCirurgia__isnull=False
    ).select_related('cirurgia', 'cirurgia__paciente')

    total_primeiras = 0
    ate_30 = 0
    ate_60 = 0
    acima_60 = 0
    salas_dict = {}

    for reg in registros_primeiras:
        sala = reg.cirurgia.sala or 'Não informada'
        if sala not in salas_dict:
            salas_dict[sala] = {'sala': sala, 'total': 0, 'ate_30': 0, 'ate_60': 0, 'acima_60': 0}

        atraso, _, _ = _calcular_atraso_minutos(reg.cirurgia.data, reg.cirurgia.hora, reg.dataInicioCirurgia)

        total_primeiras += 1
        salas_dict[sala]['total'] += 1

        if atraso <= 30:
            ate_30 += 1
            salas_dict[sala]['ate_30'] += 1
        elif atraso <= 60:
            ate_60 += 1
            salas_dict[sala]['ate_60'] += 1
        else:
            acima_60 += 1
            salas_dict[sala]['acima_60'] += 1

    elementos.append(Paragraph("Relatório de Atraso da Primeira Cirurgia do Dia", titulo_estilo))
    elementos.append(Paragraph("Período de referência: Últimos 30 dias | Controle de prevenção ao efeito cascata", subtitulo_estilo))
    elementos.append(Spacer(1, 15))

    # Tabela de Resumo Global por Faixas
    dados_resumo = [
        [Paragraph("Faixa de Atraso", cabecalho_tabela), Paragraph("Quantidade", cabecalho_tabela), Paragraph("Percentual", cabecalho_tabela)],
        [Paragraph("Até 30 min (Pontual / Tolerável)", texto_celula_bold), Paragraph(str(ate_30), texto_celula), Paragraph(f"{round((ate_30/total_primeiras*100) if total_primeiras > 0 else 0, 1)}%", texto_celula)],
        [Paragraph("Até 60 min (Atenção)", texto_celula_bold), Paragraph(str(ate_60), texto_celula), Paragraph(f"{round((ate_60/total_primeiras*100) if total_primeiras > 0 else 0, 1)}%", texto_celula)],
        [Paragraph("Acima de 60 min (Crítico)", texto_celula_bold), Paragraph(str(acima_60), texto_celula), Paragraph(f"{round((acima_60/total_primeiras*100) if total_primeiras > 0 else 0, 1)}%", texto_celula)],
    ]
    tabela_resumo = Table(dados_resumo, colWidths=[260, 120, 160])
    tabela_resumo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elementos.append(tabela_resumo)
    elementos.append(Spacer(1, 15))

    # Tabela detalhada por Sala (Ordenada alfabeticamente)
    elementos.append(Paragraph("<b>Detalhamento por Sala</b>", styles['Normal']))
    elementos.append(Spacer(1, 5))

    dados_salas = [[
        Paragraph("Sala", cabecalho_tabela),
        Paragraph("Qtd. Dias", cabecalho_tabela),
        Paragraph("Até 30m", cabecalho_tabela),
        Paragraph("Até 60m", cabecalho_tabela),
        Paragraph("> 60m", cabecalho_tabela)
    ]]

    for s_nome in sorted(salas_dict.keys()):
        d = salas_dict[s_nome]
        dados_salas.append([
            Paragraph(d['sala'], texto_celula_bold),
            Paragraph(str(d['total']), texto_celula),
            Paragraph(str(d['ate_30']), texto_celula),
            Paragraph(str(d['ate_60']), texto_celula),
            Paragraph(str(d['acima_60']), texto_celula)
        ])

    tabela_salas = Table(dados_salas, colWidths=[180, 100, 100, 100, 60])
    tabela_salas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4b5563')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))

    elementos.append(tabela_salas)

    doc.build(elementos)
    return response
