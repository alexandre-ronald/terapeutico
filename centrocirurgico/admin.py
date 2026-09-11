from django.contrib import admin

from .models import NecessidadeCirurgica, MotivoSuspensao, ProgramacaoCirurgia, ProgramacaoNecessidade, SuspensaoCirurgia, TipoSuspensao


@admin.register(NecessidadeCirurgica)
class NecessidadeCirurgicaAdmin(admin.ModelAdmin):
    list_display = ("nome", "dica_complemento", "complemento_obrigatorio", "ordem", "ativo")
    list_filter = ("ativo", "complemento_obrigatorio")
    search_fields = ("nome", "descricao", "dica_complemento")
    ordering = ("ordem", "nome")


class ProgramacaoNecessidadeInline(admin.TabularInline):
    model = ProgramacaoNecessidade
    extra = 0


@admin.register(ProgramacaoCirurgia)
class ProgramacaoCirurgiaAdmin(admin.ModelAdmin):
    list_display = ("cirurgia", "status", "enviado_em", "atualizado_por")
    list_filter = ("status", "cirurgia__sala")
    search_fields = ("cirurgia__paciente__nome", "cirurgia__paciente__prontuario", "cirurgia__procedimento")
    raw_id_fields = ("cirurgia",)
    inlines = (ProgramacaoNecessidadeInline,)


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
    raw_id_fields = ("cirurgia",)
    autocomplete_fields = ("tipo", "motivo", "registrado_por")
    readonly_fields = ("registrado_em",)
