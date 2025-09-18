from django import template

register = template.Library()

@register.filter
def dict_lookup(dictionary, key):
    """
    Permite acessar valores de dicionário no template Django.
    Uso: {{ meu_dict|dict_lookup:chave }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key, 0)
    return 0
