from django.contrib.auth import get_user_model
from django.contrib import auth, messages
from django.contrib.auth import  login, logout, authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator



from django.core.exceptions import ValidationError
import re

User = get_user_model()


@login_required
def perfil(request):
    return render(request, 'usuarios/perfil.html', {'user': request.user})

@login_required
def editar_perfil(request):
    """Edita o perfil do usuário atualmente autenticado."""
    Usuario = get_user_model()
    if request.method == "POST":
        # Usando o modelo correto
        user = request.user  # Deve ser uma instância de Usuario

        # Atualize os campos, incluindo matricula
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.matricula = request.POST.get('matricula', user.matricula)

        # Outros campos, como foto de perfil
        if 'foto_perfil' in request.FILES:
            user.foto_perfil = request.FILES['foto_perfil']

        user.save()

        messages.success(request, "Perfil atualizado com sucesso.")
        return redirect(reverse('usuarios:perfil'))
    
    return render(request, 'usuarios/editar_perfil.html', {'user': request.user})

def lockscreen(request):
    perfil = '' #PerfilUsuario.objects.get(usuario=request.user)  # Busca o perfil do usuário logado
    return render(request, 'usuarios/lockscreen.html', {
        'perfil': perfil,
        'user': request.user,
    })
def desbloquear_tela(request):
    if request.method == "POST":
        login = request.POST.get('usuario')
        senha = request.POST.get('senha')
        user = auth.authenticate(username=login, password=senha)
        if not user:
            messages.error(request, 'Senha inválida')
            return render(request, 'usuarios/lockscreen.html')
        
        return redirect(reverse('usuarios:boas_vindas'))
    return render(request, 'usuarios/lockscreen.html')

def sair(request):
    logout(request)
    return redirect(reverse('usuarios:login'))
    
@login_required
def boas_vindas(request):
    """View de boas-vindas, exibida ao usuário após o login."""
    context = {
        'user': request.user
    }
    return render(request, 'usuarios/boas_vindas.html', context)

def login_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None: 
            login(request, user)
            return redirect('usuarios:boas_vindas')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'usuarios/login.html')

from .ldap_utils import autenticar_usuario_ldap

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if autenticar_usuario_ldap(username, password):
            try:
                user = User.objects.get(username=username)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)  # Faz login sem checar senha local
                return redirect('usuarios:boas_vindas')  # ou outra URL
            except User.DoesNotExist:
                messages.error(request, 'Usuário não encontrado no sistema.')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')

    return render(request, 'usuarios/login.html')

def user_login2(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        print (username,password)
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print('entrou')
            if user.is_active:
                print('passou')
                login(request, user)
                return redirect('legado:dashboard')
            else:
                messages.error(request, "Conta desativada.")
        else:
            # Exibir a mensagem de erro definida pelo backend
            error_message = getattr(request, 'ldap_auth_error', "Usuário ou senha inválidos.")
            messages.error(request, error_message)
    return render(request, 'usuarios/login.html')



@csrf_exempt
def editar_usuario(request,usuario_id):

    if request.method == 'POST':
        # Obter dados do formulário
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        perfil_acesso = request.POST.get('perfil_acesso')
        matricula = request.POST.get('matricula')
        ativo = request.POST.get('ativo') == 'on'
        foto_perfil = request.FILES.get('foto_perfil')
        id = request.POST.get('id')

        if id:
            
            usuario = get_object_or_404(User,id=id)
            
            usuario.username 
            usuario.email=email
            usuario.first_name=first_name
            usuario.last_name=last_name
            usuario.perfil_acesso=perfil_acesso
            usuario.matricula=matricula
            usuario.ativo=ativo
            usuario.foto_perfil=foto_perfil
            usuario.save()


    usuarios_selecionado = User.objects.filter(id=usuario_id).first()
    usuarios = User.objects.all().order_by('id')

    paginator = Paginator(usuarios, 5)  # 10 pacientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'usuarios': page_obj,
        'usuarios_selecionado': usuarios_selecionado
        }
    return render(request, 'usuarios/cadastrar_usuario.html', context)

@csrf_exempt
def cadastrar_usuario(request):
    if request.method == 'POST':
        # Obter dados do formulário
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        perfil_acesso = request.POST.get('perfil_acesso')
        matricula = request.POST.get('matricula')
        ativo = request.POST.get('ativo') == 'on'
        foto_perfil = request.FILES.get('foto_perfil')
        id = request.POST.get('id')

       
        # Criar usuário
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            perfil_acesso=perfil_acesso,
            matricula=matricula,
            ativo=ativo,
            foto_perfil=foto_perfil
        )
        user.set_password(password)  # Criptografar senha
        user.save()


    usuarios = User.objects.all().order_by('id')

    paginator = Paginator(usuarios, 5)  # 10 pacientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'usuarios': page_obj
        }
    
    return render(request, 'usuarios/cadastrar_usuario.html', context)

@csrf_exempt
def editar_usuario(request,usuario_id):

    if request.method == 'POST':
        # Obter dados do formulário
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        perfil_acesso = request.POST.get('perfil_acesso')
        matricula = request.POST.get('matricula')
        ativo = request.POST.get('ativo') == 'on'
        foto_perfil = request.FILES.get('foto_perfil')
        id = request.POST.get('id')

        if id:
            
            usuario = get_object_or_404(User,id=id)
            
            usuario.username 
            usuario.email=email
            usuario.first_name=first_name
            usuario.last_name=last_name
            usuario.perfil_acesso=perfil_acesso
            usuario.matricula=matricula
            usuario.ativo=ativo
            usuario.foto_perfil=foto_perfil
            usuario.save()


    usuarios_selecionado = User.objects.filter(id=usuario_id).first()
    usuarios = User.objects.all().order_by('id')

    paginator = Paginator(usuarios, 5)  # 10 pacientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'usuarios': page_obj,
        'usuarios_selecionado': usuarios_selecionado
        }
    return render(request, 'usuarios/cadastrar_usuario.html', context)


