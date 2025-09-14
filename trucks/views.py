from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import json
from .models import TrucksVeiculos


class GestaoVeiculosView(LoginRequiredMixin, TemplateView):
    """
    View para gestão de veículos e motoristas
    """
    template_name = 'trucks/gestao_veiculos.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['veiculos'] = TrucksVeiculos.objects.all().order_by('placa')
        return context


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def atualizar_motorista(request):
    """
    View para atualizar o motorista de um veículo via AJAX
    """
    try:
        data = json.loads(request.body)
        veiculo_id = data.get('id')
        novo_motorista = data.get('motorista', '').strip()
        
        if not veiculo_id:
            return JsonResponse({'success': False, 'error': 'ID do veículo é obrigatório'})
        
        try:
            veiculo = TrucksVeiculos.objects.get(id=veiculo_id)
            veiculo.mot = novo_motorista
            veiculo.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Motorista atualizado para a placa {veiculo.placa}',
                'motorista': novo_motorista
            })
            
        except TrucksVeiculos.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Veículo não encontrado'})
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados JSON inválidos'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def criar_veiculo(request):
    """
    View para criar um novo veículo
    """
    try:
        data = json.loads(request.body)
        veiid = data.get('veiid')
        placa = data.get('placa', '').strip().upper()
        motorista = data.get('motorista', '').strip()
        
        # Validações básicas
        if not placa:
            return JsonResponse({'success': False, 'error': 'Placa é obrigatória'})
        
        if len(placa) != 7:
            return JsonResponse({'success': False, 'error': 'Placa deve ter 7 caracteres'})
        
        # Verificar se a placa já existe
        if TrucksVeiculos.objects.filter(placa=placa).exists():
            return JsonResponse({'success': False, 'error': f'Placa {placa} já existe'})
        
        # Criar novo veículo
        veiculo = TrucksVeiculos.objects.create(
            veiid=veiid,
            placa=placa,
            mot=motorista
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Veículo {placa} criado com sucesso',
            'veiculo': {
                'id': veiculo.id,
                'veiid': veiculo.veiid,
                'placa': veiculo.placa,
                'mot': veiculo.mot or ''
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados JSON inválidos'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def deletar_veiculo(request, veiculo_id):
    """
    View para deletar um veículo
    """
    try:
        veiculo = TrucksVeiculos.objects.get(id=veiculo_id)
        placa = veiculo.placa
        veiculo.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Veículo {placa} deletado com sucesso'
        })
        
    except TrucksVeiculos.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Veículo não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})