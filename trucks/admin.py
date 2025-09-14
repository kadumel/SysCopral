from django.contrib import admin
from .models import TrucksVeiculos


@admin.register(TrucksVeiculos)
class TrucksVeiculosAdmin(admin.ModelAdmin):
    list_display = ['veiid', 'placa', 'vs', 'tcmd', 'tmac', 'ecmd', 'tp', 'ta', 'eqp', 'mot', 'prop', 'die', 'loc', 'ident', 'vmanut']
    list_filter = ['placa', 'vs', 'tcmd', 'tmac', 'ecmd', 'tp', 'ta', 'eqp', 'mot', 'prop', 'die', 'loc', 'ident', 'vmanut']
    search_fields = ['veiid', 'placa', 'vs', 'tcmd', 'tmac', 'ecmd', 'tp', 'ta', 'eqp', 'mot', 'prop', 'die', 'loc', 'ident', 'vmanut']
    list_per_page = 10
    list_display_links = ['veiid', 'placa']
    list_editable = ['vs', 'tcmd', 'tmac', 'ecmd', 'tp', 'ta', 'eqp', 'mot', 'prop', 'die', 'loc', 'ident', 'vmanut']
    list_max_show_all = 100
    