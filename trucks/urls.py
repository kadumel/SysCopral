from django.urls import path
from . import views

app_name = 'trucks'

urlpatterns = [
    path('gestao-veiculos/', views.GestaoVeiculosView.as_view(), name='gestao_veiculos'),
    path('api/atualizar-motorista/', views.atualizar_motorista, name='atualizar_motorista'),
    path('api/criar-veiculo/', views.criar_veiculo, name='criar_veiculo'),
    path('api/deletar-veiculo/<int:veiculo_id>/', views.deletar_veiculo, name='deletar_veiculo'),
    path('controle-jornada/', views.controleJornada, name='controleJornada'),
    path('dashboard-jornada/', views.DashboardJornadaView.as_view(), name='dashboardJornada'),
    path('importacao-excel/', views.ImportacaoExcelView.as_view(), name='importacaoExcel'),
    path('api/processar-arquivo-individual/', views.processar_arquivo_individual, name='processar_arquivo_individual'),
    path('processamento-excel/', views.ProcessamentoExcelView.as_view(), name='processamentoExcel'),
]
