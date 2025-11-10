from django.urls import path
from . import views

app_name = 'upme'


urlpatterns = [
    path('material/', views.manutencao_generica, {'model_name': 'Material'}, name='material'),
    path('kit/', views.manutencao_generica, {'model_name': 'Especialidade'}, name='especialidade'),
    path('procedimento/', views.manutencao_generica, {'model_name': 'Procedimento'}, name='procedimento'),
    path('kits/', views.cadastrar_kits, name='cadastrar_kits'),
    path("get_kits_por_especialidade/", views.get_kits_por_especialidade, name="get_kits_por_especialidade"),
    path("get_materiais_por_kit/", views.get_materiais_por_kit, name="get_materiais_por_kit"),
    path('procedimentos/', views.cadastrar_procedimentos, name='cadastrar_procedimentos'),
    path('procedimentos/<int:id_procedimento>', views.cadastrar_procedimentos, name='cadastrar_procedimentos'),

    path('cirurgia/<int:pk>/relatorio/', views.relatorio_cirurgia, name='relatorio_cirurgia'),

    path('cirurgia/submit/', views.cirurgia_submit, name='cirurgia_submit'),

    path('paciente/', views.paciente_list, name='paciente_list'),
   
    path('get_procedimentos/', views.get_procedimentos, name='get_procedimentos'),
    path('get_kit_materials/', views.get_kit_materials, name='get_kit_materials'),

    path('mapa_cirurgico/', views.mapa_cirurgico_list, name='mapa_cirurgico_list'),

    path('fornecimento_material/', views.fornecimento_material, name='fornecimento_material'),
    path('fornecimento_material_extra/', views.fornecimento_material_extra, name='fornecimento_material_extra'),
    path('fornecimento_material/save/', views.fornecimento_material_save, name='fornecimento_material_save'),

    path('imprimir_formecimento', views.relatorio_formulario_pdf, name='relatorio_formulario'),

]
