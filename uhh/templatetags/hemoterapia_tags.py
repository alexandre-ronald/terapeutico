from django import template

register = template.Library()

@register.filter
def get_item(mapa, chave):
    return mapa.get(chave)

@register.simple_tag
def get_mapa(mapa, tipo, grupo, rh):
    return mapa.get((tipo, grupo, rh))