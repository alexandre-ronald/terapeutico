from django.contrib import admin
from .models import Material, Especialidade, Procedimento, Kit, Kit_Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Procedimento)
class ProcedimentoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "especialidade")
    list_filter = ("especialidade",)
    search_fields = ("nome", "especialidade__nome")
    ordering = ("nome",)


class KitMaterialInline(admin.TabularInline):
    model = Kit_Material
    extra = 1  # mostra 1 linha extra para adicionar material
    autocomplete_fields = ("material",)
    fields = ("material", "quantidade")


@admin.register(Kit)
class KitAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "especialidade")
    list_filter = ("especialidade",)
    search_fields = ("nome", "especialidade__nome")
    ordering = ("nome",)
    inlines = [KitMaterialInline]  # permite adicionar materiais direto no Kit


@admin.register(Kit_Material)
class KitMaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "kit", "material", "quantidade")
    list_filter = ("kit", "material")
    search_fields = ("kit__nome", "material__nome")
    ordering = ("kit__nome", "material__nome")
