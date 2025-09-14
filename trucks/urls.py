from django.urls import path
from . import views

app_name = 'trucks'

urlpatterns = [
    path('gestao-veiculos/', views.GestaoVeiculosView.as_view(), name='gestao_veiculos'),
    path('api/atualizar-motorista/', views.atualizar_motorista, name='atualizar_motorista'),
    path('api/criar-veiculo/', views.criar_veiculo, name='criar_veiculo'),
    path('api/deletar-veiculo/<int:veiculo_id>/', views.deletar_veiculo, name='deletar_veiculo'),
]
