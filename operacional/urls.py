from django.urls import path
from . import views

app_name = 'operacional'

urlpatterns = [
    path('veiculos/', views.VeiculosListView.as_view(), name='veiculos'),
    path('servicos/', views.ServicosListView.as_view(), name='servicos'),
    path('itens/', views.ItensListView.as_view(), name='itens'),
    path('abastecimento/', views.AbastecimentoListView.as_view(), name='abastecimento'),
    path('servicos-movimentos/', views.ServicosMovimentosListView.as_view(), name='servicos_movimentos'),
    # URL para Atualizar Dados
    path('atualizar-dados/', views.AtualizarDadosView.as_view(), name='atualizar_dados'),
    # URLs existentes
    path('itens/sistemas-by-grupo/', views.get_sistemas_by_grupo, name='sistemas_by_grupo'),
    path('itens/save-percentages/', views.save_item_percentages, name='save_item_percentages'),
    path('itens/save-valor-sistema/', views.save_item_valor_sistema, name='save_item_valor_sistema'),
    path('servicos/save-valor/', views.save_servico_valor, name='save_servico_valor'),
    path('abastecimento/save-litros/', views.save_abastecimento_litros, name='save_abastecimento_litros'),
    path('lancamentos/', views.LancamentosListView.as_view(), name='lancamentos'),
]   