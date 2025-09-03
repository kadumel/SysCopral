from django.urls import path
from .views import controleJornada, painel, relatorio, atualizarDados, ordemServicoList, ordemServicoCreate, ordemServicoUpdate, ordemServicoDelete, relatorio_movimento, home, cartao_visita

app_name = 'app'



urlpatterns = [
    path('', home, name='index'),
    path('home/', home, name='home'),
    path('painel/', painel, name='painel'),
    path('relatorio/', relatorio, name='relatorio'),
    path('relatorio_movimento/', relatorio_movimento, name='relatorio_mov'),
    path('atualizardados/', atualizarDados, name='atulizarDados'),
    path('ordem_servico/', ordemServicoList, name="os"),
    path('ordem_servico_create', ordemServicoCreate, name="os_create"),
    path('ordem_servico/atualiza_os/<int:id>', ordemServicoUpdate, name="os_update"),
    path('ordem_servico/deleta_os/<int:id>', ordemServicoDelete, name="os_delete"),
    path('rh/cartao-visita/', cartao_visita.as_view(), name='cartao_visita'),
    path('controle-jornada/', controleJornada, name='controleJornada'),
]