from django import template
from django.template.defaultfilters import floatformat
import locale

register = template.Library()

@register.filter
def brazilian_number(value, decimal_places=2):
    """
    Formata um número seguindo o padrão brasileiro:
    - Ponto (.) como separador de milhares
    - Vírgula (,) como separador decimal
    """
    if value is None or value == '':
        return '0,00'
    
    try:
        # Converte para float se necessário
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        elif not isinstance(value, (int, float)):
            value = float(value)
        
        # Formata o número com o número especificado de casas decimais
        if decimal_places == 0:
            formatted = f"{value:,.0f}"
        else:
            formatted = f"{value:,.{decimal_places}f}"
        
        # Substitui vírgula por ponto para milhares e ponto por vírgula para decimais
        # Primeiro, substitui vírgula por um placeholder temporário
        formatted = formatted.replace(',', '|TEMP|')
        # Substitui ponto por vírgula (decimal)
        formatted = formatted.replace('.', ',')
        # Substitui placeholder por ponto (milhares)
        formatted = formatted.replace('|TEMP|', '.')
        
        return formatted
        
    except (ValueError, TypeError):
        return '0,00'

@register.filter
def brazilian_currency(value, decimal_places=2):
    """
    Formata um valor monetário seguindo o padrão brasileiro:
    R$ 1.234,56
    """
    formatted_number = brazilian_number(value, decimal_places)
    return f"R$ {formatted_number}"

@register.filter
def multiply(value, arg):
    """
    Multiplica dois valores. Útil para calcular valor do abastecimento (litros * valor_litro)
    """
    try:
        if value is None or arg is None:
            return 0
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

