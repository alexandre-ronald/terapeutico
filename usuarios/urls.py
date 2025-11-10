from django.urls import path
from . import views


app_name = 'usuarios'

urlpatterns = [
    path('perfil/', views.perfil, name='perfil'),  # Visualizar perfil do usuário
    path('lockscreen/', views.lockscreen, name='lockscreen'),  # Visualizar perfil do usuário
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),  # Editar perfil do usuário
    path('login/', views.user_login, name='login'),  # Login
    path('logout/', views.sair, name='sair'),  # Logout
    path('desbloquear_tela/',views.desbloquear_tela,name='desbloquear_tela'),
    # exemplo de url em usuarios/urls.py
    path('boas-vindas/', views.boas_vindas, name='boas_vindas'),
    path('cadastrar-usuario/', views.cadastrar_usuario, name='cadastrar_usuario'),
    path('editar-usuario/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),


]
