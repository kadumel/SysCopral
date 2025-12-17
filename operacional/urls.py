from django.urls import path
from . import views

app_name = 'operacional'

urlpatterns = [
    path('veiculos/', views.VeiculosListView.as_view(), name='veiculos'),
    path('servicos/', views.ServicosListView.as_view(), name='servicos'),
    path('itens/', views.ItensListView.as_view(), name='itens'),
    path('abastecimento/', views.AbastecimentoListView.as_view(), name='abastecimento'),
    path('servicos-movimentos/', views.ServicosMovimentosListView.as_view(), name='servicos_movimentos'),
    # Fechamento de caixa (serviços movimentos)
    path('servicos-movimentos/fechamento/check/', views.check_fechamento, name='check_fechamento'),
    path('servicos-movimentos/fechamento/fechar/', views.fechar_caixa, name='fechar_caixa'),
    # API JSON para modal (mantido)
    path('servicos-movimentos/carta-frete/', views.carta_frete, name='carta_frete_api'),
    # Página de gestão de Carta Frete
    path('carta-frete/', views.CartaFreteListView.as_view(), name='carta_frete_page'),
    # Geração de Contas a Pagar a partir da Carta Frete
    path('carta-frete/gerar/', views.gerar_contas_a_pagar, name='carta_frete_gerar'),
    path('contas-a-pagar/', views.ContasAPagarListView.as_view(), name='contas_a_pagar'),
    path('contas-a-pagar/<int:cap_id>/itens/', views.contas_a_pagar_itens, name='contas_a_pagar_itens'),
    path('contas-a-pagar/<int:cap_id>/vencimentos/', views.contas_a_pagar_vencimentos, name='contas_a_pagar_vencimentos'),
    path('contas-a-pagar/itens/<int:item_id>/excluir/', views.contas_a_pagar_excluir_item, name='contas_a_pagar_excluir_item'),
    path('contas-a-pagar/check/', views.contas_a_pagar_check, name='contas_a_pagar_check'),
    path('contas-a-pagar/<int:cap_id>/excluir/', views.contas_a_pagar_excluir, name='contas_a_pagar_excluir'),
    # Contas a Receber - gestão
    path('contas-a-receber/', views.ContasAReceberListView.as_view(), name='contas_a_receber'),
    path('contas-a-receber/<int:cr_id>/itens/', views.contas_a_receber_itens, name='contas_a_receber_itens'),
    path('contas-a-receber/<int:cr_id>/vencimentos/', views.contas_a_receber_vencimentos, name='contas_a_receber_vencimentos'),
    path('contas-a-receber/<int:cr_id>/excluir/', views.contas_a_receber_excluir, name='contas_a_receber_excluir'),
    path('contas-a-receber/itens/<int:item_id>/excluir/', views.contas_a_receber_excluir_item, name='contas_a_receber_excluir_item'),
    path('fechamentos/', views.FechamentosListView.as_view(), name='fechamentos'),
    path('gestao-fechamento/', views.GestaoFechamentoView.as_view(), name='gestao_fechamento'),
    path('gestao-fechamento/detalhes/', views.gestao_fechamento_detalhes, name='gestao_fechamento_detalhes'),
    path('gestao-fechamento/criar/', views.gestao_fechamento_criar, name='gestao_fechamento_criar'),
    path('gestao-fechamento/excluir/', views.gestao_fechamento_excluir, name='gestao_fechamento_excluir'),
    path('gestao-fechamento/enviar-ag/', views.gestao_fechamento_enviar_ag, name='gestao_fechamento_enviar_ag'),
    path('gestao-fechamento/enviar-ag-grupo/', views.gestao_fechamento_enviar_ag_grupo, name='gestao_fechamento_enviar_ag_grupo'),
    path('gestao-fechamento/detalhes/', views.gestao_fechamento_detalhes, name='gestao_fechamento_detalhes'),
    path('gestao-fechamento/placas/', views.gestao_fechamento_listar_placas, name='gestao_fechamento_listar_placas'),
    # Documentação
    path('docs/', views.OperacionalDocsView.as_view(), name='operacional_docs'),
    # Prestação de Contas (Movimentos)
    path('prestacao-contas/', views.PrestacaoContasView.as_view(), name='prestacao_contas'),
    path('prestacao-contas/pdf/', views.prestacao_contas_pdf, name='prestacao_contas_pdf'),
    path('fechamentos/<int:fechamento_id>/itens/', views.get_fechamento_itens, name='fechamento_itens'),
    path('fechamentos/<int:fechamento_id>/excluir/', views.excluir_fechamento, name='excluir_fechamento'),
    path('fechamentos/<int:fechamento_id>/alterar-data/', views.alterar_data_fechamento, name='alterar_data_fechamento'),
    path('fechamentos/itens/<int:item_id>/excluir/', views.excluir_item_fechamento, name='excluir_item_fechamento'),
    path('fechamentos/itens/<int:item_id>/mover/', views.mover_item_fechamento, name='mover_item_fechamento'),
    path('fechamentos/itens/<int:item_id>/atualizar/', views.atualizar_item_fechamento, name='atualizar_item_fechamento'),
    # URL para Atualizar Dados
    path('atualizar-dados/', views.AtualizarDadosView.as_view(), name='atualizar_dados'),
    # URLs existentes
    path('itens/sistemas-by-grupo/', views.get_sistemas_by_grupo, name='sistemas_by_grupo'),
    path('itens/save-percentages/', views.save_item_percentages, name='save_item_percentages'),
    path('itens/save-valor-sistema/', views.save_item_valor_sistema, name='save_item_valor_sistema'),
    path('servicos/save-valor/', views.save_servico_valor, name='save_servico_valor'),
    path('abastecimento/save-litros/', views.save_abastecimento_litros, name='save_abastecimento_litros'),
    # URLs para gestão de lançamentos
    path('lancamentos/', views.LancamentosListView.as_view(), name='lancamentos'),
    path('lancamentos/criar/', views.criar_lancamento, name='criar_lancamento'),
    path('lancamentos/<int:lancamento_id>/editar/', views.editar_lancamento, name='editar_lancamento'),
    path('lancamentos/<int:lancamento_id>/excluir/', views.excluir_lancamento, name='excluir_lancamento'),
    path('lancamentos/<int:lancamento_id>/obter/', views.obter_lancamento, name='obter_lancamento'),
]