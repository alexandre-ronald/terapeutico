from django.contrib import admin

from .models import MotivoSuspensao, TipoSuspensao


@admin.register(TipoSuspensao)
class TipoSuspensaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ordem", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    ordering = ("ordem", "nome")


@admin.register(MotivoSuspensao)
class MotivoSuspensaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "ordem", "ativo", "atualizado_em")
    list_filter = ("ativo", "tipo")
    search_fields = ("nome", "descricao", "tipo__nome")
    autocomplete_fields = ("tipo",)
    ordering = ("tipo__ordem", "tipo__nome", "ordem", "nome")
