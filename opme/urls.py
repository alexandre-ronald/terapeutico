# opme/urls.py
from django.urls import path
from . import views

app_name = 'opme'

urlpatterns = [


    path("produtos/buscar/", views.buscar_produtos, name="buscar_produtos"),

    # Empréstimos
    
    path('novo/', views.consignacao_create, name='consignacao_create'),
    path('<int:pk>/conferencia/', views.consignacao_conferencia, name='consignacao_conferencia'),
    path('<int:pk>/devolucao/', views.consignacao_devolucao, name='consignacao_devolucao'),

    # Empresas
    path('empresas/', views.empresa_list, name='empresa_list'),
    path('empresas/nova/', views.empresa_create, name='empresa_create'),
    path('empresas/<int:pk>/editar/', views.empresa_update, name='empresa_update'),
    path('empresas/<int:pk>/excluir/', views.empresa_delete, name='empresa_delete'),

    # Produtos 
    path('produtos/', views.produto_list, name='produto_list'),
    path('produtos/novo/', views.produto_create, name='produto_create'),
    path('produtos/<int:pk>/editar/', views.produto_update, name='produto_update'),
    path('produtos/<int:pk>/excluir/', views.produto_delete, name='produto_delete'),

    # Caixas 
    path('caixas/', views.caixa_list, name='caixa_list'),
    path('caixas/nova/', views.caixa_create, name='caixa_create'),
    path('caixas/<int:pk>/editar/', views.caixa_update, name='caixa_update'),
    path('caixas/<int:pk>/excluir/', views.caixa_delete, name='caixa_delete'),

    # Emprestimo
    path('consignacoes/', views.consignacao_list, name='consignacao_list'),
    path('consignacoes/novo/', views.consignacao_create, name='consignacao_create'),
    path('consignacoes/<int:pk>/', views.consignacao_detail, name='consignacao_detail'),
    path('consignacoes/<int:pk>/reposicao/', views.consignacao_reposicao, name='consignacao_reposicao'),
    path('consignacoes/<int:pk>/conferencia/', views.consignacao_conferencia, name='consignacao_conferencia'),
    path('consignacoes/<int:pk>/devolucao/', views.consignacao_devolucao, name='consignacao_devolucao'),

    path('consignacoes/<int:pk>/relatorio/', views.consignacao_relatorio, name='consignacao_relatorio'),
    path('get-itens-caixa/', views.get_itens_caixa, name='get_itens_caixa'),
    path('consignacoes/editar/<int:pk>/', views.consignacao_edit, name='consignacao_edit'),
]

