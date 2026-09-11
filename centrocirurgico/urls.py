from django.urls import path
from . import views
from . import views_suspensao
from . import views_necessidade
from . import views_programador
from . import views_painel_programador

app_name = 'centrocirurgico'

urlpatterns = [
    path("painel-programador/", views_painel_programador.painel_programador, name="painel_programador"),
    path("painel-programador/necessidades/<int:pk>/alternar/", views_painel_programador.necessidade_alternar_atendimento, name="necessidade_alternar_atendimento"),
    path("programador/", views_programador.programador_mapa, name="programador_mapa"),
    path("programador/abrir/", views_programador.programacao_abrir, name="programacao_abrir"),
    path("programador/<int:pk>/", views_programador.programacao_editar, name="programacao_editar"),
    path("programador/<int:pk>/enviar/", views_programador.programacao_enviar, name="programacao_enviar"),
    path("necessidades/", views_necessidade.necessidade_lista, name="necessidade_lista"),
    path("necessidades/salvar/", views_necessidade.necessidade_salvar, name="necessidade_salvar"),
    path("necessidades/<int:pk>/alternar/", views_necessidade.necessidade_alternar, name="necessidade_alternar"),
    path("necessidades/<int:pk>/excluir/", views_necessidade.necessidade_excluir, name="necessidade_excluir"),
    path("suspensoes/", views_suspensao.suspensoes_lista, name="suspensoes_lista"),
    path(
        "suspensoes/<int:pk>/",
        views_suspensao.suspensao_detalhe,
        name="suspensao_detalhe",
    ),
    path(
        "suspensoes/<int:pk>/editar/",
        views_suspensao.suspensao_editar,
        name="suspensao_editar",
    ),
    path(
        "suspensoes/nova/",
        views_suspensao.suspensao_nova,
        name="suspensao_nova",
    ),
    path(
        "suspensoes/motivos-ativos/<int:tipo_id>/",
        views_suspensao.motivos_ativos_por_tipo,
        name="motivos_ativos_por_tipo",
    ),
    path(
        'suspensoes/configuracoes/',
        views_suspensao.configuracoes_suspensao,
        name='configuracoes_suspensao',
    ),
    path('suspensoes/tipos/salvar/', views_suspensao.tipo_salvar, name='tipo_suspensao_salvar'),
    path('suspensoes/tipos/<int:pk>/alternar/', views_suspensao.tipo_alternar, name='tipo_suspensao_alternar'),
    path('suspensoes/tipos/<int:pk>/excluir/', views_suspensao.tipo_excluir, name='tipo_suspensao_excluir'),
    path('suspensoes/motivos/salvar/', views_suspensao.motivo_salvar, name='motivo_suspensao_salvar'),
    path('suspensoes/motivos/<int:pk>/alternar/', views_suspensao.motivo_alternar, name='motivo_suspensao_alternar'),
    path('suspensoes/motivos/<int:pk>/excluir/', views_suspensao.motivo_excluir, name='motivo_suspensao_excluir'),

    ## novo de teste
    path('mapa_cirurgico/novo/', views.mapa_cirurgico_list_novo, name='mapa_cirurgico_list_novo'),
    path('giro/novo/', views.registrar_giro_novo, name='registrar_giro_novo'),
    path('girosala/novo/', views.giro_sala_novo, name='giro_sala_novo'),
    path("giro-sala/<int:pk>/registrar-etapa-manual/", views.registrar_etapa_manual, name="registrar_etapa_manual"),

    path('mapa_cirurgico/', views.mapa_cirurgico_list, name='mapa_cirurgico_list'),
    path('giro/', views.registrar_giro, name='registrar_giro'),
    path('giro/<int:pk>/<str:etapa>/', views.registrar_etapa, name='registrar_etapa'),

    path('<int:pk>/inicio-cirurgia/', views.registrar_inicio_cirurgia, name="inicio_cirurgia"),
    path('<int:pk>/fim-cirurgia/', views.registrar_final_cirurgia, name="fim_cirurgia"),
    path('<int:pk>/saida-sala/', views.registrar_saida_sala, name="saida_sala"),
    path('<int:pk>/inicio-desmontagem/', views.registrar_inicio_desmontagem, name="inicio_desmontagem"),
    path('<int:pk>/final-desmontagem/', views.registrar_final_desmontagem, name="final_desmontagem"),

    path('<int:pk>/inicio-limpeza/', views.registrar_inicio_limpeza, name="inicio_limpeza"),
    path('<str:tipo>/<int:pk>/inicio-limpeza-tipo/', views.registrar_inicio_limpeza_tipo, name="inicio_limpeza_tipo"),
    path("relatorio-lavagens/", views.relatorio_lavagens, name="relatorio_lavagens"),
    path('<int:pk>/final-limpeza/', views.registrar_final_limpeza, name="final_limpeza"),
    path('<int:pk>/sala-liberada/', views.registrar_sala_liberada, name="sala_liberada"),

    path('girosala/', views.giro_sala, name='giro_sala'),
    path('girodesala/', views.giro, name='giro'),

    path('limpeza-terminal/', views.limpeza_list, name='limpeza-list'),
    path('limpeza-terminal/nova/', views.limpeza_create, name='limpeza-create'),
    path('limpeza-terminal/<int:pk>/', views.limpeza_detail, name='limpeza-detail'),
    path('limpeza-terminal/<int:pk>/editar/', views.limpeza_update, name='limpeza-update'),
    path('limpeza-terminal/dashboard/', views.limpeza_dashboard, name='limpeza-dashboard'),
    path('limpeza-terminal/<int:pk>/deletar/', views.limpeza_delete, name='limpeza-delete'),

    path("pedido-cirurgia/", views.lista_pedidos_cirurgia, name="lista_pedidos_cirurgia"),
    path("pedido-cirurgia/novo/", views.novo_pedido_cirurgia, name="novo_pedido_cirurgia"),
    path("giro-observacao/<int:pk>/", views.salvar_observacao_giro, name="salvar_observacao_giro"),

    path("indicadores/giro-sala/", views.indicador_giro_sala, name="indicador_giro_sala"),
    path("api/giro-sala/<str:sala>/", views.detalhe_giro_sala, name="detalhe_giro_sala"),
    path("indicadores/tempo-sala/", views.indicador_tempo_sala, name="indicador_tempo_sala"),
    path('api/tempo-sala/<str:sala_nome>/', views.api_tempo_sala, name='api_tempo_sala'),
    path('tempo-cirurgia/', views.indicador_tempo_cirurgia, name='indicador_tempo_cirurgia'),
    path('api/tempo-cirurgia/<str:procedimento_nome>/', views.api_tempo_cirurgia_por_procedimento, name='api_tempo_cirurgia_por_procedimento'),

    path('tempo-cirurgia/pdf/', views.exportar_relatorio_tempo_cirurgia_pdf, name='exportar_relatorio_tempo_cirurgia_pdf'),
    path('tempo-sala/pdf/', views.exportar_relatorio_tempo_sala_pdf, name='exportar_relatorio_tempo_sala_pdf'),
    path('giro-sala/pdf/', views.exportar_relatorio_giro_sala_pdf, name='exportar_relatorio_giro_sala_pdf'),

    path('atraso-primeira-cirurgia/', views.indicador_atraso_primeira_cirurgia, name='indicador_atraso_primeira_cirurgia'),
    path('api/atraso-faixa/<str:faixa>/', views.api_detalhe_atraso_faixa, name='api_detalhe_atraso_faixa'),
    path('api/atraso-sala/<str:sala_nome>/', views.api_detalhe_atraso_sala, name='api_detalhe_atraso_sala'),
    path('atraso-primeira-cirurgia/pdf/', views.exportar_relatorio_atraso_primeira_cirurgia_pdf, name='exportar_relatorio_atraso_primeira_cirurgia_pdf'),
]
