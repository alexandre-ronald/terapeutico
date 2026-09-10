from django.contrib import admin
from .models import Empresa
# Register your models here.
# opme/admin.py
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome',)  # só nome
    search_fields = ('nome',)