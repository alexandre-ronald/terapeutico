# opme/urls.py
from django.urls import path
from . import views

app_name = 'uhh'

urlpatterns = [
        
    path("relatorio/<int:solicitacao_id>/hemomar/", views.relatorio_solicitacao, name="relatorio_hemomar"),

    # Prova Cruzada
    path('provas/', views.lista_provas, name='lista_provas'),
    path('provas/nova/', views.nova_prova, name='nova_prova'),

    # Liberação
    path('liberacoes/', views.lista_liberacoes, name='lista_liberacoes'),
    path('liberacoes/nova/', views.nova_liberacao, name='nova_liberacao'),

    path("devolucoes/nova/", views.nova_devolucao, name="nova_devolucao"),
    path("devolucoes/", views.lista_devolucoes, name="lista_devolucoes"),

    # =============================
    # SOLICITAÇÕES
    # =============================

    path("solicitacoes/", views.lista_solicitacoes, name="lista_solicitacoes" ),
    path("solicitacoes/nova/", views.nova_solicitacao, name="nova_solicitacao" ),
    path("solicitacoes/<int:solicitacao_id>/itens/", views.itens_solicitacao, name="itens_solicitacao"),
    path('solicitacoes/<int:solicitacao_id>/editar/', views.editar_solicitacao, name='editar_solicitacao'),

    # =============================
    # RETORNOS
    # =============================

    path("retornos/", views.lista_retornos, name="lista_retornos" ),
    path("retornos/<int:solicitacao_id>/registrar/", views.registrar_retorno, name="registrar_retorno"),

    # Bolsas
    path('bolsas/', views.lista_bolsas, name='lista_bolsas'),
    path('bolsas/nova/', views.nova_bolsa, name='nova_bolsa'),
    path('bolsas/<int:bolsa_id>/editar/', views.editar_bolsa, name='editar_bolsa'),

]

