from django.contrib import admin

from .models import MotivoSuspensao, SuspensaoCirurgia, TipoSuspensao


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



@admin.register(SuspensaoCirurgia)
class SuspensaoCirurgiaAdmin(admin.ModelAdmin):
    list_display = (
        "cirurgia",
        "tipo",
        "motivo",
        "registrado_por",
        "registrado_em",
    )
    list_filter = ("tipo", "motivo", "registrado_em")
    search_fields = (
        "cirurgia__paciente__nome",
        "cirurgia__paciente__prontuario",
        "cirurgia__procedimento",
        "observacao",
    )
    autocomplete_fields = ("cirurgia", "tipo", "motivo", "registrado_por")
    readonly_fields = ("registrado_em",)
