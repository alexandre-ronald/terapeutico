from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin

@admin.register(User)
class CustomUsuarioAdmin(UserAdmin):  # Herde de UserAdmin, não de ModelAdmin
    list_display = ('username', 'first_name', 'last_name', 'matricula', 'perfil_acesso', 'ativo')
    list_filter = ('perfil_acesso', 'ativo', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'matricula')
    ordering = ('username',)
    
    # Adicione campos personalizados aos fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Campos Personalizados', {'fields': ('matricula', 'perfil_acesso', 'ativo', 'foto_perfil')}),
    )