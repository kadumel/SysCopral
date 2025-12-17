from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView
from django.db.models import Q, Sum, F
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
import re
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db import connection, transaction
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.staticfiles.storage import staticfiles_storage
from io import BytesIO
from PIL import Image  # type: ignore
import base64
import tempfile
from pathlib import Path
import os
try:
    from xhtml2pdf import pisa  # type: ignore
except Exception:
    pisa = None
from .models import Veiculo, Servico, Item, Abastecimento, Atualizações, Lancamento, OpeCategoria, Fechamento, ContasReceber, ItensContasReceber, ItensContasPagar, VencContasReceber, VencContasPagar, tipo_periodo

# Aliases para nomes de modelos que podem variar
try:
    from .models import ContasAPagar as ContasAPagarModel  # type: ignore
except Exception:
    try:
        from .models import ContasPagar as ContasAPagarModel  # type: ignore
    except Exception:
        ContasAPagarModel = None  # type: ignore
try:
    from .models import ItensContasAPagar as ItensContasAPagarModel  # type: ignore
except Exception:
    try:
        from .models import ItensContasPagar as ItensContasAPagarModel  # type: ignore
    except Exception:
        ItensContasAPagarModel = None  # type: ignore

# Compatibilidade: alias para o modelo de itens de fechamento
try:
    from .models import ItensFechamento as ItensFechamento  # pode não existir nas versões novas
except Exception:
    try:
        # usar ItensContasReceber como backend da tabela de itens quando não houver ItensFechamento
        ItensFechamento = ItensContasReceber  # type: ignore
    except Exception:
        try:
            # fallback para nomenclatura alternativa
            from .models import ItensContasAReceber as ItensFechamento  # type: ignore
        except Exception:
            pass
from datetime import date, timedelta, datetime  
from django.db import IntegrityError
import json
from django.utils import timezone
from django.contrib.auth.models import User
from .forms import LancamentoForm
# Create your views here.

class VeiculosListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Class-based view para listagem de veículos com filtro por placa e status, com paginação
    """
    model = Veiculo
    template_name = 'operacional/veiculos.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'veiculos'
    paginate_by = 10
    ordering = ['placa__placa']
    
    def get_queryset(self):
        """
        Retorna queryset filtrado por placa, frota, centro de custo, agregado e status
        """
        queryset = super().get_queryset().select_related('placa')
        
        placa_filtro = self.request.GET.get('placa', '')
        frota_filtro = self.request.GET.get('frota', '')
        centro_custo_filtro = self.request.GET.get('centro_custo', '')
        agregado_filtro = self.request.GET.get('agregado', '')
        status_filtro = self.request.GET.get('status', '')
        
        # Aplicar filtro por placa se fornecido
        if placa_filtro:
            queryset = queryset.filter(
                Q(placa__placa__icontains=placa_filtro)
            )
        
        # Aplicar filtro por frota se fornecido
        if frota_filtro:
            queryset = queryset.filter(
                Q(nm_frota__icontains=frota_filtro)
            )
        
        # Aplicar filtro por centro de custo se fornecido
        if centro_custo_filtro:
            queryset = queryset.filter(
                Q(nm_centro_custo__icontains=centro_custo_filtro)
            )
        
        # Aplicar filtro por agregado se fornecido
        if agregado_filtro:
            queryset = queryset.filter(
                Q(placa__nm_agregado__icontains=agregado_filtro)
            )
        
        # Aplicar filtro por status se fornecido
        if status_filtro:
            if status_filtro == 'ativo':
                queryset = queryset.filter(dt_inativacao__isnull=True)
            elif status_filtro == 'inativo':
                queryset = queryset.filter(dt_inativacao__isnull=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Adiciona contexto extra para os filtros e contagem total
        """
        context = super().get_context_data(**kwargs)
        
        placa_filtro = self.request.GET.get('placa', '')
        frota_filtro = self.request.GET.get('frota', '')
        centro_custo_filtro = self.request.GET.get('centro_custo', '')
        agregado_filtro = self.request.GET.get('agregado', '')
        status_filtro = self.request.GET.get('status', '')
        
        # Obter valores distintos para os seletores
        frotas_disponiveis = Veiculo.objects.values_list('nm_frota', flat=True).distinct().exclude(nm_frota__isnull=True).exclude(nm_frota__exact='').order_by('nm_frota')
        centros_custo_disponiveis = Veiculo.objects.values_list('nm_centro_custo', flat=True).distinct().exclude(nm_centro_custo__isnull=True).exclude(nm_centro_custo__exact='').order_by('nm_centro_custo')
        agregados_disponiveis = Veiculo.objects.select_related('placa').values_list('placa__nm_agregado', flat=True).distinct().exclude(placa__nm_agregado__isnull=True).exclude(placa__nm_agregado__exact='').order_by('placa__nm_agregado')
        
        context.update({
            'placa_filtro': placa_filtro,
            'frota_filtro': frota_filtro,
            'centro_custo_filtro': centro_custo_filtro,
            'agregado_filtro': agregado_filtro,
            'status_filtro': status_filtro,
            'frotas_disponiveis': frotas_disponiveis,
            'centros_custo_disponiveis': centros_custo_disponiveis,
            'agregados_disponiveis': agregados_disponiveis,
            'total_veiculos': self.get_queryset().count(),
        })
        
        return context


class ServicosListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Class-based view para listagem de serviços com filtros e paginação
    """
    model = Servico
    template_name = 'operacional/servicos.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'servicos'
    paginate_by = 10
    ordering = ['nm_servico']
    
    def get_queryset(self):
        """
        Retorna queryset filtrado por código, nome, tipo e sistema
        """
        queryset = super().get_queryset()
        
        cd_servico_filtro = self.request.GET.get('cd_servico', '')
        nm_servico_filtro = self.request.GET.get('nm_servico', '')
        tipo_servico_filtro = self.request.GET.get('tipo_servico', '')
        
        # Aplicar filtro por código do serviço se fornecido
        if cd_servico_filtro:
            queryset = queryset.filter(
                Q(cd_servico__icontains=cd_servico_filtro)
            )
        
        # Aplicar filtro por nome do serviço se fornecido
        if nm_servico_filtro:
            queryset = queryset.filter(
                Q(nm_servico__icontains=nm_servico_filtro)
            )
        
        # Aplicar filtro por tipo de serviço se fornecido
        if tipo_servico_filtro:
            queryset = queryset.filter(
                Q(nm_tipo_servico__icontains=tipo_servico_filtro)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Adiciona contexto extra para os filtros e contagem total
        """
        context = super().get_context_data(**kwargs)
        
        cd_servico_filtro = self.request.GET.get('cd_servico', '')
        nm_servico_filtro = self.request.GET.get('nm_servico', '')
        tipo_servico_filtro = self.request.GET.get('tipo_servico', '')
        
        # Obter valores distintos para os seletores
        tipos_servico_disponiveis = Servico.objects.values_list('nm_tipo_servico', flat=True).distinct().exclude(nm_tipo_servico__isnull=True).exclude(nm_tipo_servico__exact='').order_by('nm_tipo_servico')
        
        context.update({
            'cd_servico_filtro': cd_servico_filtro,
            'nm_servico_filtro': nm_servico_filtro,
            'tipo_servico_filtro': tipo_servico_filtro,
            'tipos_servico_disponiveis': tipos_servico_disponiveis,
            'total_servicos': self.get_queryset().count(),
        })
        
        return context


class ItensListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Class-based view para listagem de itens com filtros e paginação
    """
    model = Item
    template_name = 'operacional/itens.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'itens'
    paginate_by = 10
    ordering = ['nm_item']
    
    def get_queryset(self):
        """
        Retorna queryset filtrado por código, nome, grupo e sistema
        """
        queryset = super().get_queryset()

        
        cd_item_filtro = self.request.GET.get('cd_item', '')
        nm_item_filtro = self.request.GET.get('nm_item', '')
        grupo_filtro = self.request.GET.get('grupo', '')
        sistema_filtro = self.request.GET.get('sistema', '')
        
        # Aplicar filtro por código do item se fornecido (id_item é inteiro)
        if cd_item_filtro:
            try:
                queryset = queryset.filter(id_item=int(cd_item_filtro))
            except ValueError:
                # Se não for número, ignora o filtro de código
                pass
        
        # Aplicar filtro por nome do item se fornecido
        if nm_item_filtro:
            queryset = queryset.filter(
                Q(nm_item__icontains=nm_item_filtro)
            )
        
        # Aplicar filtro por grupo se fornecido
        if grupo_filtro:
            queryset = queryset.filter(
                Q(nm_grupo__icontains=grupo_filtro)
            )
        
        # Aplicar filtro por sistema se fornecido
        if sistema_filtro:
            queryset = queryset.filter(
                Q(nm_sistema__icontains=sistema_filtro)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Adiciona contexto extra para os filtros e contagem total
        """
        context = super().get_context_data(**kwargs)
        
        cd_item_filtro = self.request.GET.get('cd_item', '')
        nm_item_filtro = self.request.GET.get('nm_item', '')
        grupo_filtro = self.request.GET.get('grupo', '')
        sistema_filtro = self.request.GET.get('sistema', '')
        
        # Obter valores distintos para os seletores
        grupos_disponiveis = Item.objects.values_list('nm_grupo', flat=True).distinct().exclude(nm_grupo__isnull=True).exclude(nm_grupo__exact='').order_by('nm_grupo')
        sistemas_disponiveis = Item.objects.values_list('nm_sistema', flat=True).distinct().exclude(nm_sistema__isnull=True).exclude(nm_sistema__exact='').order_by('nm_sistema')
        
        context.update({
            'cd_item_filtro': cd_item_filtro,
            'nm_item_filtro': nm_item_filtro,
            'grupo_filtro': grupo_filtro,
            'sistema_filtro': sistema_filtro,
            'grupos_disponiveis': grupos_disponiveis,
            'sistemas_disponiveis': sistemas_disponiveis,
            'total_itens': self.get_queryset().count(),
        })
        
        
        return context


def get_sistemas_by_grupo(request):
    """
    View para retornar sistemas filtrados por grupo via AJAX
    """
    grupo = request.GET.get('grupo', '')
    if grupo:
        sistemas = Item.objects.filter(
            nm_grupo__icontains=grupo
        ).values_list('nm_sistema', flat=True).distinct().exclude(
            nm_sistema__isnull=True
        ).exclude(
            nm_sistema__exact=''
        ).order_by('nm_sistema')
        sistemas_list = list(sistemas)
    else:
        # Se não há grupo selecionado, retorna todos os sistemas
        sistemas = Item.objects.values_list('nm_sistema', flat=True).distinct().exclude(
            nm_sistema__isnull=True
        ).exclude(
            nm_sistema__exact=''
        ).order_by('nm_sistema')
        sistemas_list = list(sistemas)
    
    return JsonResponse({'sistemas': sistemas_list})


@csrf_exempt
@require_http_methods(["POST"])
def save_item_percentages(request):
    """
    View para salvar alterações de percentual dos itens via AJAX
    """
    try:
        data = request.POST
        item_id = data.get('item_id')
        codigo = (data.get('codigo') or '').strip()
        nm_item = (data.get('nm_item') or '').strip()
        new_percentage = data.get('percentage')
        
        if (not item_id and not codigo and not nm_item) or new_percentage is None:
            return JsonResponse({
                'success': False,
                'message': 'Dados incompletos'
            }, status=400)
        
        # Normalizar e validar percentual (aceita vírgula como decimal)
        try:
            perc_str = str(new_percentage).strip()
            # Regra de normalização:
            # - Se houver vírgula, tratar como separador decimal -> remover pontos (milhar) e trocar vírgula por ponto
            # - Caso não haja vírgula, manter pontos como separador decimal (não remover)
            if ',' in perc_str:
                perc_str = perc_str.replace('.', '')
                perc_str = perc_str.replace(',', '.')
            percentage_value = float(perc_str)
            if percentage_value < 0 or percentage_value > 100:
                return JsonResponse({
                    'success': False,
                    'message': 'Percentual deve estar entre 0 e 100'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Percentual deve ser um número válido'
            }, status=400)
        
        # Buscar e atualizar o item
        # Tenta por id_item, depois por pro_codigo, depois por nm_item (exato)
        item_obj = None
        item_pk_str = re.sub(r'\D', '', str(item_id or '').strip())
        if item_pk_str:
            try:
                item_obj = Item.objects.get(id_item=int(item_pk_str))
            except Item.DoesNotExist:
                item_obj = None
        if item_obj is None and codigo:
            try:
                item_obj = Item.objects.get(pro_codigo=codigo)
            except Item.DoesNotExist:
                item_obj = None
        if item_obj is None and nm_item:
            try:
                item_obj = Item.objects.get(nm_item=nm_item)
            except Item.DoesNotExist:
                item_obj = None
        if item_obj is None:
            return JsonResponse({'success': False, 'message': 'Item não encontrado (id/código/nome).'}, status=404)
        print('[Itens] save_item_percentages', {
            'item_id': getattr(item_obj, 'id_item', None),
            'raw': new_percentage,
            'normalized': percentage_value
        })
        item_obj.percentual = percentage_value
        item_obj.save(update_fields=['percentual'])
        return JsonResponse({
            'success': True,
            'message': 'Percentual atualizado com sucesso',
            'new_percentage': percentage_value
        })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao salvar: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_servico_valor(request):
    """
    View para salvar alterações de valor do serviço via AJAX
    Espera: servico_id (cd_servico) e value (float >= 0)
    """
    try:
        data = request.POST
        servico_id = data.get('servico_id')
        new_value = data.get('value')

        if not servico_id or new_value is None:
            return JsonResponse({
                'success': False,
                'message': 'Dados incompletos'
            }, status=400)

        try:
            value_float = float(new_value)
            if value_float < 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Valor deve ser maior ou igual a 0'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Valor deve ser um número válido'
            }, status=400)

        try:
            servico = Servico.objects.get(cd_servico=servico_id)
            servico.valor = value_float
            servico.save()
            return JsonResponse({
                'success': True,
                'message': 'Valor do serviço atualizado com sucesso',
                'new_value': value_float
            })
        except Servico.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Serviço não encontrado'
            }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao salvar: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_item_valor_sistema(request):
    """
    View para salvar alterações de valor do sistema dos itens via AJAX
    Espera: item_id (cd_item) e value (float)
    """
    try:
        data = request.POST
        item_id = data.get('item_id') or data.get('id')
        codigo = (data.get('codigo') or '').strip()
        nm_item = (data.get('nm_item') or '').strip()
        new_value = data.get('value') or data.get('valor')

        if (not item_id and not codigo and not nm_item) or new_value is None:
            return JsonResponse({
                'success': False,
                'message': 'Dados incompletos'
            }, status=400)

        # Normalizar e validar valor numérico (aceita vírgula como decimal)
        try:
            val_str = str(new_value).strip()
            # Regra de normalização:
            # - Se houver vírgula, tratar como separador decimal -> remover pontos (milhar) e trocar vírgula por ponto
            # - Caso não haja vírgula, manter pontos como separador decimal (não remover)
            if ',' in val_str:
                val_str = val_str.replace('.', '')
                val_str = val_str.replace(',', '.')
            value_float = float(val_str)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Valor deve ser um número válido'
            }, status=400)

        # Atualizar item com fallback: id_item -> pro_codigo -> nm_item
        item_obj = None
        item_pk_str = re.sub(r'\D', '', str(item_id or '').strip())
        if item_pk_str:
            try:
                item_obj = Item.objects.get(id_item=int(item_pk_str))
            except Item.DoesNotExist:
                item_obj = None
        if item_obj is None and codigo:
            try:
                item_obj = Item.objects.get(pro_codigo=codigo)
            except Item.DoesNotExist:
                item_obj = None
        if item_obj is None and nm_item:
            try:
                item_obj = Item.objects.get(nm_item=nm_item)
            except Item.DoesNotExist:
                item_obj = None
        if item_obj is None:
            return JsonResponse({'success': False, 'message': 'Item não encontrado (id/código/nome).'}, status=404)
        print('[Itens] save_item_valor_sistema', {
            'item_id': getattr(item_obj, 'id_item', None),
            'raw': new_value,
            'normalized': value_float
        })
        item_obj.vl_sistema = value_float
        item_obj.save(update_fields=['vl_sistema'])
        return JsonResponse({
            'success': True,
            'message': 'Valor do sistema atualizado com sucesso',
            'new_value': value_float
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao salvar: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_abastecimento_litros(request):
    """
    View para salvar alterações de litros dos abastecimentos via AJAX
    Espera: abastecimento_id e litros (float >= 0)
    """
    try:
        data = request.POST
        abastecimento_id = data.get('abastecimento_id')
        new_litros = data.get('litros')

        if not abastecimento_id or new_litros is None:
            return JsonResponse({
                'success': False,
                'message': 'Dados incompletos'
            }, status=400)

        try:
            litros_float = float(new_litros)
            if litros_float < 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Litros deve ser maior ou igual a 0'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Litros deve ser um número válido'
            }, status=400)

        try:
            abastecimento = Abastecimento.objects.get(id=abastecimento_id)
            abastecimento.qt_litros = litros_float
            abastecimento.save()
            return JsonResponse({
                'success': True,
                'message': 'Litros atualizados com sucesso',
                'new_value': litros_float
            })
        except Abastecimento.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Abastecimento não encontrado'
            }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao salvar: {str(e)}'
        }, status=500)


class AbastecimentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View para listar abastecimentos com filtros e paginação
    """
    model = Abastecimento
    template_name = 'operacional/abastecimento.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'abastecimentos'
    paginate_by = 10
    ordering = ['-dt_abastecimento']

    def get_queryset(self):
        """
        Aplica filtros baseados nos parâmetros GET
        """
        queryset = super().get_queryset().select_related(
            'id_veiculo__placa',  # Otimizar acesso à placa
            'id_item'             # Otimizar acesso ao item
        )
        
        # Filtro por placa (através do relacionamento com Veiculo -> Agregado)
        placa_filtro = self.request.GET.get('placa', '')
        if placa_filtro:
            queryset = queryset.filter(
                Q(id_veiculo__placa__placa__icontains=placa_filtro)
            )
        
        # Filtro por data inicial
        data_inicial_filtro = self.request.GET.get('data_inicial', '')
        if data_inicial_filtro:
            queryset = queryset.filter(
                Q(dt_abastecimento__date__gte=data_inicial_filtro)
            )
        
        # Filtro por data final
        data_final_filtro = self.request.GET.get('data_final', '')
        if data_final_filtro:
            queryset = queryset.filter(
                Q(dt_abastecimento__date__lte=data_final_filtro)
            )
        
        # Filtro por tipo de combustível (através do relacionamento com Item)
        tipo_combustivel_filtro = self.request.GET.get('tipo_combustivel', '')
        if tipo_combustivel_filtro:
            queryset = queryset.filter(
                Q(id_item__nm_item__icontains=tipo_combustivel_filtro)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Adiciona contexto extra para os filtros e contagem total
        """
        context = super().get_context_data(**kwargs)
        
        placa_filtro = self.request.GET.get('placa', '')
        data_inicial_filtro = self.request.GET.get('data_inicial', '')
        data_final_filtro = self.request.GET.get('data_final', '')
        tipo_combustivel_filtro = self.request.GET.get('tipo_combustivel', '')
        
        # Se não houver filtros de data, definir como mês atual
        if not data_inicial_filtro:
            # Primeiro dia do mês atual
            hoje = date.today()
            data_inicial_filtro = hoje.replace(day=1).strftime('%Y-%m-%d')
        
        if not data_final_filtro:
            # Último dia do mês atual
            hoje = date.today()
            # Calcular o primeiro dia do próximo mês e subtrair 1 dia
            if hoje.month == 12:
                proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1)
            else:
                proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
            ultimo_dia = (proximo_mes - timedelta(days=1))
            data_final_filtro = ultimo_dia.strftime('%Y-%m-%d')
        
        # Obter valores distintos para os seletores
        tipos_combustivel = Item.objects.values_list('nm_item', flat=True).distinct().exclude(nm_item__isnull=True).exclude(nm_item__exact='').order_by('nm_item')
        
        # Calcular indicadores
        queryset = self.get_queryset()
        
        # Quantidade de veículos (contagem distinta)
        quantidade_veiculos = queryset.values('id_veiculo').distinct().count()
        
        # Total quilometragem (somatório da quilometragem)
        total_quilometragem = queryset.aggregate(
            total_km=Sum('total_km')
        )['total_km'] or 0
        
        # Total litros (somatório dos litros)
        total_litros = queryset.aggregate(
            total_litros=Sum('qt_litros')
        )['total_litros'] or 0
        
        # Total gasto (litros * valor por litro) - usando vl_litro
        total_gasto = queryset.aggregate(
            total_gasto=Sum(
                F('qt_litros') * F('vl_litro')
            )
        )['total_gasto'] or 0
        
        # Média km/l (total_km / total_litros)
        try:
            media_km_por_litro = (float(total_quilometragem) / float(total_litros)) if float(total_litros or 0) > 0 else 0.0
        except Exception:
            media_km_por_litro = 0.0
        
        context.update({
            'placa_filtro': placa_filtro,
            'data_inicial_filtro': data_inicial_filtro,
            'data_final_filtro': data_final_filtro,
            'tipo_combustivel_filtro': tipo_combustivel_filtro,
            'tipos_combustivel': tipos_combustivel,
            'total_abastecimentos': self.get_queryset().count(),
            'quantidade_veiculos': quantidade_veiculos,
            'total_quilometragem': total_quilometragem,
            'total_litros': total_litros,
            'total_gasto': total_gasto,
            'media_km_por_litro': media_km_por_litro,
        })
        # Calcular km por litro por linha para uso no template
        try:
            abasts = context.get(self.context_object_name) or context.get('object_list') or []
            for a in abasts:
                try:
                    litros = float(getattr(a, 'qt_litros', 0) or 0)
                    km = float(getattr(a, 'total_km', 0) or 0)
                    a.km_por_litro = (km / litros) if litros and litros != 0 else None
                except Exception:
                    a.km_por_litro = None
        except Exception:
            pass
        
        return context

class OperacionalDocsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'docs/operacional_documentation.html'
    permission_required = 'operacional.acessar_operacional'

class PrestacaoContasView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Página para gerar o documento de Prestação de Contas por placa/data de fechamento.
    A lista de itens é obtida via endpoint existente `gestao_fechamento_detalhes`.
    """
    template_name = 'operacional/prestacao_contas.html'
    permission_required = 'operacional.acessar_operacional'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            placas = list(
                Veiculo.objects.select_related('placa')
                .values_list('placa__placa', flat=True)
                .distinct().order_by('placa__placa')
            )
        except Exception:
            placas = []
        context.update({
            'placas_disponiveis': placas,
            'data_fechamento': (self.request.GET.get('data_fechamento') or '').strip(),
            'placa_filtro': (self.request.GET.get('placa') or '').strip(),
        })
        return context


# View para Atualizar Dados

class AtualizarDadosView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View para executar procedures de atualização de dados
    """
    template_name = 'operacional/atualizar_dados.html'
    permission_required = 'operacional.acessar_operacional'
    
    def post(self, request, *args, **kwargs):
        """
        Executa as procedures de atualização quando o formulário é submetido
        """
        # Executar procedure de cadastros
        try:
            # Usar autocommit para evitar problemas de transação
            with connection.cursor() as cursor:
                # Garantir autocommit
                cursor.execute("SET IMPLICIT_TRANSACTIONS OFF")
                cursor.execute("EXEC sp_cadastros")
                
            # Registrar atualização
            Atualizações.objects.update_or_create(
                objeto="Cadastros", 
                defaults={'dt_atualizacao': timezone.now() - timedelta(hours=3)}
            )
            messages.success(request, 'Cadastros atualizados com sucesso!')
                
        except Exception as e1:
            messages.error(request, f'Erro na atualização de cadastros: {str(e1)}')
        
        # Executar procedure de abastecimentos
        try:
            # Usar autocommit para evitar problemas de transação
            with connection.cursor() as cursor:
                # Garantir autocommit
                cursor.execute("SET IMPLICIT_TRANSACTIONS OFF")
                cursor.execute("EXEC sp_abastecimento")
                
            # Registrar atualização
            Atualizações.objects.update_or_create(
                objeto="Abastecimentos", 
                defaults={'dt_atualizacao': timezone.now() - timedelta(hours=3)}
            )
            messages.success(request, 'Abastecimentos atualizados com sucesso!')
                
        except Exception as e2:
            messages.error(request, f'Erro na atualização de abastecimentos: {str(e2)}')
            
        return self.get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adicionar informações sobre última atualização, contadores, etc.
        # Buscar últimas atualizações
        try:
            ultima_atualizacao_cadastros = Atualizações.objects.filter(objeto="Cadastros").order_by('-dt_atualizacao').first()
            ultima_atualizacao_abastecimentos = Atualizações.objects.filter(objeto="Abastecimentos").order_by('-dt_atualizacao').first()
        except:
            ultima_atualizacao_cadastros = None
            ultima_atualizacao_abastecimentos = None
        
        context.update({
            'total_veiculos': Veiculo.objects.count(),
            'total_servicos': Servico.objects.count(),
            'total_itens': Item.objects.count(),
            'total_abastecimentos': Abastecimento.objects.count(),
            'ultima_atualizacao_cadastros': ultima_atualizacao_cadastros,
            'ultima_atualizacao_abastecimentos': ultima_atualizacao_abastecimentos,
        })
        
        return context


class ServicosMovimentosListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Lista serviços de movimentações a partir da view de banco VW_MOVIMENTACOES
    """
    template_name = 'operacional/servicos_movimentos.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'servicos'
    paginate_by = None

    def get_queryset(self):
        """
        Busca dados diretamente da view VW_MOVIMENTACOES aplicando filtros opcionais.
        Retorna uma lista de dicts compatível com o template.
        """
        placa_filtro = self.request.GET.get('placa', '').strip()
        agregado_filtro = self.request.GET.get('agregado', '').strip()
        data_inicio = self.request.GET.get('data_inicio', '').strip()
        data_fim = self.request.GET.get('data_fim', '').strip()

        # Não carregar dados inicialmente: exigir ao menos um filtro
        if not any([placa_filtro, agregado_filtro, data_inicio, data_fim]):
            return []

        # Descobrir nomes reais das colunas da view
        with connection.cursor() as cursor:
            cursor.execute("SELECT TOP 1 * FROM VW_MOVIMENTACOES")
            all_cols = [c[0] for c in cursor.description]

        cols_lower = {c.lower(): c for c in all_cols}

        def find_col(candidates, fallback_contains=None):
            # tenta casar por nomes conhecidos
            for cand in candidates:
                if cand in cols_lower:
                    return cols_lower[cand]
            # fallback: tenta por substring no nome da coluna
            if fallback_contains:
                for k_lower, orig in cols_lower.items():
                    if fallback_contains in k_lower:
                        return orig
            return None

        code_col = find_col(['cdservico', 'cd_servico', 'codigo', 'codigo_servico', 'cdserv', 'idservico'], fallback_contains='servico')
        name_col = find_col(['nmservico', 'nm_servico', 'nome_servico', 'servico', 'descricao', 'descricao_servico'], fallback_contains='serv')
        type_col = find_col(['nmtiposervico', 'nm_tipo_servico', 'tipo_servico', 'tipo', 'categoria', 'nmtipo'], fallback_contains='tipo')
        value_col = find_col(['valor', 'vl_servico', 'vlr', 'vl', 'preco', 'preco_servico'], fallback_contains='valor')
        plate_col = find_col(['placa', 'nrplaca', 'nr_placa', 'placa_principal', 'placa1'], fallback_contains='placa')
        agregado_col = find_col(['agregado', 'nmagregado', 'nm_agregado', 'agregado_nome', 'nome_agregado'], fallback_contains='agreg')
        date_col = find_col(['data', 'dtmov', 'dt_mov', 'dtservico', 'dt_servico', 'dtmovimento', 'data_mov', 'dt_emissao', 'dtemissao'], fallback_contains='data')
        os_col = find_col(['cdorderservico', 'orderservico', 'ordemservico', 'cdordemservico', 'cd_os', 'os'], fallback_contains='servico')
        qty_col = find_col(['qtde', 'quantidade', 'qtd'], fallback_contains='qt')
        total_col = find_col(['total', 'vl_total', 'vltotal'], fallback_contains='total')
        item_code_col = find_col(['cditem', 'cd_item', 'codigo_item'], fallback_contains='item')
        item_name_col = find_col(['nmitem', 'nm_item', 'nome_item', 'descricao_item'], fallback_contains='item')
        status_col = find_col(['status', 'st'], fallback_contains='status')
        unit_col = find_col(['unidade', 'unid', 'und', 'un'])

        select_parts = []
        if code_col: select_parts.append(f"{code_col} AS code_col")
        if name_col: select_parts.append(f"{name_col} AS name_col")
        if type_col: select_parts.append(f"{type_col} AS type_col")
        if value_col: select_parts.append(f"{value_col} AS value_col")
        if plate_col: select_parts.append(f"{plate_col} AS plate_col")
        if agregado_col: select_parts.append(f"{agregado_col} AS agregado_col")
        if date_col: select_parts.append(f"{date_col} AS date_col")
        if os_col: select_parts.append(f"{os_col} AS os_col")
        if qty_col: select_parts.append(f"{qty_col} AS qty_col")
        if total_col: select_parts.append(f"{total_col} AS total_col")
        if item_code_col: select_parts.append(f"{item_code_col} AS item_code_col")
        if item_name_col: select_parts.append(f"{item_name_col} AS item_name_col")
        if status_col: select_parts.append(f"{status_col} AS status_col")
        if unit_col: select_parts.append(f"{unit_col} AS unit_col")
        if not select_parts:
            select_parts.append("*")

        sql = []
        if select_parts:
            sql = [
                "SELECT "+", ".join(select_parts),
                "FROM VW_MOVIMENTACOES",
            ]
        else:
            # Tenta conjunto padrão de colunas conforme modelo Fechamento
            code_col = 'CDSERVICO'
            name_col = 'NMSERVICO'
            type_col = 'TIPO'
            value_col = 'VALOR'
            plate_col = 'PLACA'
            item_code_col = 'CDITEM'
            item_name_col = 'NMITEM'
            qty_col = 'QTDE'
            total_col = 'TOTAL'
            date_col = 'DATA'
            sql = [
                "SELECT PLACA AS plate_col, DATA AS date_col, CDSERVICO AS code_col, NMSERVICO AS name_col,",
                "       TIPO AS type_col, CDITEM AS item_code_col, NMITEM AS item_name_col,",
                "       QTDE AS qty_col, VALOR AS value_col, TOTAL AS total_col",
                "FROM VW_MOVIMENTACOES",
            ]
        where = []
        params = []


        if placa_filtro and plate_col:
            where.append(f"{plate_col} LIKE %s")
            params.append(f"%{placa_filtro}%")

        if agregado_filtro and agregado_col:
            where.append(f"{agregado_col} LIKE %s")
            params.append(f"%{agregado_filtro}%")

        if data_inicio and date_col:
            where.append(f"CAST({date_col} AS DATE) >= %s")
            params.append(data_inicio)

        if data_fim and date_col:
            where.append(f"CAST({date_col} AS DATE) <= %s")
            params.append(data_fim)

        if where:
            sql.append("WHERE " + " AND ".join(where))

        if name_col:
            sql.append(f"ORDER BY {name_col} ASC")
        elif code_col:
            sql.append(f"ORDER BY {code_col} ASC")

        rows = []
        with connection.cursor() as cursor:
            cursor.execute("\n".join(sql), params)
            print(sql)
            print(params)
            cols = [col[0].lower() for col in cursor.description]
            for r in cursor.fetchall():
                row = dict(zip(cols, r))
                rows.append({
                    'cd_servico': row.get('code_col') if 'code_col' in row else row.get((code_col or '').lower()),
                    'nm_servico': row.get('name_col') if 'name_col' in row else row.get((name_col or '').lower()),
                    'nm_tipo_servico': row.get('type_col') if 'type_col' in row else row.get((type_col or '').lower()),
                    'valor': row.get('value_col') if 'value_col' in row else row.get((value_col or '').lower()) or 0,
                    'placa': row.get('plate_col') if 'plate_col' in row else row.get((plate_col or '').lower()) if plate_col else None,
                    'agregado': row.get('agregado_col') if 'agregado_col' in row else row.get((agregado_col or '').lower()) if agregado_col else None,
                    'data': row.get('date_col') if 'date_col' in row else row.get((date_col or '').lower()) if date_col else None,
                    'ordem_servico': row.get('os_col') if 'os_col' in row else row.get((os_col or '').lower()) if os_col else None,
                    'quantidade': row.get('qty_col') if 'qty_col' in row else row.get((qty_col or '').lower()) if qty_col else None,
                    'total': row.get('total_col') if 'total_col' in row else row.get((total_col or '').lower()) if total_col else None,
                    'cd_item': row.get('item_code_col') if 'item_code_col' in row else row.get((item_code_col or '').lower()) if item_code_col else None,
                    'nm_item': row.get('item_name_col') if 'item_name_col' in row else row.get((item_name_col or '').lower()) if item_name_col else None,
                    'unidade': row.get('unit_col') if 'unit_col' in row else row.get((unit_col or '').lower()) if unit_col else None,
                    'status': row.get('status_col') if 'status_col' in row else None,
                })

        return rows

    def _agrupar_hierarquia(self, rows, data_inicio=None, data_fim=None, status_filter=None):
        grupos = {}
        # Coleta códigos/ids para minimizar queries
        service_codes = set()
        item_ids = set()
        for r in rows:
            if r.get('cd_servico') is not None:
                service_codes.add(r.get('cd_servico'))
            if r.get('cd_item') is not None:
                item_ids.add(r.get('cd_item'))

        # Cache de valores de serviço e percentuais de item
        servico_code_to_valor = {}
        if service_codes:
            for s in Servico.objects.filter(cd_servico__in=list(service_codes)).values('cd_servico', 'valor'):
                servico_code_to_valor[s['cd_servico']] = s['valor'] or 0

        # Preparar chaves robustas para itens: tanto por id_item (int) quanto por pro_codigo (str) e nm_item
        item_id_to_percent = {}
        item_code_to_percent = {}
        item_name_to_percent = {}
        # Mapas de valor do sistema (unitário) por item
        item_id_to_vl_sistema = {}
        item_code_to_vl_sistema = {}
        item_name_to_vl_sistema = {}
        if item_ids:
            # tentar por id_item
            for it in Item.objects.filter(id_item__in=list(item_ids)).values('id_item', 'percentual', 'vl_sistema'):
                item_id_to_percent[it['id_item']] = it['percentual'] or 0
                item_id_to_vl_sistema[it['id_item']] = it.get('vl_sistema') or 0
        # também coletar códigos como string a partir dos rows, pois algumas views usam códigos não numéricos
        item_codes_str = set()
        item_names_str = set()
        for r in rows:
            cd_item_val = r.get('cd_item')
            if cd_item_val is not None:
                try:
                    # preservar como string normalizada
                    item_codes_str.add(str(cd_item_val).strip())
                except Exception:
                    pass
            nm_item_val = r.get('nm_item')
            if nm_item_val:
                try:
                    item_names_str.add(str(nm_item_val).strip().upper())
                except Exception:
                    pass
        if item_codes_str:
            for it in Item.objects.filter(pro_codigo__in=list(item_codes_str)).values('pro_codigo', 'percentual', 'vl_sistema'):
                key = str(it['pro_codigo']).strip()
                item_code_to_percent[key] = it['percentual'] or 0
                item_code_to_vl_sistema[key] = it.get('vl_sistema') or 0
        if item_names_str:
            for it in Item.objects.filter(nm_item__in=list(item_names_str)).values('nm_item', 'percentual', 'vl_sistema'):
                key = str(it['nm_item']).strip().upper()
                item_name_to_percent[key] = it['percentual'] or 0
                item_name_to_vl_sistema[key] = it.get('vl_sistema') or 0

        # Preparar mapa de status "fechado" por item (ordem, cd_item, data, placa)
        placas_str = set([ (r.get('placa') or '').strip() for r in rows if r.get('placa') ])
        plate_to_veic = {}
        if placas_str:
            for v in Veiculo.objects.select_related('placa').filter(placa__placa__in=list(placas_str)).values('id_veiculo','placa__placa'):
                plate_to_veic[v['placa__placa']] = v['id_veiculo']

        # Intervalo de datas
        di = self.request.GET.get('data_inicio') or data_inicio
        df = self.request.GET.get('data_fim') or data_fim
        items_qs = ItensFechamento.objects.select_related('contas_receber','contas_receber__placa','contas_receber__placa__placa')
        if di:
            items_qs = items_qs.filter(data__date__gte=di)
        if df:
            items_qs = items_qs.filter(data__date__lte=df)
        if plate_to_veic:
            items_qs = items_qs.filter(contas_receber__placa__in=list(plate_to_veic.values()))

        # Conjuntos de itens fechados por item e por serviço
        closed_by_item = set()
        closed_by_serv = set()
        for it in items_qs.values('ordemServico','cdItem','cdServico','data','contas_receber__placa__placa__placa'):
            plate_txt = it['contas_receber__placa__placa__placa']
            date_only = it['data'].date() if hasattr(it['data'],'date') else it['data']
            closed_by_item.add((it['ordemServico'], it.get('cdItem'), date_only, plate_txt))
            closed_by_serv.add((it['ordemServico'], it.get('cdServico'), date_only, plate_txt))

        for r in rows:
            placa = (r.get('placa') or '').strip() if r.get('placa') else 'SEM PLACA'
            tipo_raw = (r.get('nm_tipo_servico') or '').strip() if r.get('nm_tipo_servico') else ''
            tipo_norm = tipo_raw.lower().replace('ç','c').replace('õ','o').replace('ó','o').replace('á','a').replace('é','e').replace('í','i').replace('ú','u').replace('â','a').replace('ê','e').replace('ô','o')
            # Ocultar completamente o tipo "lançamento"
            if 'lancamento' in tipo_norm:
                continue
            tipo = tipo_raw if tipo_raw else 'SEM TIPO'
            total_item = r.get('total') if r.get('total') is not None else ((r.get('valor') or 0) * (r.get('quantidade') or 1))
            # Calcula "cobrar" com chaves normalizadas
            cobrar_val = 0.0
            cd_servico_row = r.get('cd_servico')
            cd_item_row = r.get('cd_item')
            # normalizar chaves para int quando possível
            def to_int_safe(v):
                try:
                    return int(v)
                except Exception:
                    return None
            cd_servico_key = to_int_safe(cd_servico_row) if cd_servico_row is not None else None
            cd_item_key = to_int_safe(cd_item_row) if cd_item_row is not None else None
            is_servico = 'servic' in tipo_norm  # somente quando o tipo indicar serviço
            if is_servico:
                # Serviço: usar valor do modelo; fallback para TOTAL do item
                base_val = servico_code_to_valor.get(cd_servico_key) if cd_servico_key is not None else None
                cobrar_val = float(base_val or 0)
                if cobrar_val == 0:
                    cobrar_val = float(total_item or 0)
                perc_display = 0.0  # para serviços não aplicar percentual por padrão
            else:
                # Demais tipos:
                # Regra de prioridade (unitário):
                # 1) Se houver vl_sistema (>0), usar vl_sistema (unitário)
                # 2) Caso contrário, usar (valor unitário "Vl Frota") + percentual do item aplicado sobre o unitário
                # Em ambos os casos, "cobrar" = unitário efetivo * quantidade
                # Buscar vl_sistema por id, código ou nome
                vl_sistema_lookup = 0
                if cd_item_key is not None and cd_item_key in item_id_to_vl_sistema:
                    vl_sistema_lookup = item_id_to_vl_sistema.get(cd_item_key) or 0
                else:
                    cd_item_raw = r.get('cd_item')
                    cd_item_str = str(cd_item_raw).strip() if cd_item_raw is not None else ''
                    vl_sistema_lookup = item_code_to_vl_sistema.get(cd_item_str) or 0
                    if not vl_sistema_lookup:
                        nm_item_raw = r.get('nm_item')
                        nm_item_key = str(nm_item_raw).strip().upper() if nm_item_raw else ''
                        vl_sistema_lookup = item_name_to_vl_sistema.get(nm_item_key) or 0
                try:
                    vl_sistema_f = float(vl_sistema_lookup or 0)
                except Exception:
                    vl_sistema_f = 0.0
                # Percentual do item
                perc_lookup = 0
                if cd_item_key is not None and cd_item_key in item_id_to_percent:
                    perc_lookup = item_id_to_percent.get(cd_item_key) or 0
                else:
                    # tentar por código como string
                    cd_item_raw = r.get('cd_item')
                    cd_item_str = str(cd_item_raw).strip() if cd_item_raw is not None else ''
                    perc_lookup = item_code_to_percent.get(cd_item_str) or 0
                    if not perc_lookup:
                        # fallback por nome do item
                        nm_item_raw = r.get('nm_item')
                        nm_item_key = str(nm_item_raw).strip().upper() if nm_item_raw else ''
                        perc_lookup = item_name_to_percent.get(nm_item_key) or 0
                try:
                    perc_f = float(perc_lookup or 0)
                except Exception:
                    perc_f = 0.0
                fator = perc_f if perc_f <= 1 else (perc_f / 100.0)
                unit_frota = 0.0
                try:
                    unit_frota = float(r.get('valor') or 0)
                except Exception:
                    unit_frota = 0.0
                qty_f = 0.0
                try:
                    qty_f = float(r.get('quantidade') or 0)
                except Exception:
                    qty_f = 0.0
                # Determinar unitário efetivo para "Vl Sistema"
                if vl_sistema_f > 0:
                    unit_eff = vl_sistema_f
                    perc_display = 0.0  # para exibição
                else:
                    unit_eff = unit_frota * (1 + (fator if fator else 0.0))
                    perc_display = perc_f if perc_f > 1 else (perc_f * 100.0)
                cobrar_val = unit_eff * qty_f

            if placa not in grupos:
                grupos[placa] = { 'placa': placa, 'total_placa': 0, 'cobrar_placa': 0, 'tipos': {}, 'status_placa': 'all_open' }

            if tipo not in grupos[placa]['tipos']:
                grupos[placa]['tipos'][tipo] = { 'tipo': tipo, 'total_tipo': 0, 'cobrar_tipo': 0, 'itens': [], 'has_open': False, 'has_closed': False, 'status_tipo': 'all_open' }

            # Determinar status do item fechado/aberto baseado APENAS no campo 'status' quando disponível
            status_raw = (r.get('status') or '').strip().lower() if r.get('status') else ''
            if status_raw in ('fechado', 'closed', '1', 'true'):
                item_fechado = True
            elif status_raw in ('aberto', 'open', '0', 'false'):
                item_fechado = False
            else:
                # fallback legacy (se status não vier na view)
                data_val = r.get('data')
                data_only = data_val.date() if hasattr(data_val,'date') else data_val
                os_val = r.get('ordem_servico')
                cd_item_val = r.get('cd_item')
                cd_serv_val = r.get('cd_servico')
                is_servico = 'servic' in tipo_norm
                if is_servico:
                    item_fechado = bool(cd_serv_val) and ((os_val, cd_serv_val, data_only, placa) in closed_by_serv)
                else:
                    item_fechado = bool(cd_item_val) and ((os_val, cd_item_val, data_only, placa) in closed_by_item)

            item_status_str = 'fechado' if item_fechado else 'aberto'
            # Aplicar filtro de status, se solicitado
            if status_filter in ('aberto', 'fechado') and item_status_str != status_filter:
                continue

            grupos[placa]['tipos'][tipo]['itens'].append({
                'data': r.get('data'),
                'ordem_servico': r.get('ordem_servico'),
                'cd_item': r.get('cd_item'),
                'nm_item': r.get('nm_item'),
                'quantidade': r.get('quantidade') or 0,
                'valor': r.get('valor') or 0,
                'total': total_item or 0,
                'perc': perc_display if 'perc_display' in locals() else 0.0,
                # "Vl Sistema" unitário efetivo (vl_sistema se >0, senão unitário + percentual do item)
                'vl_sistema': unit_eff if 'unit_eff' in locals() else (vl_sistema_f if 'vl_sistema_f' in locals() else 0.0),
                'cobrar': cobrar_val or 0,
                'cd_servico': r.get('cd_servico'),
                'nm_servico': r.get('nm_servico'),
                'unidade': r.get('unidade') or '',
                'status': item_status_str,
            })

            grupos[placa]['tipos'][tipo]['total_tipo'] += (total_item or 0)
            grupos[placa]['tipos'][tipo]['cobrar_tipo'] += (cobrar_val or 0)
            grupos[placa]['total_placa'] += (total_item or 0)
            grupos[placa]['cobrar_placa'] += (cobrar_val or 0)

            # Atualiza status agregador do tipo e da placa
            if item_fechado:
                grupos[placa]['tipos'][tipo]['has_closed'] = True
            else:
                grupos[placa]['tipos'][tipo]['has_open'] = True
            if 'has_closed' not in grupos[placa]:
                grupos[placa]['has_closed'] = False
                grupos[placa]['has_open'] = False
            if item_fechado:
                grupos[placa]['has_closed'] = True
            else:
                grupos[placa]['has_open'] = True

        # converter para listas ordenadas e definir status_placa, removendo tipos/placas sem itens
        lista = []
        for placa_key in sorted(grupos.keys()):
            tipo_list = []
            for tipo_key in sorted(grupos[placa_key]['tipos'].keys()):
                t = grupos[placa_key]['tipos'][tipo_key]
                # descarta tipos sem itens
                if not t['itens']:
                    continue
                if t['has_open'] and t['has_closed']:
                    t['status_tipo'] = 'mixed'
                elif t['has_closed'] and not t['has_open']:
                    t['status_tipo'] = 'all_closed'
                else:
                    t['status_tipo'] = 'all_open'
                tipo_list.append(t)

            # pular placas sem tipos válidos
            if not tipo_list:
                continue

            # status por placa baseado nos itens agregados
            has_open = grupos[placa_key].get('has_open', False)
            has_closed = grupos[placa_key].get('has_closed', False)
            if has_open and has_closed:
                placa_status = 'mixed'
            elif has_closed and not has_open:
                placa_status = 'all_closed'
            else:
                placa_status = 'all_open'

            lista.append({
                'placa': grupos[placa_key]['placa'],
                'total_placa': grupos[placa_key]['total_placa'],
                'cobrar_placa': grupos[placa_key].get('cobrar_placa', 0),
                'status_placa': placa_status,
                'tipos': tipo_list,
            })
        return lista

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Valores distintos para filtro de tipo vindos da view (descoberta de coluna dinâmica)
        tipos_servico_disponiveis = []
        with connection.cursor() as cursor:
            cursor.execute("SELECT TOP 1 * FROM VW_MOVIMENTACOES")
            all_cols = [c[0] for c in cursor.description]
        cols_lower = {c.lower(): c for c in all_cols}
        for cand in ['nmtiposervico', 'nm_tipo_servico', 'tipo_servico', 'tipo', 'categoria', 'nmtipo']:
            if cand in cols_lower:
                type_col = cols_lower[cand]
                break
        else:
            type_col = None

        if type_col:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT {type_col} FROM VW_MOVIMENTACOES WHERE {type_col} IS NOT NULL AND {type_col} <> '' ORDER BY {type_col}")
                tipos_servico_disponiveis = [row[0] for row in cursor.fetchall()]

        # Preparar grupos e métricas para cards
        rows_ctx = self.get_queryset()
        status_item_filtro = (self.request.GET.get('status_item') or '').strip().lower()
        if status_item_filtro not in ('aberto', 'fechado'):
            status_item_filtro = ''
        grupos_ctx = self._agrupar_hierarquia(rows_ctx, data_inicio=self.request.GET.get('data_inicio', ''), data_fim=self.request.GET.get('data_fim', ''), status_filter=status_item_filtro)
        # métricas
        total_placas = len(grupos_ctx)
        placas_fechadas = sum(1 for g in grupos_ctx if g.get('status_placa') == 'all_closed')
        placas_abertas = total_placas - placas_fechadas

        total_itens = 0
        itens_fechados = 0
        for g in grupos_ctx:
            for t in g.get('tipos', []):
                itens = t.get('itens', [])
                total_itens += len(itens)
                itens_fechados += sum(1 for it in itens if it.get('status') == 'fechado')
        itens_abertos = max(total_itens - itens_fechados, 0)

        context.update({
            'nm_servico_filtro': self.request.GET.get('nm_servico', ''),
            'tipo_servico_filtro': self.request.GET.get('tipo_servico', ''),
            'cd_servico_filtro': self.request.GET.get('cd_servico', ''),
            'placa_filtro': self.request.GET.get('placa', ''),
            'agregado_filtro': self.request.GET.get('agregado', ''),
            'data_inicio': self.request.GET.get('data_inicio', ''),
            'data_fim': self.request.GET.get('data_fim', ''),
            'tipos_servico_disponiveis': tipos_servico_disponiveis,
            'total_servicos': len(rows_ctx),
            'grupos': grupos_ctx,
            'status_item_filtro': status_item_filtro,
            # métricas para cards
            'metric_total_placas': total_placas,
            'metric_placas_fechadas': placas_fechadas,
            'metric_placas_abertas': placas_abertas,
            'metric_total_itens': total_itens,
            'metric_itens_fechados': itens_fechados,
            'metric_itens_abertos': itens_abertos,
            # Campos padrão para período/parcelas
            'periodos_choices': tipo_periodo,
            'periodo_selecionado': self.request.GET.get('periodo', 'S'),
            'parcela_selecionada': self.request.GET.get('parcela', 1),
        })

        return context


class FechamentosListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Gestão de fechamentos com filtros de placa e data de fechamento, tabela similar à de movimentações."""
    template_name = 'operacional/fechamentos.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'fechamentos'
    paginate_by = 20

    def get_queryset(self):
        cod_ag = (self.request.GET.get('cod_ag') or '').strip()
        agregado = (self.request.GET.get('agregado') or '').strip()
        placa = (self.request.GET.get('placa') or '').strip()
        data_fech = (self.request.GET.get('data_fechamento') or '').strip()  # yyyy-mm-dd
        qs = Fechamento.objects.select_related('placa', 'placa__placa').all().order_by('-data_fechamento')
        if cod_ag and any(getattr(f, 'name', '') == 'cod_ag' for f in Fechamento._meta.get_fields()):
            qs = qs.filter(cod_ag__icontains=cod_ag)
        if agregado:
            # Agregado (nome) associado ao veículo deste fechamento
            qs = qs.filter(placa__placa__nm_agregado=agregado)
        if placa:
            # filtra por placa do veículo (FK -> Agregado.placa)
            qs = qs.filter(placa__placa__placa__icontains=placa) if 'placa__placa__placa' in [lf.name for lf in Fechamento._meta.get_fields()] else qs.filter(placa__placa__icontains=placa)
        if data_fech:
            try:
                dt = datetime.strptime(data_fech, '%Y-%m-%d').date()
                qs = qs.filter(data_fechamento__date=dt)
            except Exception:
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Opções para selects
        datas_distintas = (
            Fechamento.objects.order_by('-data_fechamento')
            .values_list('data_fechamento__date', flat=True)
            .distinct()
        )
        datas_opcoes = [d.strftime('%Y-%m-%d') for d in datas_distintas if d]

        from .models import Agregado, Veiculo
        # Somente agregados que possuem registros de fechamento (via Veiculo)
        agregados_disponiveis = (
            Agregado.objects.filter(veiculos_placa__fechamentos_id_veiculo__isnull=False)
            .values_list('nm_agregado', flat=True)
            .distinct()
            .order_by('nm_agregado')
        )

        agregado_sel = self.request.GET.get('agregado', '')
        if agregado_sel:
            placas_disponiveis = (
                Veiculo.objects.select_related('placa')
                .filter(placa__nm_agregado=agregado_sel, fechamentos_id_veiculo__isnull=False)
                .values_list('placa__placa', flat=True)
                .distinct()
                .order_by('placa__placa')
            )
        else:
            placas_disponiveis = (
                Veiculo.objects.select_related('placa')
                .filter(fechamentos_id_veiculo__isnull=False)
                .values_list('placa__placa', flat=True)
                .distinct()
                .order_by('placa__placa')
            )

        # Total geral de fechamentos filtrados
        total_valor_fechamentos = self.get_queryset().aggregate(s=models.Sum('valor_total'))['s'] or 0.0

        context.update({
            'cod_ag_filtro': self.request.GET.get('cod_ag', ''),
            'agregado_filtro': agregado_sel,
            'placa_filtro': self.request.GET.get('placa', ''),
            'data_fechamento': self.request.GET.get('data_fechamento', ''),
            'total_registros': self.get_queryset().count(),
            'datas_fechamento_opcoes': datas_opcoes,
            'agregados_disponiveis': agregados_disponiveis,
            'placas_disponiveis': placas_disponiveis,
            'total_valor_fechamentos': float(total_valor_fechamentos),
        })
        return context


class ContasAPagarListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'operacional/contas_a_pagar.html'
    permission_required = 'operacional.acessar_operacional'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        di = (self.request.GET.get('data_inicio') or '').strip()
        df = (self.request.GET.get('data_fim') or '').strip()
        placa_f = (self.request.GET.get('placa') or '').strip()
        contas_list = []
        placas_disponiveis = []
        if ContasAPagarModel is not None:
            qs = ContasAPagarModel.objects.select_related('placa', 'placa__placa').all()
            if di:
                qs = qs.filter(data_fechamento__gte=di)
            if df:
                qs = qs.filter(data_fechamento__lte=df)
            if placa_f:
                try:
                    qs = qs.filter(placa__placa__placa__iexact=placa_f)
                except Exception:
                    # fallback em caso de diferente caminho de FK
                    qs = qs.filter(placa__placa__iexact=placa_f)
            qs = qs.order_by('-data_fechamento')
            # Descobrir nome do FK nos itens CAP (robusto a variações)
            fk_field_name = None
            try:
                if ItensContasAPagarModel is not None:
                    for f in ItensContasAPagarModel._meta.get_fields():
                        try:
                            if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:
                                fk_field_name = f.name
                                break
                        except Exception:
                            continue
            except Exception:
                fk_field_name = None
            for cab in qs:
                try:
                    if fk_field_name and ItensContasAPagarModel is not None:
                        qtd_itens = ItensContasAPagarModel.objects.filter(**{fk_field_name: cab}).count()
                    else:
                        qtd_itens = 0
                except Exception:
                    qtd_itens = 0
                try:
                    qtd_venc = VencContasPagar.objects.filter(contas_pagar=cab).count()
                    locked = VencContasPagar.objects.filter(contas_pagar=cab, fechamento__isnull=False).exists()
                except Exception:
                    qtd_venc = 0
                    locked = False
                contas_list.append({
                    'id': cab.id,
                    'placa': cab.placa,
                    'data_fechamento': cab.data_fechamento,
                    'valor': getattr(cab, 'valor', 0.0),
                    'qtd_itens': qtd_itens,
                    'qtd_venc': qtd_venc,
                    'locked': locked,
                })
            # placas disponíveis
            try:
                placas_disponiveis = list(
                    ContasAPagarModel.objects.select_related('placa', 'placa__placa')
                    .values_list('placa__placa__placa', flat=True)
                    .distinct()
                    .order_by('placa__placa__placa')
                )
            except Exception:
                placas_disponiveis = []
        context.update({
            'contas': contas_list,
            'placas_disponiveis': placas_disponiveis,
            'placa_filtro': placa_f,
            'data_inicio': di,
            'data_fim': df,
        })
        return context

class ContasAReceberListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'operacional/contas_a_receber.html'
    permission_required = 'operacional.acessar_operacional'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        di = (self.request.GET.get('data_inicio') or '').strip()
        df = (self.request.GET.get('data_fim') or '').strip()
        placa_f = (self.request.GET.get('placa') or '').strip()
        qs = ContasReceber.objects.select_related('placa', 'placa__placa').all()
        if di:
            qs = qs.filter(data_fechamento__gte=di)
        if df:
            qs = qs.filter(data_fechamento__lte=df)
        if placa_f:
            qs = qs.filter(placa__placa__placa__iexact=placa_f)
        qs = qs.order_by('-data_fechamento')
        contas = []
        for cab in qs:
            try:
                qtd_itens = ItensContasReceber.objects.filter(contas_receber=cab).count()
            except Exception:
                qtd_itens = 0
            try:
                qtd_venc = VencContasReceber.objects.filter(contas_receber=cab).count()
            except Exception:
                qtd_venc = 0
            try:
                locked = VencContasReceber.objects.filter(contas_receber=cab, fechamento__isnull=False).exists()
            except Exception:
                locked = False
            contas.append({
                'id': cab.id,
                'placa': cab.placa,
                'data_fechamento': cab.data_fechamento,
                'valor': cab.valor,
                'qtd_itens': qtd_itens,
                'qtd_venc': qtd_venc,
                'locked': locked,
            })
        # placas com contas a receber
        try:
            placas_disponiveis = list(
                ContasReceber.objects.select_related('placa','placa__placa')
                .values_list('placa__placa__placa', flat=True)
                .distinct()
                .order_by('placa__placa__placa')
            )
        except Exception:
            placas_disponiveis = []
        context.update({
            'contas': contas,
            'placas_disponiveis': placas_disponiveis,
            'placa_filtro': placa_f,
            'data_inicio': di,
            'data_fim': df,
        })
        return context

@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def contas_a_receber_itens(request, cr_id: int):
    try:
        cab = ContasReceber.objects.get(id=cr_id)
    except ContasReceber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Contas a Receber não encontrado.'}, status=404)
    rows = []
    for it in ItensContasReceber.objects.filter(contas_receber=cab).order_by('data', 'nmItem'):
        rows.append({
            'id': it.id,
            'data': it.data.strftime('%d/%m/%Y') if it.data else '',
            'tipo': it.tipo,
            'ordemServico': it.ordemServico,
            'cdItem': it.cdItem,
            'nmItem': it.nmItem,
            'qtde': it.qtde,
            'unidade': it.unidade,
            'valor_unitario': float(it.valor_unitario or 0),
            'percentual': float(it.percentual or 0),
            'valor': float(it.valor or 0),
            'total': float(it.total or 0),
            'periodo': it.periodo,
            'parcela': it.parcela,
            'nmServico': it.nmServico,
            'cdServico': it.cdServico,
        })
    # bloqueio para exclusão do cabeçalho quando houver vencimentos vinculados a fechamento
    can_delete = not VencContasReceber.objects.filter(contas_receber=cab, fechamento__isnull=False).exists()
    return JsonResponse({'success': True, 'rows': rows, 'can_delete': can_delete})

@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def contas_a_receber_vencimentos(request, cr_id: int):
    try:
        cab = ContasReceber.objects.get(id=cr_id)
    except ContasReceber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Contas a Receber não encontrado.'}, status=404)
    rows = []
    for v in VencContasReceber.objects.filter(contas_receber=cab).order_by('data_vencimento', 'seq_vencimento'):
        rows.append({
            'seq': v.seq_vencimento,
            'data': v.data_vencimento.strftime('%d/%m/%Y') if v.data_vencimento else '',
            'fechamento_id': getattr(v, 'fechamento_id', None),
            'valor': float(v.valor or 0),
        })
    return JsonResponse({'success': True, 'rows': rows})

@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def contas_a_receber_excluir(request, cr_id: int):
    """Exclui Contas a Receber, seus itens e vencimentos se não houver vencimento com fechamento vinculado."""
    try:
        cab = ContasReceber.objects.get(id=cr_id)
    except ContasReceber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cabeçalho não encontrado.'}, status=404)
    # Bloqueio por vínculo com fechamento
    if VencContasReceber.objects.filter(contas_receber=cab, fechamento__isnull=False).exists():
        return JsonResponse({'success': False, 'error': 'Não é possível excluir: existem vencimentos vinculados a fechamento.'}, status=400)
    with transaction.atomic():
        VencContasReceber.objects.filter(contas_receber=cab).delete()
        ItensContasReceber.objects.filter(contas_receber=cab).delete()
        cab.delete()
    return JsonResponse({'success': True, 'message': 'Contas a Receber excluído com sucesso.'})

@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def contas_a_receber_excluir_item(request, item_id: int):
    """Exclui um item do Contas a Receber se o cabeçalho não estiver bloqueado por fechamento."""
    try:
        item = ItensContasReceber.objects.select_related('contas_receber').get(id=item_id)
    except ItensContasReceber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item não encontrado.'}, status=404)
    cab = item.contas_receber
    # Bloqueio por vínculo com fechamento
    if VencContasReceber.objects.filter(contas_receber=cab, fechamento__isnull=False).exists():
        return JsonResponse({'success': False, 'error': 'Não é permitido excluir. Já existem vencimentos vinculados a fechamento.'}, status=400)
    try:
        # Excluir item e recalcular total do cabeçalho e vencimentos
        with transaction.atomic():
            item.delete()
            # Recalcular total do cabeçalho a partir dos itens restantes (campo total)
            total_cab = ItensContasReceber.objects.filter(contas_receber=cab).aggregate(s=models.Sum('total'))['s'] or 0.0
            cab.valor = float(total_cab)
            # Atualizar usuário se disponível
            try:
                if request.user and request.user.is_authenticated:
                    cab.atualizado_por = request.user
            except Exception:
                pass
            cab.save(update_fields=['valor', 'atualizado_por', 'dt_atualizacao'] if hasattr(cab, 'atualizado_por') else ['valor', 'dt_atualizacao'])
            # Recalcular vencimentos (mantém fechamento=None)
            try:
                VencContasReceber.objects.filter(contas_receber=cab).delete()
                period_days = {'S': 7, 'Q': 14, 'M': 28}
                by_due_date = {}
                items_qs = ItensContasReceber.objects.filter(contas_receber=cab)
                for it in items_qs:
                    n_parc = int(getattr(it, 'parcela', 1) or 1)
                    per = str(getattr(it, 'periodo', 'S') or 'S').upper()
                    delta = period_days.get(per, 7)
                    valor_item = float(getattr(it, 'total', 0) or 0.0)
                    if n_parc <= 0:
                        n_parc = 1
                    if n_parc == 1:
                        shares = [round(valor_item, 2)]
                    else:
                        base = round(valor_item / n_parc, 2)
                        shares = [base] * (n_parc - 1)
                        last = round(valor_item - sum(shares), 2)
                        shares.append(last)
                    for idx in range(n_parc):
                        due = cab.data_fechamento + timedelta(days=delta * idx)
                        by_due_date[due] = float(by_due_date.get(due, 0.0) + shares[idx])
                seq = 1
                for due_date in sorted(by_due_date.keys()):
                    VencContasReceber.objects.create(
                        contas_receber=cab,
                        fechamento=None,
                        seq_vencimento=seq,
                        data_vencimento=due_date,
                        valor=round(by_due_date[due_date], 2),
                    )
                    seq += 1
            except Exception:
                pass
    except Exception:
        return JsonResponse({'success': False, 'error': 'Falha ao excluir item.'}, status=500)
    # Retornar totais atualizados para a UI
    qtd_itens = ItensContasReceber.objects.filter(contas_receber=cab).count()
    qtd_venc = VencContasReceber.objects.filter(contas_receber=cab).count()
    return JsonResponse({'success': True, 'total_cab': float(getattr(cab, 'valor', 0) or 0.0), 'qtd_itens': qtd_itens, 'qtd_venc': qtd_venc, 'cr_id': cab.id})

class GestaoFechamentoView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'operacional/gestao_fechamento.html'
    permission_required = 'operacional.acessar_operacional'

    def dispatch(self, request, *args, **kwargs):
        try:
            print('GestaoFechamentoView.dispatch', request.method, dict(request.GET))
        except Exception:
            pass
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            print('GestaoFechamentoView.get', dict(request.GET))
        except Exception:
            pass
        return super().get(request, *args, **kwargs)

    print('teste', 100*'-')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        placa_f = (self.request.GET.get('placa') or '').strip()
        agregado_f = (self.request.GET.get('agregado') or '').strip()
        data_str = (self.request.GET.get('data_fechamento') or '').strip()  # yyyy-mm-dd
        # Não carrega dados se não houver data de fechamento

        print('teste', 100*'*')
        rows = []
        if data_str:
            print(data_str)
            dt = None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    dt = datetime.strptime(data_str, fmt).date()
                    break
                except Exception:
                    continue
            if dt:
                # Totais por placa via vencimentos (Receber)
                start_dt = dt
                print(start_dt)
                end_dt = dt + timedelta(days=1)
                print(end_dt)
                recv_qs = VencContasReceber.objects.filter(data_vencimento__gte=start_dt, data_vencimento__lt=end_dt)
                if placa_f:
                    veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa_f).values_list('id_veiculo', flat=True))
                    if veic_ids:
                        recv_qs = recv_qs.filter(contas_receber__placa__in=veic_ids)
                if agregado_f:
                    veic_ids_ag = list(Veiculo.objects.select_related('placa').filter(placa__nm_agregado__icontains=agregado_f).values_list('id_veiculo', flat=True))
                    if veic_ids_ag:
                        recv_qs = recv_qs.filter(contas_receber__placa__in=veic_ids_ag)
                # Agrupar por placa (tentar caminho triplo e, se vazio, caminho duplo)
                recv_by_plate = list(
                    recv_qs
                    .values('contas_receber__placa__placa')
                    .annotate(total=models.Sum('valor'))
                )
                recv_map = {r['contas_receber__placa__placa']: float(r['total'] or 0) for r in recv_by_plate}
                # Fallback por iteração com select_related (robusto para caminhos de FK)
                if not recv_map:
                    recv_map = {}
                    recv_iter = VencContasReceber.objects.select_related('contas_receber', 'contas_receber__placa').filter(data_vencimento__gte=start_dt, data_vencimento__lt=end_dt)
                    for v in recv_iter:
                        try:
                            plate_txt = (getattr(getattr(v.contas_receber, 'placa', None), 'placa', None) or '').strip()
                        except Exception:
                            plate_txt = ''
                        if not plate_txt:
                            continue
                        if placa_f and plate_txt.lower() != placa_f.lower():
                            continue
                        recv_map[plate_txt] = float(recv_map.get(plate_txt, 0.0) + float(v.valor or 0.0))
                # Fallback adicional: somar cabeçalhos CR pela mesma data_fechamento
                cr_hdr = ContasReceber.objects.filter(data_fechamento=dt)
                if placa_f:
                    veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa_f).values_list('id_veiculo', flat=True))
                    if veic_ids:
                        cr_hdr = cr_hdr.filter(placa__in=veic_ids)
                cr_hdr_by_plate = (
                    cr_hdr
                    .values('placa__placa__placa')
                    .annotate(total=models.Sum('valor'))
                )
                for r in cr_hdr_by_plate:
                    key = r['placa__placa__placa']
                    # Usar cabeçalho apenas se não houver vencimentos para a placa (evita dupla contagem)
                    if key not in recv_map or recv_map.get(key, 0.0) == 0.0:
                        recv_map[key] = float(r['total'] or 0)

                # Totais por placa via vencimentos (Pagar)
                pagar_qs = VencContasPagar.objects.filter(data_vencimento__gte=start_dt, data_vencimento__lt=end_dt)
                if placa_f:
                    veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa_f).values_list('id_veiculo', flat=True))
                    if veic_ids:
                        pagar_qs = pagar_qs.filter(contas_pagar__placa__in=veic_ids)
                if agregado_f:
                    veic_ids_ag = list(Veiculo.objects.select_related('placa').filter(placa__nm_agregado__icontains=agregado_f).values_list('id_veiculo', flat=True))
                    if veic_ids_ag:
                        pagar_qs = pagar_qs.filter(contas_pagar__placa__in=veic_ids_ag)
                pagar_by_plate = list(
                    pagar_qs
                    .values('contas_pagar__placa__placa')
                    .annotate(total=models.Sum('valor'))
                )
                pagar_map = {r['contas_pagar__placa__placa']: float(r['total'] or 0) for r in pagar_by_plate}
                # Fallback por iteração com select_related
                if not pagar_map:
                    pagar_map = {}
                    pagar_iter = VencContasPagar.objects.select_related('contas_pagar', 'contas_pagar__placa').filter(data_vencimento__gte=start_dt, data_vencimento__lt=end_dt)
                    for v in pagar_iter:
                        try:
                            plate_txt = (getattr(getattr(v.contas_pagar, 'placa', None), 'placa', None) or '').strip()
                        except Exception:
                            plate_txt = ''
                        if not plate_txt:
                            continue
                        if placa_f and plate_txt.lower() != placa_f.lower():
                            continue
                        pagar_map[plate_txt] = float(pagar_map.get(plate_txt, 0.0) + float(v.valor or 0.0))
                # Fallback adicional: somar cabeçalhos CP pela mesma data_fechamento
                if ContasAPagarModel is not None:
                    cp_hdr = ContasAPagarModel.objects.filter(data_fechamento=dt)
                    if placa_f:
                        veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa_f).values_list('id_veiculo', flat=True))
                        if veic_ids:
                            cp_hdr = cp_hdr.filter(placa__in=veic_ids)
                    cp_hdr_by_plate = (
                        cp_hdr
                        .values('placa__placa__placa')
                        .annotate(total=models.Sum('valor'))
                    )
                    for r in cp_hdr_by_plate:
                        key = r['placa__placa__placa']
                        # Usar cabeçalho apenas se não houver vencimentos para a placa (evita dupla contagem)
                        if key not in pagar_map or pagar_map.get(key, 0.0) == 0.0:
                            pagar_map[key] = float(r['total'] or 0)

                # Lançamentos por placa na data (Receitas somam, Despesas subtraem)
                lanc_qs = Lancamento.objects.select_related('veiculo', 'veiculo__placa').filter(data=dt)
                if placa_f:
                    veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa_f).values_list('id_veiculo', flat=True))
                    if veic_ids:
                        lanc_qs = lanc_qs.filter(veiculo__id_veiculo__in=veic_ids)
                if agregado_f:
                    veic_ids_ag = list(Veiculo.objects.select_related('placa').filter(placa__nm_agregado__icontains=agregado_f).values_list('id_veiculo', flat=True))
                    if veic_ids_ag:
                        lanc_qs = lanc_qs.filter(veiculo__id_veiculo__in=veic_ids_ag)
                lanc_map = {}
                for l in lanc_qs:
                    try:
                        ag = getattr(l.veiculo, 'placa', None)
                        plate_txt = str(ag.placa) if ag and getattr(ag, 'placa', None) else ''
                    except Exception:
                        plate_txt = ''
                    if not plate_txt:
                        continue
                    nat = (getattr(l, 'natureza', '') or '').strip().upper()
                    sign = 1.0 if nat in ('R', 'RECEITA', 'CREDITO', 'CREDIT') else -1.0
                    lanc_map[plate_txt] = float(lanc_map.get(plate_txt, 0.0) + sign * float(getattr(l, 'valor', 0) or 0.0))

                # Conjunto de placas envolvidas
                all_plates = set(recv_map.keys()) | set(pagar_map.keys()) | set(lanc_map.keys())
                if placa_f:
                    all_plates = {p for p in all_plates if str(p).strip().lower() == placa_f.lower()}

                for plate in sorted(all_plates):
                    total_receber = float(recv_map.get(plate, 0.0))
                    total_pagar = float(pagar_map.get(plate, 0.0))
                    total_lanc = float(lanc_map.get(plate, 0.0))
                    # Regra: TOTAL = Contas a Pagar - Contas a Receber + Lançamentos(± por natureza)
                    total_final = total_pagar - total_receber + total_lanc
                    # localizar fechamento (id e cod_ag) para a placa/data
                    fech_id = None
                    cod_ag_val = ''
                    ag_nome_val = ''
                    try:
                        veic_row = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=plate).first()
                        if veic_row:
                            ag_nome_val = str(getattr(getattr(veic_row, 'placa', None), 'nm_agregado', '') or '')
                            if agregado_f and (ag_nome_val or '').lower().find(agregado_f.lower()) == -1:
                                # placa não pertence ao agregado filtrado
                                continue
                            fech_dt_start = datetime.combine(dt, datetime.min.time())
                            fech_dt_end = fech_dt_start + timedelta(days=1)
                            fech = Fechamento.objects.filter(placa=veic_row, data_fechamento__gte=fech_dt_start, data_fechamento__lt=fech_dt_end).first()
                            if fech:
                                fech_id = fech.id
                                cod_ag_val = str(getattr(fech, 'cod_ag', '') or '')
                    except Exception:
                        pass
                    rows.append({
                        'placa': plate,
                        'agregado': ag_nome_val,
                        'total_receber': total_receber,
                        'total_pagar': total_pagar,
                        'lancamentos': total_lanc,
                        'total_final': total_final,
                        'fechamento_id': fech_id,
                        'cod_ag': cod_ag_val,
                    })

        # Placas disponíveis (todas cadastradas)
        try:
            placas_disponiveis = list(
                Veiculo.objects.select_related('placa')
                .values_list('placa__placa', flat=True)
                .distinct()
                .order_by('placa__placa')
            )
        except Exception:
            placas_disponiveis = []
        try:
            agregados_disponiveis = list(
                Veiculo.objects.select_related('placa')
                .values_list('placa__nm_agregado', flat=True)
                .distinct()
                .order_by('placa__nm_agregado')
            )
        except Exception:
            agregados_disponiveis = []

        context.update({
            'placa_filtro': placa_f,
            'agregado_filtro': agregado_f,
            'data_fechamento': (self.request.GET.get('data_fechamento') or '').strip(),
            'placas_disponiveis': placas_disponiveis,
            'agregados_disponiveis': agregados_disponiveis,
            'rows': rows,
            # Agrupar por agregado para exibir hierarquia Agregado -> Placas
            'grupos': (lambda rr: [
                {
                    'agregado': k or 'SEM AGREGADO',
                    'placas': v,
                    'placas_csv': ','.join([str(p.get('placa') or '') for p in v if p.get('placa')]),
                    'all_have_fech': all(bool(p.get('fechamento_id')) for p in v),
                    'all_sent_ag': all(bool((p.get('cod_ag') or '').strip()) for p in v),
                    'totais': {
                        'total_receber': sum(p.get('total_receber', 0.0) for p in v),
                        'total_pagar': sum(p.get('total_pagar', 0.0) for p in v),
                        'lancamentos': sum(p.get('lancamentos', 0.0) for p in v),
                        'total_final': sum(p.get('total_final', 0.0) for p in v),
                    }
                }
                for k, v in (lambda m: m.items())( (lambda m:
                    ( [m.setdefault((p.get('agregado') or '').strip() or 'SEM AGREGADO', []).append(p) for p in rr], m )[1]
                )({}) )
            ])(rows),
        })
        return context

@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def gestao_fechamento_criar(request):
    """
    Cria (ou obtém) um Fechamento para a placa/data e vincula nos vencimentos (CR/CP) e lançamentos desse dia.
    Espera JSON: { placa, data_fechamento (yyyy-mm-dd|dd/mm/yyyy) }
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    placa = (payload.get('placa') or '').strip()
    data_str = (payload.get('data_fechamento') or '').strip()
    if not data_str or not placa:
        return JsonResponse({'success': False, 'error': 'Parâmetros obrigatórios ausentes'}, status=400)
    dt = None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            dt = datetime.strptime(data_str, fmt).date()
            break
        except Exception:
            continue
    if dt is None:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
    # Resolver veículo
    veic = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
    if not veic:
        return JsonResponse({'success': False, 'error': 'Veículo não encontrado'}, status=404)
    start_dt = datetime.combine(dt, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    # Criar/obter Fechamento
    with transaction.atomic():
        fech, created = Fechamento.objects.get_or_create(
            placa=veic,
            data_fechamento=start_dt,
            defaults={
                'cod_ag': None,
                'valor_total': 0.0,
                'usuario': request.user,
            }
        )
        # Vincular Vencimentos CR do dia
        cr_qs = VencContasReceber.objects.select_related('contas_receber').filter(
            data_vencimento__gte=start_dt.date(), data_vencimento__lt=end_dt.date(),
            contas_receber__placa=veic
        )
        VencContasReceber.objects.filter(id__in=list(cr_qs.values_list('id', flat=True))).update(fechamento=fech)
        # Vincular Vencimentos CP do dia
        cp_qs = VencContasPagar.objects.select_related('contas_pagar').filter(
            data_vencimento__gte=start_dt.date(), data_vencimento__lt=end_dt.date(),
            contas_pagar__placa=veic
        )
        VencContasPagar.objects.filter(id__in=list(cp_qs.values_list('id', flat=True))).update(fechamento=fech)
        # Vincular Lançamentos do dia
        Lancamento.objects.filter(veiculo=veic, data=dt).update(fechamento=fech)
    return JsonResponse({'success': True, 'created': created, 'fechamento_id': fech.id})

@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def gestao_fechamento_excluir(request):
    """
    Exclui o Fechamento da placa/data se não possuir cod_ag preenchido.
    Desvincula fechamento de CR/CP/Lançamentos no mesmo dia.
    Espera JSON: { placa, data_fechamento (yyyy-mm-dd|dd/mm/yyyy) }
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    placa = (payload.get('placa') or '').strip()
    data_str = (payload.get('data_fechamento') or '').strip()
    if not data_str or not placa:
        return JsonResponse({'success': False, 'error': 'Parâmetros obrigatórios ausentes'}, status=400)
    dt = None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            dt = datetime.strptime(data_str, fmt).date()
            break
        except Exception:
            continue
    if dt is None:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
    veic = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
    if not veic:
        return JsonResponse({'success': False, 'error': 'Veículo não encontrado'}, status=404)
    start_dt = datetime.combine(dt, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    fech = Fechamento.objects.filter(placa=veic, data_fechamento=start_dt).first()
    if not fech:
        return JsonResponse({'success': False, 'error': 'Fechamento não encontrado'}, status=404)
    if getattr(fech, 'cod_ag', None) and str(fech.cod_ag).strip() != '':
        return JsonResponse({'success': False, 'error': 'Não é permitido excluir: fechamento possui Cod AG.'}, status=400)
    with transaction.atomic():
        # Desvincular vencimentos e lançamentos
        VencContasReceber.objects.filter(
            fechamento=fech
        ).update(fechamento=None)
        VencContasPagar.objects.filter(
            fechamento=fech
        ).update(fechamento=None)
        Lancamento.objects.filter(
            fechamento=fech
        ).update(fechamento=None)
        # Excluir o fechamento
        fech.delete()
    return JsonResponse({'success': True})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def gestao_fechamento_enviar_ag(request):
    """
    Marca um Fechamento como enviado para o AG preenchendo o campo cod_ag.
    Espera JSON: { fechamento_id } ou { placa, data_fechamento }
    Regras:
      - Não sobrescreve cod_ag se já estiver preenchido
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        payload = {}
    fech_id = payload.get('fechamento_id')
    cab = None
    if fech_id:
        try:
            cab = Fechamento.objects.get(id=int(fech_id))
        except Exception:
            cab = None
    if cab is None:
        placa = (payload.get('placa') or '').strip()
        data_str = (payload.get('data_fechamento') or '').strip()
        if not placa or not data_str:
            return JsonResponse({'success': False, 'error': 'Parâmetros inválidos'}, status=400)
        dt = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dt = datetime.strptime(data_str, fmt)
                break
            except Exception:
                continue
        if dt is None:
            return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
        veic = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
        if not veic:
            return JsonResponse({'success': False, 'error': 'Veículo não encontrado'}, status=404)
        cab = Fechamento.objects.filter(placa=veic, data_fechamento=dt).first()
        if not cab:
            return JsonResponse({'success': False, 'error': 'Fechamento não encontrado'}, status=404)
    # Se já enviado, não sobrescrever
    if getattr(cab, 'cod_ag', None) and str(cab.cod_ag).strip() != '':
        return JsonResponse({'success': False, 'error': 'Fechamento já enviado para o AG.'}, status=400)
    # Gerar um código simples de AG
    ag_code = f'AG-{cab.id}'
    try:
        cab.cod_ag = ag_code
        cab.save(update_fields=['cod_ag'])
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Falha ao marcar envio: {e}'}, status=500)
    return JsonResponse({'success': True, 'cod_ag': ag_code})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def gestao_fechamento_enviar_ag_grupo(request):
    """
    Marca um conjunto de Fechamentos (todas as placas do mesmo agregado) como enviados para o AG
    gerando/aplicando o MESMO código para todas.
    Espera JSON: { placas: [str], data_fechamento }
    Regras:
      - Se algum fechamento já possuir cod_ag e os demais não, todos recebem esse mesmo código.
      - Se existirem códigos diferentes entre as placas, retorna erro (não sobrescreve).
      - Se nenhum tiver código, gera 'AG-{slug_agregado}-{yyyymmdd}' e aplica para todos.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    placas = payload.get('placas') or []
    data_str = (payload.get('data_fechamento') or '').strip()
    if not placas or not data_str:
        return JsonResponse({'success': False, 'error': 'Parâmetros inválidos'}, status=400)
    # Parse data
    dt = None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            dt = datetime.strptime(data_str, fmt)
            break
        except Exception:
            continue
    if dt is None:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
    start_dt = dt if isinstance(dt, datetime) else datetime.combine(dt, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    fechamentos = []
    agregados = set()
    for placa in placas:
        veic = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=str(placa).strip()).first()
        if not veic:
            return JsonResponse({'success': False, 'error': f'Veículo não encontrado: {placa}'}, status=404)
        agregados.add((getattr(getattr(veic, 'placa', None), 'nm_agregado', '') or '').strip())
        cab = Fechamento.objects.filter(placa=veic, data_fechamento__gte=start_dt, data_fechamento__lt=end_dt).first()
        if not cab:
            return JsonResponse({'success': False, 'error': f'Fechamento não encontrado para {placa} em {data_str}'}, status=404)
        fechamentos.append(cab)
    # Verificar códigos existentes
    existing_codes = { (str(getattr(f, 'cod_ag', '') or '').strip() or None) for f in fechamentos }
    existing_codes.discard(None)
    if len(existing_codes) > 1:
        return JsonResponse({'success': False, 'error': 'Existem placas com códigos AG diferentes. Ajuste antes de enviar em grupo.'}, status=400)
    # Determinar o código
    if existing_codes:
        group_code = existing_codes.pop()
    else:
        # gerar um código padronizado por agregado e data respeitando o tamanho do campo cod_ag (20)
        ag_nome = (list(agregados)[0] if agregados else '').strip() or 'AGREGADO'
        # sanitizar
        import re, unicodedata
        ag_slug = unicodedata.normalize('NFD', ag_nome)
        ag_slug = ''.join(ch for ch in ag_slug if unicodedata.category(ch) != 'Mn')
        ag_slug = re.sub(r'[^A-Za-z0-9\-]+', '-', ag_slug).strip('-').upper()
        ymd = start_dt.strftime("%Y%m%d")
        max_len = 20
        # tentativa 1: AG-{slug}-{YYYYMMDD}
        candidate = f'AG-{ag_slug}-{ymd}'
        if len(candidate) > max_len:
            # truncar o slug para caber
            reserved = len('AG-') + 1 + len(ymd)  # prefix + '-' + date
            allow = max_len - reserved
            if allow < 1:
                allow = 1
            candidate = f'AG-{ag_slug[:allow]}-{ymd}'
        if len(candidate) > max_len:
            # fallback final estável e curto
            candidate = f'AG-{ymd}'
        group_code = candidate
    # Aplicar código a todos sem cod_ag
    try:
        with transaction.atomic():
            for f in fechamentos:
                cur = (str(getattr(f, 'cod_ag', '') or '').strip() or None)
                if cur and cur != group_code:
                    return JsonResponse({'success': False, 'error': f'Placa {f.placa.placa.placa} já possui código AG diferente ({cur}).'}, status=400)
                if not cur:
                    f.cod_ag = group_code
                    f.save(update_fields=['cod_ag'])
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Falha ao marcar envio em grupo: {e}'}, status=500)
    return JsonResponse({'success': True, 'cod_ag': group_code})
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def gestao_fechamento_detalhes(request):
    """
    Retorna detalhes (JSON) de um fechamento por placa e data:
    - vencimentos de Contas a Receber
    - vencimentos de Contas a Pagar
    - lançamentos
    - itens (Contas a Receber e Contas a Pagar)
    Parâmetros: placa, data_fechamento (yyyy-mm-dd ou dd/mm/yyyy)
    """
    placa = (request.GET.get('placa') or '').strip()
    data_str = (request.GET.get('data_fechamento') or '').strip()
    if not data_str:
        return JsonResponse({'success': False, 'error': 'Parâmetros inválidos'}, status=400)
    dt = None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            dt = datetime.strptime(data_str, fmt).date()
            break
        except Exception:
            continue
    if dt is None:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
    start_dt = dt
    end_dt = dt + timedelta(days=1)
    # Contas a Receber - vencimentos
    # Regra: considerar a data de fechamento do cabeçalho (contas_receber.data_fechamento),
    # e não a data de vencimento individual
    cr_qs = VencContasReceber.objects.select_related('contas_receber', 'contas_receber__placa').filter(contas_receber__data_fechamento=dt)
    if placa:
        veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).values_list('id_veiculo', flat=True))
        if veic_ids:
            cr_qs = cr_qs.filter(contas_receber__placa__in=veic_ids)
    cr_rows = []
    for v in cr_qs:
        try:
            placa_txt = ''
            if getattr(v, 'contas_receber', None) and getattr(v.contas_receber, 'placa', None):
                # v.contas_receber.placa -> Veiculo; Veiculo.placa -> Agregado; Agregado.placa -> str
                ag = getattr(v.contas_receber.placa, 'placa', None)
                placa_txt = str(ag) if isinstance(ag, str) else (getattr(ag, 'placa', '') if ag else '')
        except Exception:
            placa_txt = ''
        try:
            cr_id = getattr(v.contas_receber, 'id', None)
        except Exception:
            cr_id = None
        cr_rows.append({
            'seq': v.seq_vencimento,
            'data': v.data_vencimento.strftime('%d/%m/%Y') if v.data_vencimento else '',
            'fechamento': (getattr(v.contas_receber, 'data_fechamento', None).strftime('%d/%m/%Y') if getattr(v.contas_receber, 'data_fechamento', None) else ''),
            'cr_id': cr_id,
            'valor': float(v.valor or 0),
            'placa': placa_txt,
        })
    # Contas a Pagar - vencimentos
    # Regra: considerar a data de fechamento do cabeçalho (contas_pagar.data_fechamento),
    # e não a data de vencimento individual
    cp_qs = VencContasPagar.objects.select_related('contas_pagar', 'contas_pagar__placa').filter(contas_pagar__data_fechamento=dt)
    if placa:
        veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).values_list('id_veiculo', flat=True))
        if veic_ids:
            cp_qs = cp_qs.filter(contas_pagar__placa__in=veic_ids)
    cp_rows = []
    for v in cp_qs:
        try:
            placa_txt = ''
            if getattr(v, 'contas_pagar', None) and getattr(v.contas_pagar, 'placa', None):
                ag = getattr(v.contas_pagar.placa, 'placa', None)
                placa_txt = str(ag) if isinstance(ag, str) else (getattr(ag, 'placa', '') if ag else '')
        except Exception:
            placa_txt = ''
        try:
            cp_id = getattr(v.contas_pagar, 'id', None)
        except Exception:
            cp_id = None
        cp_rows.append({
            'seq': v.seq_vencimento,
            'data': v.data_vencimento.strftime('%d/%m/%Y') if v.data_vencimento else '',
            'fechamento': (getattr(v.contas_pagar, 'data_fechamento', None).strftime('%d/%m/%Y') if getattr(v.contas_pagar, 'data_fechamento', None) else ''),
            'cp_id': cp_id,
            'valor': float(v.valor or 0),
            'placa': placa_txt,
        })
    # Lançamentos
    lanc_qs = Lancamento.objects.select_related('veiculo', 'veiculo__placa').filter(data=dt)
    if placa:
        veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).values_list('id_veiculo', flat=True))
        if veic_ids:
            lanc_qs = lanc_qs.filter(veiculo__id_veiculo__in=veic_ids)
    lanc_rows = []
    for l in lanc_qs:
        try:
            placa_txt = ''
            if getattr(l, 'veiculo', None) and getattr(l.veiculo, 'placa', None):
                ag = getattr(l.veiculo.placa, 'placa', None)
                placa_txt = str(ag) if isinstance(ag, str) else (getattr(ag, 'placa', '') if ag else '')
        except Exception:
            placa_txt = ''
        lanc_rows.append({
            'data': l.data.strftime('%d/%m/%Y') if l.data else '',
            'categoria': getattr(l.categoria, 'nome', ''),
            'valor': float(l.valor or 0),
            'placa': placa_txt,
            'obs': l.obs or '',
            'periodo': getattr(l, 'periodo', '') or '',
            'parcela': getattr(l, 'parcela', 1) or 1,
        })
    # Itens de Contas a Receber/Contas a Pagar
    cr_itens_rows = []
    cp_itens_rows = []
    # localizar veiculos por placa (quando fornecida)
    veic_ids = None
    if placa:
        veic_ids = list(Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).values_list('id_veiculo', flat=True))
        if not veic_ids:
            veic_ids = []
    # Cabeçalhos CR na data
    cr_cabs = ContasReceber.objects.filter(data_fechamento=dt)
    if veic_ids is not None:
        cr_cabs = cr_cabs.filter(placa__id_veiculo__in=veic_ids)
    cr_cabs_ids = list(cr_cabs.values_list('id', flat=True))
    if cr_cabs_ids:
        for it in ItensContasReceber.objects.select_related().filter(contas_receber_id__in=cr_cabs_ids).order_by('data', 'ordemServico'):
            cr_itens_rows.append({
                'os': it.ordemServico,
                'servico': it.nmServico,
                'data': it.data.strftime('%d/%m/%Y') if it.data else '',
                'tipo': it.tipo or '',
                'item': it.nmItem,
                'qtde': float(it.qtde or 0),
                'un': it.unidade or '',
                'valor_unit': float(it.valor_unitario or 0),
                'percentual': float(it.percentual or 0),
                'valor': float(it.valor or 0),
                'total': float(it.total or 0),
                'periodo': getattr(it, 'periodo', '') or '',
                'parcela': getattr(it, 'parcela', 1) or 1,
            })
    # Cabeçalhos CP na data
    cp_cabs = ContasAPagarModel.objects.filter(data_fechamento=dt)
    if veic_ids is not None:
        cp_cabs = cp_cabs.filter(placa__id_veiculo__in=veic_ids)
    cp_cabs_ids = list(cp_cabs.values_list('id', flat=True))
    if cp_cabs_ids:
        for it in ItensContasPagar.objects.select_related().filter(contas_pagar_id__in=cp_cabs_ids).order_by('data', 'codigo'):
            cp_itens_rows.append({
                'empresa': it.empresa or '',
                'codigo': it.codigo or '',
                'placa': it.placa or '',
                'data': it.data.strftime('%d/%m/%Y') if it.data else '',
                'act': it.act or '',
                'status': it.status or '',
                'trecho': it.trecho or '',
                'valor': float(it.valor or 0),
                'adiantamento': float(it.adiantamento or 0),
                'outros': float(it.outros or 0),
                'saldo': float(it.saldo or 0),
                'periodo': it.periodo or '',
                'parcela': it.parcela or 1,
            })
    return JsonResponse({
        'success': True,
        'cr_venc': cr_rows,
        'cp_venc': cp_rows,
        'lanc': lanc_rows,
        'cr_itens': cr_itens_rows,
        'cp_itens': cp_itens_rows,
    })

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def gestao_fechamento_listar_placas(request):
    """
    Lista placas com Fechamento gerado na data informada (yyyy-mm-dd).
    Retorna placa, nome do agregado e id do fechamento.
    """
    data_str = (request.GET.get('data_fechamento') or '').strip()
    if not data_str:
        return JsonResponse({'success': False, 'error': 'Informe data_fechamento'}, status=400)
    try:
        dt = datetime.strptime(data_str, '%Y-%m-%d').date()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
    start_dt = datetime.combine(dt, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    rows = []
    qs = (Fechamento.objects
          .select_related('placa', 'placa__placa')
          .filter(
              data_fechamento__gte=start_dt,
              data_fechamento__lt=end_dt,
              # Somente fechamentos já enviados para o AG
              cod_ag__isnull=False
          )
          .exclude(cod_ag__exact=''))
    seen = set()
    for f in qs:
        try:
            placa_txt = f.placa.placa.placa  # Agregado.placa
            ag_nome = f.placa.placa.nm_agregado
        except Exception:
            placa_txt = ''
            ag_nome = ''
        key = (placa_txt or '', ag_nome or '')
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            'fechamento_id': getattr(f, 'id', None),
            'placa': placa_txt,
            'agregado': ag_nome,
        })
    return JsonResponse({'success': True, 'rows': rows})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def contas_a_pagar_itens(request, cap_id: int):
    # retornar itens no formato simples
    try:
        cab = ContasAPagarModel.objects.get(id=cap_id)
    except ContasAPagarModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cabeçalho não encontrado.'}, status=404)
    # identificar fk
    fk_field_name = None
    for f in ItensContasAPagarModel._meta.get_fields():
        try:
            if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:
                fk_field_name = f.name
                break
        except Exception:
            continue
    rows = []
    # pode deletar? somente se não houver vencimentos vinculados a fechamento
    can_delete = not VencContasPagar.objects.filter(contas_pagar=cab, fechamento__isnull=False).exists()
    if fk_field_name:
        for it in ItensContasAPagarModel.objects.filter(**{fk_field_name: cab}).order_by('data', 'codigo'):
            rows.append({
                'id': it.id,
                'empresa': it.empresa,
                'codigo': it.codigo,
                'placa': it.placa,
                'data': it.data.strftime('%d/%m/%Y') if it.data else '',
                'act': it.act or '',
                'status': it.status or '',
                'trecho': it.trecho or '',
                'valor': f'{float(it.valor or 0):.2f}',
                'adiantamento': f'{float(it.adiantamento or 0):.2f}',
                'outros': f'{float(it.outros or 0):.2f}',
                'saldo': f'{float(it.saldo or 0):.2f}',
                'periodo': it.periodo or '',
                'parcela': it.parcela or 1,
            })
    return JsonResponse({'success': True, 'rows': rows, 'can_delete': can_delete})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def contas_a_pagar_vencimentos(request, cap_id: int):
    try:
        cab = ContasAPagarModel.objects.get(id=cap_id)
    except ContasAPagarModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cabeçalho não encontrado.'}, status=404)
    rows = []
    for v in VencContasPagar.objects.filter(contas_pagar=cab).order_by('data_vencimento', 'seq_vencimento'):
        rows.append({
            'seq': v.seq_vencimento,
            'data': v.data_vencimento.strftime('%d/%m/%Y') if v.data_vencimento else '',
            'fechamento_id': getattr(v, 'fechamento_id', None),
            'valor': float(v.valor or 0),
        })
    return JsonResponse({'success': True, 'rows': rows})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def contas_a_pagar_excluir(request, cap_id: int):
    """Exclui o Contas a Pagar, seus itens e vencimentos se não houver vencimento com fechamento vinculado."""
    try:
        cab = ContasAPagarModel.objects.get(id=cap_id)
    except ContasAPagarModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cabeçalho não encontrado.'}, status=404)
    # Bloqueio por vínculo com fechamento
    if VencContasPagar.objects.filter(contas_pagar=cab, fechamento__isnull=False).exists():
        return JsonResponse({'success': False, 'error': 'Não é possível excluir: existem vencimentos vinculados a fechamento.'}, status=400)
    # Excluir em transação
    with transaction.atomic():
        # apagar vencimentos explicitamente (por clareza), itens e depois o cabeçalho (FKs são CASCADE)
        VencContasPagar.objects.filter(contas_pagar=cab).delete()
        # identificar nome do fk nos itens
        fk_field_name = None
        for f in ItensContasAPagarModel._meta.get_fields():
            try:
                if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:  # fallback name
                    fk_field_name = f.name
                    break
                if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:
                    fk_field_name = f.name
                    break
            except Exception:
                continue
        if fk_field_name:
            ItensContasAPagarModel.objects.filter(**{fk_field_name: cab}).delete()
        cab.delete()
    return JsonResponse({'success': True, 'message': 'Contas a Pagar excluído com sucesso.'})
@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def contas_a_pagar_check(request):
    """Verifica se já existe Contas a Pagar para a placa/data e retorna flags de valor fixo."""
    placa = (request.GET.get('placa') or '').strip()
    data_str = (request.GET.get('data_fechamento') or '').strip()  # yyyy-mm-dd
    if not placa or not data_str:
        return JsonResponse({'success': False, 'error': 'Parâmetros inválidos'}, status=400)
    try:
        dt = datetime.strptime(data_str, '%Y-%m-%d').date()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)
    veic = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
    if not veic:
        return JsonResponse({'success': True, 'exists': False})
    cab = ContasAPagarModel.objects.filter(placa=veic, data_fechamento=dt).first()
    if not cab:
        return JsonResponse({'success': True, 'exists': False})
    locked = VencContasPagar.objects.filter(contas_pagar=cab, fechamento__isnull=False).exists()
    # Interpretar fl_vlfixo como 'S'/'N' -> booleano
    flfix = False
    try:
        raw = getattr(cab, 'fl_vlfixo', '')
        flfix = str(raw).strip().upper() in ('S', 'Y', '1', 'TRUE')
    except Exception:
        flfix = False
    # valor_fixo pode ser None
    try:
        vfix = float(getattr(cab, 'valor_fixo', 0) or 0)
    except Exception:
        vfix = 0.0
    resp = {
        'success': True,
        'exists': True,
        'locked': locked,
        'valor': float(getattr(cab, 'valor', 0) or 0),
        'fl_vlfixo': flfix,
        'valor_fixo': vfix,
    }
    return JsonResponse(resp)

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def contas_a_pagar_excluir_item(request, item_id: int):
    # localizar item e cabeçalho
    try:
        it = ItensContasAPagarModel.objects.select_related().get(id=item_id)
    except ItensContasAPagarModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item não encontrado.'}, status=404)
    # descobrir FK do cabeçalho
    cab = None
    for f in ItensContasAPagarModel._meta.get_fields():
        try:
            if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:
                cab = getattr(it, f.name)
                break
        except Exception:
            continue
    if cab is None:
        return JsonResponse({'success': False, 'error': 'Cabeçalho não associado.'}, status=400)
    # bloquear se houver vencimentos com fechamento
    if VencContasPagar.objects.filter(contas_pagar=cab, fechamento__isnull=False).exists():
        return JsonResponse({'success': False, 'error': 'Não é permitido excluir. Já existem vencimentos vinculados a fechamento.'}, status=400)
    # excluir item, recalcular header e vencimentos
    with transaction.atomic():
        it.delete()
        # atualizar total do cabeçalho
        # identificar nome do fk novamente
        fk_field_name = None
        for f in ItensContasAPagarModel._meta.get_fields():
            try:
                if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:
                    fk_field_name = f.name
                    break
            except Exception:
                continue
        total_new = 0.0
        items_qs = ItensContasAPagarModel.objects.filter(**({fk_field_name: cab} if fk_field_name else {}))
        # Se não houver mais itens, excluir cabeçalho e seus vencimentos
        remaining = 0
        try:
            remaining = items_qs.count()
        except Exception:
            remaining = 0
        if remaining == 0:
            # remover vencimentos e o próprio cabeçalho
            try:
                VencContasPagar.objects.filter(contas_pagar=cab).delete()
            except Exception:
                pass
            cap_id = cab.id
            cab.delete()
            return JsonResponse({
                'success': True,
                'message': 'Item excluído e cabeçalho removido (sem itens restantes).',
                'cap_id': cap_id,
                'deleted_header': True,
                'total_cab': 0.0,
                'qtd_itens': 0,
                'qtd_venc': 0,
            })
        for it2 in items_qs:
            try:
                total_new += float(getattr(it2, 'saldo', 0) or 0)
            except Exception:
                continue
        cab.valor = total_new
        cab.atualizado_por = request.user
        cab.save(update_fields=['valor', 'atualizado_por', 'dt_atualizacao'])
        # recalcular vencimentos
        VencContasPagar.objects.filter(contas_pagar=cab).delete()
        period_days = {'S': 7, 'Q': 14, 'M': 28}
        by_due_date = {}
        for it2 in items_qs:
            n_parc = int(getattr(it2, 'parcela', 1) or 1)
            per = str(getattr(it2, 'periodo', 'S') or 'S').upper()
            delta = period_days.get(per, 7)
            saldo_item = float(getattr(it2, 'saldo', 0) or 0.0)
            if n_parc <= 0:
                n_parc = 1
            if n_parc == 1:
                shares = [round(saldo_item, 2)]
            else:
                base = round(saldo_item / n_parc, 2)
                shares = [base] * (n_parc - 1)
                last = round(saldo_item - sum(shares), 2)
                shares.append(last)
            for idx in range(n_parc):
                due = cab.data_fechamento + timedelta(days=delta * idx)
                by_due_date[due] = float(by_due_date.get(due, 0.0) + shares[idx])
        seq = 1
        for due_date in sorted(by_due_date.keys()):
            VencContasPagar.objects.create(
                contas_pagar=cab,
                fechamento=None,
                seq_vencimento=seq,
                data_vencimento=due_date,
                valor=round(by_due_date[due_date], 2),
            )
            seq += 1
    # preparar retorno com totais atualizados para atualização imediata da UI
    qtd_itens = 0
    try:
        qtd_itens = items_qs.count()
    except Exception:
        pass
    qtd_venc = VencContasPagar.objects.filter(contas_pagar=cab).count()
    return JsonResponse({
        'success': True,
        'message': 'Item excluído com sucesso.',
        'cap_id': cab.id,
        'total_cab': float(getattr(cab, 'valor', 0) or 0.0),
        'qtd_itens': qtd_itens,
        'qtd_venc': qtd_venc,
        'deleted_header': False,
    })


class CartaFreteListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'operacional/carta_frete.html'
    permission_required = 'operacional.acessar_operacional'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        placa = (self.request.GET.get('placa') or '').strip()
        status_f = (self.request.GET.get('status') or '').strip()
        di = (self.request.GET.get('data_inicio') or '').strip()
        df = (self.request.GET.get('data_fim') or '').strip()

        # Bloqueia consulta completa sem período: exige data início e fim
        if not di or not df:
            messages.info(self.request, 'Informe Data Início e Data Fim para consultar a Carta Frete.')
            context.update({
                'rows': [],
                'rows_values': [],
                'cols': [],
                'grupos': [],
                'placa_filtro': placa,
                'status_filtro': status_f,
                'data_inicio': di,
                'data_fim': df,
                'total_valor': 0.0,
                'total_adiantamento': 0.0,
                'total_outros': 0.0,
                'total_saldo': 0.0,
            })
            return context

        rows = []
        cols = []
        rows_values = []
        grupos = []
        total_valor = total_adiant = total_outros = total_saldo = 0.0

        try:
            where = []
            params = []
            if placa:
                where.append('PLACA = %s')
                params.append(placa)
            if di:
                where.append('CAST(DATA AS DATE) >= %s')
                params.append(di)
            if df:
                where.append('CAST(DATA AS DATE) <= %s')
                params.append(df)
            # Não filtramos por STATUS aqui, pois o filtro desejado é pela coluna de situação (aberto/fechado),
            # que pode ter nomes variados na view. Faremos o filtro após ler as colunas.

            sql = ["SELECT * FROM VW_CARTA_FRETE"]
            if where:
                sql.append('WHERE ' + ' AND '.join(where))
            sql.append('ORDER BY DATA ASC')
            with connection.cursor() as cursor:
                cursor.execute('\n'.join(sql), params)
                cols = [c[0] for c in cursor.description]
                for r in cursor.fetchall():
                    d = dict(zip(cols, r))
                    rows.append(d)

            # localizar nomes das colunas
            def pick_col(target_names):
                lower_map = {c.lower(): c for c in cols}
                for name in target_names:
                    if name in lower_map:
                        return lower_map[name]
                for c in cols:
                    cl = c.lower()
                    for name in target_names:
                        if name in cl:
                            return c
                return None

            col_valor = pick_col(['valor', 'vl', 'vl_total'])
            col_adiant = pick_col(['adiantamento', 'adiant', 'vl_adiantamento'])
            col_outros = pick_col(['outros', 'vl_outros'])
            col_saldo = pick_col(['saldo', 'vl_saldo'])
            col_placa = pick_col(['placa', 'nrplaca', 'placa_principal'])
            col_situacao = pick_col(['situacao', 'situação'])

            # Aplicar filtro por situacao (aberto/fechado) se solicitado
            if status_f and col_situacao:
                wanted = (status_f or '').strip().upper()
                rows = [d for d in rows if str(d.get(col_situacao) or '').strip().upper() == wanted]

            by_placa = {}
            for d in rows:
                if col_valor: total_valor += float(d.get(col_valor) or 0)
                if col_adiant: total_adiant += float(d.get(col_adiant) or 0)
                if col_outros: total_outros += float(d.get(col_outros) or 0)
                if col_saldo: total_saldo += float(d.get(col_saldo) or 0)
                # agrupar por placa
                placa_key = str(d.get(col_placa) or '').strip() if col_placa else '—'
                g = by_placa.get(placa_key) or {'placa': placa_key, 'qtd': 0, 'valor': 0.0, 'adiantamento': 0.0, 'outros': 0.0, 'saldo': 0.0, 'has_open': False, 'has_closed': False}
                g['qtd'] += 1
                if col_valor: g['valor'] += float(d.get(col_valor) or 0)
                if col_adiant: g['adiantamento'] += float(d.get(col_adiant) or 0)
                if col_outros: g['outros'] += float(d.get(col_outros) or 0)
                if col_saldo: g['saldo'] += float(d.get(col_saldo) or 0)
                # status por linha, se houver coluna de situação
                if col_situacao:
                    sit_val = str(d.get(col_situacao) or '').strip()
                    sit_norm = sit_val.upper()
                    sit_norm_ascii = (
                        sit_val
                        .encode('ascii', 'ignore')
                        .decode('ascii')
                        .upper()
                    )
                    is_closed = (
                        ('FECH' in sit_norm) or ('FECH' in sit_norm_ascii) or
                        ('ENCERR' in sit_norm_ascii) or ('CLOS' in sit_norm) or
                        sit_norm in ('FECHADO', 'F', 'CLOSED', 'C', '1', 'TRUE')
                    )
                    is_open = (
                        ('ABER' in sit_norm) or ('OPEN' in sit_norm) or
                        sit_norm in ('ABERTO', 'A', 'OPEN', 'O', '0', 'FALSE')
                    )
                    if is_closed:
                        g['has_closed'] = True
                    if is_open:
                        g['has_open'] = True
                by_placa[placa_key] = g
            # construir matriz de valores na mesma ordem de cols para o template
            rows_values = [[(row.get(c) if row.get(c) is not None else '') for c in cols] for row in rows]
            grupos = []
            for v in by_placa.values():
                status_txt = ''
                if v.get('has_open'):
                    status_txt = 'ABERTO'
                elif v.get('has_closed'):
                    status_txt = 'FECHADO'
                grupos.append({
                    'placa': v['placa'],
                    'qtd': v['qtd'],
                    'valor': v['valor'],
                    'adiantamento': v['adiantamento'],
                    'outros': v['outros'],
                    'saldo': v['saldo'],
                    'status': status_txt,
                })
            grupos = sorted(grupos, key=lambda x: x['placa'])

        except Exception as e:
            messages.error(self.request, f'Erro ao carregar Carta Frete: {e}')

        context.update({
            'rows': rows,
            'rows_values': rows_values,
            'cols': cols,
            'grupos': grupos,
            'placa_filtro': placa,
            'status_filtro': status_f,
            'data_inicio': di,
            'data_fim': df,
            'total_valor': total_valor,
            'total_adiantamento': total_adiant,
            'total_outros': total_outros,
            'total_saldo': total_saldo,
        })
        return context

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def get_fechamento_itens(request, fechamento_id: int):
    try:
        cab = Fechamento.objects.get(id=fechamento_id)
    except Fechamento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fechamento não encontrado'}, status=404)
    itens = ItensFechamento.objects.filter(fechamento=cab).order_by('tipo', 'nmItem')
    data = []
    for it in itens:
        data.append({
            'id': it.id,
            'data': it.data.strftime('%d/%m/%Y') if it.data else '',
            'ordem_servico': it.ordemServico,
            'tipo': it.tipo,
            'nm_servico': it.nmServico,
            'cd_item': it.cdItem,
            'nm_item': it.nmItem,
            'qtde': it.qtde,
            'valor_unitario': it.valor_unitario,
            'percentual': it.percentual,
            'valor': it.valor,
            'total': it.total,
            'periodo': it.periodo,
            'parcela': it.parcela,
            'cod_ag': cab.cod_ag,
            'data_fechamento': cab.data_fechamento.strftime('%Y-%m-%d') if cab.data_fechamento else '',
        })
    return JsonResponse({'success': True, 'itens': data})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def excluir_item_fechamento(request, item_id: int):
    try:
        item = ItensFechamento.objects.select_related('fechamento').get(id=item_id)
    except ItensFechamento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item não encontrado'}, status=404)
    cab = item.fechamento
    if getattr(cab, 'cod_ag', None) and str(cab.cod_ag).strip() != '':
        return JsonResponse({'success': False, 'error': 'O item não pode ser excluído: já lançado no AG.'}, status=403)
    with transaction.atomic():
        total_item = float(item.total or 0)
        item.delete()
        # Atualiza total do cabeçalho
        novo_total = (float(cab.valor_total or 0) - total_item)
        cab.valor_total = novo_total if novo_total > 0 else 0.0
        cab.save(update_fields=['valor_total'])
    return JsonResponse({'success': True, 'message': 'Item excluído com sucesso.', 'novo_total': float(cab.valor_total or 0)})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def atualizar_item_fechamento(request, item_id: int):
    """Atualiza período e parcelas de um item do fechamento."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
        periodo = (payload.get('periodo') or '').strip()
        parcela = int(payload.get('parcela') or 1)
        item = ItensFechamento.objects.select_related('fechamento').get(id=item_id)
        cab = item.fechamento
        if getattr(cab, 'cod_ag', None) and str(cab.cod_ag).strip() != '':
            return JsonResponse({'success': False, 'error': 'Item bloqueado: fechamento já possui Cod AG.'}, status=403)
        item.periodo = periodo or item.periodo
        item.parcela = parcela
        item.save(update_fields=['periodo', 'parcela'])
        return JsonResponse({'success': True, 'message': 'Item atualizado com sucesso.'})
    except ItensFechamento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro ao atualizar item: {str(e)}'}, status=500)

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def mover_item_fechamento(request, item_id: int):
    """Move um item para outra data de fechamento. Se não existir cabeçalho para a placa/data, cria um novo.
    Espera JSON: { data_fechamento: 'dd/mm/yyyy' }
    Bloqueia se o fechamento de origem tiver Cod AG preenchido.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        nova_data_str = (payload.get('data_fechamento') or '').strip()
        if not nova_data_str:
            return JsonResponse({'success': False, 'error': 'Data não informada'}, status=400)
        try:
            nova_dt = datetime.strptime(nova_data_str, '%d/%m/%Y')
        except Exception:
            try:
                nova_dt = datetime.strptime(nova_data_str, '%Y-%m-%d')
            except Exception:
                return JsonResponse({'success': False, 'error': 'Formato de data inválido'}, status=400)

        item = ItensFechamento.objects.select_related('fechamento', 'fechamento__placa', 'fechamento__placa__placa').get(id=item_id)
        cab_origem = item.fechamento
        # Bloqueio por Cod AG
        if getattr(cab_origem, 'cod_ag', None) and str(cab_origem.cod_ag).strip() != '':
            return JsonResponse({'success': False, 'error': 'Item não pode ser movido: fechamento original já possui Cod AG.'}, status=403)

        # Encontrar ou criar cabeçalho destino para mesma placa na nova data
        with transaction.atomic():
            cab_dest = Fechamento.objects.select_for_update().filter(
                placa=cab_origem.placa,
                data_fechamento__date=nova_dt.date(),
            ).first()
            if not cab_dest:
                cab_dest = Fechamento.objects.create(
                    placa=cab_origem.placa,
                    data_fechamento=nova_dt,
                    cod_ag=None,
                    valor_total=0.0,
                    usuario=request.user,
                )

            # Atualizar totais de origem e destino
            valor_item = float(item.total or 0)
            # move item
            item.fechamento = cab_dest
            item.save(update_fields=['fechamento'])

            # recalcula total dos dois cabeçalhos
            total_origem = ItensFechamento.objects.filter(fechamento=cab_origem).aggregate(s=models.Sum('total'))['s'] or 0.0
            cab_origem.valor_total = float(total_origem)
            cab_origem.save(update_fields=['valor_total'])

            total_dest = ItensFechamento.objects.filter(fechamento=cab_dest).aggregate(s=models.Sum('total'))['s'] or 0.0
            cab_dest.valor_total = float(total_dest)
            cab_dest.save(update_fields=['valor_total'])

        return JsonResponse({'success': True, 'message': 'Item movido com sucesso.'})
    except ItensFechamento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro ao mover item: {str(e)}'}, status=500)

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def excluir_fechamento(request, fechamento_id: int):
    try:
        cab = Fechamento.objects.get(id=fechamento_id)
    except Fechamento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fechamento não encontrado'}, status=404)
    # Bloqueia exclusão se já possuir cod_ag preenchido
    if getattr(cab, 'cod_ag', None) and str(cab.cod_ag).strip() != '':
        return JsonResponse({'success': False, 'error': 'Fechamento bloqueado: já possui Cod AG.'}, status=403)
    with transaction.atomic():
        ItensFechamento.objects.filter(fechamento=cab).delete()
        cab.delete()
    return JsonResponse({'success': True, 'message': 'Fechamento excluído com sucesso.'})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def alterar_data_fechamento(request, fechamento_id: int):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        nova_data = payload.get('data_fechamento')  # esperado dd/mm/yyyy
        if not nova_data:
            return JsonResponse({'success': False, 'error': 'Data não informada'}, status=400)
        dt = datetime.strptime(nova_data, '%d/%m/%Y')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Formato de data inválido'}, status=400)
    try:
        cab = Fechamento.objects.get(id=fechamento_id)
    except Fechamento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fechamento não encontrado'}, status=404)
    # Bloqueia alteração se já possuir cod_ag preenchido
    if getattr(cab, 'cod_ag', None) and str(cab.cod_ag).strip() != '':
        return JsonResponse({'success': False, 'error': 'Alteração bloqueada: fechamento já possui Cod AG.'}, status=403)
    cab.data_fechamento = dt
    cab.save(update_fields=['data_fechamento'])
    return JsonResponse({'success': True, 'message': 'Data de fechamento atualizada.'})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def carta_frete(request):
    """Retorna dados agregados da view VW_CARTA_FRETE para exibir em modal.
    Filtros obrigatórios: data_inicio, data_fim (yyyy-mm-dd). Opcional: placa.
    """
    placa = (request.GET.get('placa') or '').strip()
    di = (request.GET.get('data_inicio') or '').strip()
    df = (request.GET.get('data_fim') or '').strip()
    status_f = (request.GET.get('status') or '').strip()
    if not di or not df:
        return JsonResponse({'success': False, 'error': 'Informe Data Início e Data Fim para consultar.'}, status=400)
    rows = []
    # totais específicos
    total_valor = 0.0
    total_adiant = 0.0
    total_outros = 0.0
    total_saldo = 0.0
    colnames = {'valor': None, 'adiantamento': None, 'outros': None, 'saldo': None}
    try:
        where = []
        params = []
        if placa:
            where.append("PLACA = %s")
            params.append(placa)
        if di:
            where.append("CAST(DATA AS DATE) >= %s")
            params.append(di)
        if df:
            where.append("CAST(DATA AS DATE) <= %s")
            params.append(df)
        sql = ["SELECT * FROM VW_CARTA_FRETE"]
        if where:
            sql.append("WHERE "+" AND ".join(where))
        with connection.cursor() as cursor:
            cursor.execute("\n".join(sql), params)
            cols = [c[0] for c in cursor.description]
            for r in cursor.fetchall():
                obj = dict(zip(cols, r))
                rows.append(obj)
        # detectar colunas por nome (case-insensitive)
        def pick_col(target_names):
            # tenta match exato first
            lower_map = {c.lower(): c for c in cols}
            for name in target_names:
                if name in lower_map:
                    return lower_map[name]
            # tenta por contains
            for c in cols:
                cl = c.lower()
                for name in target_names:
                    if name in cl:
                        return c
            return None

        col_valor = pick_col(['valor', 'vl', 'vl_total'])
        col_adiant = pick_col(['adiantamento', 'adiant', 'vl_adiantamento'])
        col_outros = pick_col(['outros', 'vl_outros'])
        col_saldo = pick_col(['saldo', 'vl_saldo'])
        # aplicar filtro por coluna 'situacao', se houver parâmetro status
        col_situacao = pick_col(['situacao', 'situação'])
        if status_f and col_situacao:
            wanted = (status_f or '').strip().upper()
            rows = [row for row in rows if str(row.get(col_situacao) or '').strip().upper() == wanted]

        colnames = {
            'valor': col_valor,
            'adiantamento': col_adiant,
            'outros': col_outros,
            'saldo': col_saldo,
        }
        # somar valores
        for row in rows:
            try:
                if col_valor:
                    total_valor += float(row.get(col_valor) or 0)
                if col_adiant:
                    total_adiant += float(row.get(col_adiant) or 0)
                if col_outros:
                    total_outros += float(row.get(col_outros) or 0)
                if col_saldo:
                    total_saldo += float(row.get(col_saldo) or 0)
            except Exception:
                continue
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({
        'success': True,
        'rows': rows,
        'totais': {
            'valor': total_valor,
            'adiantamento': total_adiant,
            'outros': total_outros,
            'saldo': total_saldo,
        },
        'colnames': colnames,
    })


@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def gerar_contas_a_pagar(request):
    """
    Gera um registro em Contas a Pagar (cabeçalho) e insere itens a partir dos dados da view VW_CARTA_FRETE,
    conforme seleção feita no frontend.
    Espera JSON: { placa, data_fechamento (yyyy-mm-dd), data_inicio?, data_fim?, status?, indices: [int] }
    """
    if ContasAPagarModel is None or ItensContasAPagarModel is None:
        return JsonResponse({'success': False, 'error': 'Modelos de Contas a Pagar não disponíveis.'}, status=500)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    placa = (payload.get('placa') or '').strip()
    data_fech = (payload.get('data_fechamento') or '').strip()
    di = (payload.get('data_inicio') or '').strip()
    df = (payload.get('data_fim') or '').strip()
    status_f = (payload.get('status') or '').strip()
    indices = payload.get('indices') or []
    periodos_override = payload.get('periodos', {}) or {}
    parcelas_override = payload.get('parcelas', {}) or {}
    # Opção de valor fixo
    fl_vlfixo = bool(payload.get('fl_vlfixo') or False)
    try:
        valor_fixo = float(payload.get('valor_fixo') or 0)
    except Exception:
        valor_fixo = 0.0
    if not placa or not data_fech or not isinstance(indices, list) or not indices:
        return JsonResponse({'success': False, 'error': 'Parâmetros obrigatórios ausentes'}, status=400)
    try:
        dt_fech = datetime.strptime(data_fech, '%Y-%m-%d').date()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Data de fechamento inválida (yyyy-mm-dd).'}, status=400)

    # Montar consulta igual à página
    where = []
    params = []
    where.append('PLACA = %s')
    params.append(placa)
    if di:
        where.append('CAST(DATA AS DATE) >= %s')
        params.append(di)
    if df:
        where.append('CAST(DATA AS DATE) <= %s')
        params.append(df)
    sql = ["SELECT * FROM VW_CARTA_FRETE"]
    if where:
        sql.append('WHERE ' + ' AND '.join(where))
    sql.append('ORDER BY DATA ASC')

    rows = []
    cols = []
    with connection.cursor() as cursor:
        cursor.execute('\n'.join(sql), params)
        cols = [c[0] for c in cursor.description]
        for r in cursor.fetchall():
            rows.append(dict(zip(cols, r)))
    # Aplicar filtro por situacao (aberto/fechado) após leitura para manter alinhado com os índices do modal
    def pick_col(target_names):
        lower_map = {c.lower(): c for c in cols}
        for name in target_names:
            if name in lower_map:
                return lower_map[name]
        for c in cols:
            cl = c.lower()
            for name in target_names:
                if name in cl:
                    return c
        return None
    col_situacao = pick_col(['situacao', 'situação'])
    if status_f and col_situacao:
        wanted = (status_f or '').strip().upper()
        rows = [d for d in rows if str(d.get(col_situacao) or '').strip().upper() == wanted]
    if not rows:
        return JsonResponse({'success': False, 'error': 'Nenhum dado encontrado para os filtros informados.'}, status=404)

    # Selecionar itens pela lista de índices
    sel = []
    for i in indices:
        try:
            idx = int(i)
            sel.append((idx, rows[idx]))
        except Exception:
            continue
    if not sel:
        return JsonResponse({'success': False, 'error': 'Nenhum item válido selecionado.'}, status=400)

    # Mapear colunas prováveis
    def pick_col(target_names):
        lower_map = {c.lower(): c for c in cols}
        for name in target_names:
            if name in lower_map:
                return lower_map[name]
        for c in cols:
            cl = c.lower()
            for name in target_names:
                if name in cl:
                    return c
        return None

    col_valor = pick_col(['valor', 'vl', 'vl_total'])
    col_adiant = pick_col(['adiantamento', 'adiant', 'vl_adiantamento'])
    col_outros = pick_col(['outros', 'vl_outros'])
    col_saldo = pick_col(['saldo', 'vl_saldo'])
    col_codigo = pick_col(['codigo', 'cd', 'cod'])
    col_empresa = pick_col(['empresa'])
    col_data = pick_col(['data', 'dt'])
    col_status = pick_col(['status'])
    col_trecho = pick_col(['trecho'])
    col_act = pick_col(['act', 'descricao', 'observacao'])

    # Obter FK de veículo pela placa
    # Buscar pelo campo da chave da relacionada (Agregado.placa)
    veiculo = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
    if not veiculo:
        return JsonResponse({'success': False, 'error': 'Veículo não encontrado para a placa informada.'}, status=404)

    with transaction.atomic():
        # Localizar (ou criar) cabeçalho para a mesma placa e data_fechamento
        cab, cab_created = ContasAPagarModel.objects.get_or_create(
            placa=veiculo,
            data_fechamento=dt_fech,
            defaults={
                'valor': 0.0,
                'criado_por': request.user,
                'atualizado_por': request.user,
            },
        )
        # Atualizar flags/valor fixo no cabeçalho caso o modelo possua os campos
        # Isolado em savepoint para evitar sujar a transação se a coluna ainda não existir no DB
        try:
            with transaction.atomic():
                update_fields = []
                if hasattr(cab, 'fl_vlfixo'):
                    # Campo é CharField ('S'/'N') no modelo atual
                    setattr(cab, 'fl_vlfixo', 'S' if fl_vlfixo else 'N')
                    update_fields.append('fl_vlfixo')
                if hasattr(cab, 'valor_fixo'):
                    setattr(cab, 'valor_fixo', valor_fixo)
                    update_fields.append('valor_fixo')
                if update_fields:
                    cab.save(update_fields=update_fields)
        except Exception:
            # ignora falha (ex.: migração de colunas ainda não aplicada)
            pass
        # Se já houver vencimentos vinculados a fechamento, não permitir novas inclusões
        if not cab_created:
            try:
                if VencContasPagar.objects.filter(contas_pagar=cab, fechamento__isnull=False).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Este Contas a Pagar já possui vencimentos vinculados a fechamento (enviado para pagamento) e não pode ser alterado.'
                    }, status=400)
            except Exception:
                # Se der erro na checagem, por segurança bloquear edição
                return JsonResponse({
                    'success': False,
                    'error': 'Falha ao verificar vencimentos vinculados. Inclusão de itens bloqueada para segurança.'
                }, status=400)
        # Identificar o nome do campo FK uma única vez
        fk_field_name = None
        for f in ItensContasAPagarModel._meta.get_fields():
            try:
                if isinstance(f, models.ForeignKey) and f.related_model == ContasAPagarModel:
                    fk_field_name = f.name
                    break
            except Exception:
                continue
        if not fk_field_name:
            for candidate in ('contasapagar', 'contas_pagar', 'id_contas_pagar', 'contaspagar'):
                if candidate in [ff.name for ff in ItensContasAPagarModel._meta.get_fields()]:
                    fk_field_name = candidate
                    break
        # Montar conjunto de chaves existentes para evitar duplicados
        existing_keys = set()
        if fk_field_name:
            qs_exist = ItensContasAPagarModel.objects.filter(**{fk_field_name: cab}).values('empresa', 'codigo', 'placa', 'data')
            for it in qs_exist:
                key = f"{(it.get('empresa') or '').strip()}|{(it.get('codigo') or '').strip()}|{(it.get('placa') or '').strip()}|{it.get('data')}"
                existing_keys.add(key)
        created = 0
        total_added = 0.0
        skipped_dupes = 0
        for idx_original, d in sel:
            # Parse data do item
            data_item = None
            try:
                v = d.get(col_data)
                if hasattr(v, 'date'):
                    data_item = v
                elif isinstance(v, str) and v:
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                        try:
                            data_item = datetime.strptime(v, fmt).date()
                            break
                        except Exception:
                            continue
                else:
                    data_item = dt_fech
            except Exception:
                data_item = dt_fech
            # Campos numéricos
            def num(x):
                try:
                    return float(x or 0)
                except Exception:
                    return 0.0
            # Checar duplicidade por (empresa, codigo, placa, data)
            empresa_val = (str(d.get(col_empresa) or '') if col_empresa else '')
            codigo_val = (str(d.get(col_codigo) or '') if col_codigo else '')
            dup_key = f"{empresa_val.strip()}|{placa.strip()}|{codigo_val.strip()}|{(data_item or dt_fech)}"
            if dup_key in existing_keys:
                continue
            # Montar kwargs dinamicamente e identificar o campo FK correto para Contas a Pagar
            item_kwargs = {
                'empresa': empresa_val,
                'codigo': codigo_val,
                'placa': placa,
                'data': (data_item or dt_fech),
                'act': (str(d.get(col_act) or '') if col_act else ''),
                'status': (str(d.get(col_status) or '') if col_status else ''),
                'trecho': (str(d.get(col_trecho) or '') if col_trecho else ''),
                'valor': (num(d.get(col_valor)) if col_valor else 0.0),
                'adiantamento': (num(d.get(col_adiant)) if col_adiant else 0.0),
                'outros': (num(d.get(col_outros)) if col_outros else 0.0),
                'saldo': (num(d.get(col_saldo)) if col_saldo else 0.0),
                'periodo': str(periodos_override.get(str(idx_original)) or periodos_override.get(idx_original) or 'S'),
                'parcela': int(parcelas_override.get(str(idx_original)) or parcelas_override.get(idx_original) or 1),
            }
            if fk_field_name:
                item_kwargs[fk_field_name] = cab
            # Isolar inserção de item em savepoint para não quebrar transação externa
            try:
                with transaction.atomic():
                    ItensContasAPagarModel.objects.create(**item_kwargs)
                    existing_keys.add(dup_key)
                    created += 1
                    total_added += float(item_kwargs.get('saldo') or 0.0)
            except IntegrityError:
                # Provável duplicidade pelo campo unique (ex.: codigo)
                skipped_dupes += 1
                continue
            except Exception:
                # Qualquer erro na criação deste item: desfaz apenas este savepoint e segue
                continue
        # Atualizar valor do cabeçalho
        # Definir valor do cabeçalho conforme regra de valor fixo
        if fl_vlfixo and valor_fixo > 0:
            cab.valor = valor_fixo
        else:
            if cab_created:
                cab.valor = total_added
            else:
                cab.valor = float(cab.valor or 0) + total_added
        cab.atualizado_por = request.user
        # Garantir persistência de fl_vlfixo/valor_fixo junto com a atualização do cabeçalho
        extra_updates = []
        if hasattr(cab, 'fl_vlfixo'):
            setattr(cab, 'fl_vlfixo', 'S' if fl_vlfixo else 'N')
            extra_updates.append('fl_vlfixo')
        if hasattr(cab, 'valor_fixo'):
            setattr(cab, 'valor_fixo', valor_fixo)
            extra_updates.append('valor_fixo')
        cab.save(update_fields=['valor', 'atualizado_por', 'dt_atualizacao'] + extra_updates)

        # Recalcular vencimentos (ope_contas_pagar_vencimento) com base em TODOS os itens do cabeçalho
        # Recalcular vencimentos em savepoint para evitar quebrar a transação externa
        try:
            with transaction.atomic():
                # Mapa de incremento por período
                period_days = {'S': 7, 'Q': 14, 'M': 28}
                # Agrupar valores por data de vencimento
                by_due_date = {}
                # Buscar todos itens do cabeçalho
                items_qs = ItensContasAPagarModel.objects.filter(**({fk_field_name: cab} if fk_field_name else {}))
                if fl_vlfixo and valor_fixo > 0:
                    # Valor fixo: um único vencimento na data de fechamento
                    by_due_date = {cab.data_fechamento: round(valor_fixo, 2)}
                else:
                    for it in items_qs:
                        n_parc = int(getattr(it, 'parcela', 1) or 1)
                        per = str(getattr(it, 'periodo', 'S') or 'S').upper()
                        delta = period_days.get(per, 7)
                        saldo_item = float(getattr(it, 'saldo', 0) or 0.0)
                        if n_parc <= 0:
                            n_parc = 1
                        # dividir saldo igualmente entre parcelas com ajuste na última
                        if n_parc == 1:
                            shares = [round(saldo_item, 2)]
                        else:
                            base = round(saldo_item / n_parc, 2)
                            shares = [base] * (n_parc - 1)
                            last = round(saldo_item - sum(shares), 2)
                            shares.append(last)
                        for idx in range(n_parc):
                            due = cab.data_fechamento + timedelta(days=delta * idx)
                            by_due_date[due] = float(by_due_date.get(due, 0.0) + shares[idx])

                # Apagar vencimentos atuais do cabeçalho e recriar ordenados por data
                VencContasPagar.objects.filter(contas_pagar=cab).delete()
                seq = 1
                for due_date in sorted(by_due_date.keys()):
                    VencContasPagar.objects.create(
                        contas_pagar=cab,
                        fechamento=None,
                        seq_vencimento=seq,
                        data_vencimento=due_date,
                        valor=round(by_due_date[due_date], 2),
                    )
                    seq += 1
        except Exception:
            # Falha no recálculo de vencimentos: desfaz apenas este bloco
            pass
    msg = f'Contas a Pagar atualizado: {created} itens incluídos'
    if skipped_dupes:
        msg += f' ({skipped_dupes} já existentes ignorados)'
    return JsonResponse({'success': True, 'message': msg + '.', 'id': cab.id})

    def _agrupar_fechamentos(self, qs):
        """
        Monta a mesma hierarquia da tabela de Movimentações:
        grupos = [
          { placa, total_placa, cobrar_placa, tipos: [ { tipo, total_tipo, cobrar_tipo, itens: [ ... ] } ] }
        ]
        Para Fechamento, o campo 'total' do registro é usado para somas e 'cobrar'.
        """
        by_placa = {}
        for r in qs:
            if any(getattr(f, 'name', '') == 'placa' for f in ItensFechamento._meta.get_fields()):
                placa_val = (getattr(r, 'placa', '') or '').strip() or '—'
            else:
                placa_val = (getattr(r.fechamento, 'cod_ag', '') or '').strip() or '—'
            placa = placa_val
            tipo = (r.tipo or '').strip() or 'SEM TIPO'
            if placa not in by_placa:
                by_placa[placa] = {
                    'placa': placa,
                    'total_placa': 0.0,
                    'cobrar_placa': 0.0,
                    'tipos': {}
                }
            gp = by_placa[placa]
            if tipo not in gp['tipos']:
                gp['tipos'][tipo] = {
                    'tipo': tipo,
                    'total_tipo': 0.0,
                    'cobrar_tipo': 0.0,
                    'itens': []
                }
            gt = gp['tipos'][tipo]

            item = {
                'data': r.data,
                'ordem_servico': r.ordemServico,
                'cd_item': r.cdItem,
                'nm_item': r.nmItem,
                'quantidade': r.qtde,
                'valor': r.valor,
                'total': r.total,
                'perc': None,
                'cobrar': r.total or 0.0,
                'periodo': r.periodo,
                'parcela': r.parcela,
                'nm_servico': r.nmServico,
            }
            gt['itens'].append(item)
            # somas
            gt['total_tipo'] += float(r.total or 0)
            gt['cobrar_tipo'] += float(r.total or 0)
            gp['total_placa'] += float(r.total or 0)
            gp['cobrar_placa'] += float(r.total or 0)

        # normalizar estrutura em listas
        grupos = []
        for placa, gp in by_placa.items():
            tipos_list = []
            for tipo, gt in gp['tipos'].items():
                tipos_list.append(gt)
            gp['tipos'] = tipos_list
            grupos.append(gp)
        return grupos

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def check_fechamento(request):
    """Verifica se já existe Contas a Receber para uma placa e data de fechamento (dd/mm/yyyy ou yyyy-mm-dd)."""
    placa = (request.GET.get('placa') or '').strip()
    data_str = (request.GET.get('data') or '').strip()  # esperado dd/mm/yyyy
    if not placa or not data_str:
        return JsonResponse({'success': False, 'error': 'Parâmetros inválidos'}, status=400)
    # Tenta múltiplos formatos para robustez
    dt = None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            dt = datetime.strptime(data_str, fmt)
            break
        except Exception:
            continue
    if dt is None:
        return JsonResponse({'success': False, 'error': 'Data inválida'}, status=400)

    # Verifica existência de Contas a Receber
    veic = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
    if not veic:
        return JsonResponse({'success': True, 'exists': False})
    header_exists = ContasReceber.objects.filter(placa=veic, data_fechamento=dt.date()).exists()
    return JsonResponse({'success': True, 'exists': header_exists})


@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def fechar_caixa(request):
    """
    Gera Contas a Receber (cabeçalho), insere itens selecionados em ItensContasReceber
    e recalcula VencContasReceber conforme período e parcelas.
    Espera JSON: { placa, data_inicio, data_fim, data_fechamento (dd/mm/yyyy|yyyy-mm-dd), periodo, parcela, itens_tabela }
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    placa = (payload.get('placa') or '').strip()
    data_inicio = (payload.get('data_inicio') or '').strip()
    data_fim = (payload.get('data_fim') or '').strip()
    data_fech = (payload.get('data_fechamento') or '').strip()  # dd/mm/yyyy
    periodo = (payload.get('periodo') or '').strip() or 'S'
    parcela = int(payload.get('parcela') or 1)

    itens_da_tela = (payload.get('itens_tabela') or [])
    if not placa or not data_fech:
        return JsonResponse({'success': False, 'error': 'Parâmetros obrigatórios ausentes'}, status=400)
    # Parse data de fechamento
    try:
        dt_fech = datetime.strptime(data_fech, '%d/%m/%Y')
    except Exception:
        try:
            dt_fech = datetime.strptime(data_fech, '%Y-%m-%d')
        except Exception:
            return JsonResponse({'success': False, 'error': 'Data de fechamento inválida'}, status=400)

    # Definir dt_inicio e dt_fim
    if itens_da_tela:
        # Inferir a partir dos itens
        min_dt = None
        max_dt = None
        for d in itens_da_tela:
            v = d.get('data')
            cur = None
            if hasattr(v, 'date'):
                cur = v.date()
            elif isinstance(v, str):
                for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                    try:
                        cur = datetime.strptime(v, fmt).date()
                        break
                    except Exception:
                        continue
            if cur is None:
                continue
            if min_dt is None or cur < min_dt:
                min_dt = cur
            if max_dt is None or cur > max_dt:
                max_dt = cur
        dt_inicio = min_dt or date.today()
        dt_fim = max_dt or date.today()
    else:
        if not data_inicio or not data_fim:
            return JsonResponse({'success': False, 'error': 'Parâmetros de período ausentes'}, status=400)
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except Exception:
            return JsonResponse({'success': False, 'error': 'Formato de data inválido'}, status=400)

    # Resolver id_veiculo a partir da placa informada
    veiculo_obj = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa).first()
    if not veiculo_obj:
        return JsonResponse({'success': False, 'error': 'Veículo não encontrado para a placa informada.'}, status=404)

    # Utilizar exclusivamente os dados da TABELA (payload), conforme requisito
    rows = itens_da_tela
    if not rows:
        return JsonResponse({'success': False, 'error': 'Nenhum item selecionado.'}, status=404)

    created = 0
    soma_total = 0.0
    with transaction.atomic():
        cab, _ = ContasReceber.objects.get_or_create(
            placa=veiculo_obj,
            data_fechamento=dt_fech.date(),
            defaults={
                'valor': 0.0,
                'criado_por': request.user,
                'atualizado_por': request.user,
            }
        )
        # mapa para atualizar itens já existentes (evitar duplicatas e permitir upsert)
        existing_map = {}
        for it in ItensContasReceber.objects.filter(contas_receber=cab):
            try:
                k = f"{getattr(it,'ordemServico',0)}|{getattr(it,'cdItem',0)}|{(it.data.date() if getattr(it,'data',None) else '')}"
                existing_map[k] = it
            except Exception:
                continue
        for d in rows:
            unit_val = float(d.get('valor_unitario') or 0)
            qty_val = float(d.get('quantidade') or 1)
            raw_total = float(d.get('valor') or (unit_val * qty_val))
            perc_mv = d.get('perc')
            vl_sis = float(d.get('vl_sistema') or 0.0)
            # percentual informado na tela (pode vir em 0–1 ou 0–100)
            try:
                perc_val = float(perc_mv) if perc_mv is not None else 0.0
            except Exception:
                perc_val = 0.0
            cobrar_val = float(d.get('cobrar') or raw_total)
            soma_total += cobrar_val
            # Calcular 'valor' conforme regra:
            # - se houver valor do sistema, usar diretamente
            # - senão, aplicar o percentual que veio da tabela item sobre o valor unitário (percentual a mais)
            # Observação: armazenamos o percentual exatamente como veio da tabela (apenas arredondado),
            # sem converter de fração para pontos percentuais ou inferir a partir do "cobrar".
            fator = (perc_val / 100.0) if perc_val > 1 else (perc_val or 0.0)
            # Valor a armazenar: se "Vl Sistema" efetivo (>0) vier no payload, usa-o; senão calcula por unitário + percentual
            # Observação: no cálculo por percentual não aplicar arredondamento aqui (somente exibição pode formatar)
            valor_calc = vl_sis if vl_sis > 0 else ((unit_val * (1 + (fator or 0.0))) if unit_val else 0.0)
            # Percentual: armazenar exatamente o recebido da tabela de item (apenas arredondado)
            perc_to_store = round(perc_val or 0.0, 2)
            # data do item (datetime)
            item_dt = None
            try:
                val = d.get('data')
                if hasattr(val, 'date') and hasattr(val, 'time'):
                    item_dt = val
                elif isinstance(val, str) and val:
                    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                        try:
                            item_dt = datetime.strptime(val, fmt)
                            break
                        except Exception:
                            continue
                if not item_dt:
                    item_dt = datetime.combine(dt_fim, datetime.min.time())
            except Exception:
                item_dt = datetime.combine(dt_fim, datetime.min.time())

            # chaves e nomes
            def safe_int(v, default=0):
                try:
                    return int(v)
                except Exception:
                    return default
            tipo_txt = (d.get('tipo') or d.get('type_col') or '')
            nm_item_val = d.get('nm_item') or d.get('item_name_col') or ''
            nm_serv_val = d.get('nm_servico') or d.get('name_col') or ''
            if not nm_serv_val:
                nm_serv_val = nm_item_val
            if not nm_item_val and nm_serv_val:
                nm_item_val = nm_serv_val
            os_val = d.get('ordem_servico') or d.get('os_col') or 0
            cd_item_key = safe_int(d.get('cd_item') or d.get('item_code_col') or 0, 0)
            cd_serv_key = safe_int(d.get('cd_servico') or d.get('code_col') or (d.get('cd_item') or 0), 0)
            dup_key = f"{os_val}|{cd_item_key}|{item_dt.date()}"
            if dup_key in existing_map:
                # atualizar item existente (upsert)
                it = existing_map[dup_key]
                it.cdServico = (cd_serv_key or cd_item_key)
                it.nmServico = nm_serv_val
                it.tipo = tipo_txt
                it.nmItem = nm_item_val
                it.qtde = float(d.get('quantidade') or d.get('qty_col') or 0)
                it.unidade = (d.get('unidade') or '').strip() if isinstance(d.get('unidade'), str) else ''
                it.valor_unitario = unit_val
                it.percentual = perc_to_store
                it.valor = valor_calc
                it.total = cobrar_val
                it.periodo = (d.get('periodo') or periodo)
                it.parcela = int(d.get('parcela') or parcela or 1)
                it.save(update_fields=['cdServico','nmServico','tipo','nmItem','qtde','unidade','valor_unitario','percentual','valor','total','periodo','parcela','dt_atualizacao'])
            else:
                ItensContasReceber.objects.create(
                    contas_receber=cab,
                    ordemServico=os_val,
                    cdServico=(cd_serv_key or cd_item_key),
                    nmServico=nm_serv_val,
                    data=item_dt,
                    tipo=tipo_txt,
                    cdItem=(cd_item_key or cd_serv_key),
                    nmItem=nm_item_val,
                    qtde=float(d.get('quantidade') or d.get('qty_col') or 0),
                    unidade=(d.get('unidade') or '').strip() if isinstance(d.get('unidade'), str) else '',
                    valor_unitario=unit_val,
                    percentual=perc_to_store,
                    valor=valor_calc,
                    total=cobrar_val,
                    periodo=(d.get('periodo') or periodo),
                    parcela=int(d.get('parcela') or parcela or 1),
                )
                created += 1

        # Atualizar valor total do cabeçalho
        total_cab = ItensContasReceber.objects.filter(contas_receber=cab).aggregate(s=models.Sum('total'))['s'] or 0.0
        cab.valor = float(total_cab)
        cab.atualizado_por = request.user
        cab.save(update_fields=['valor', 'atualizado_por', 'dt_atualizacao'])

        # Recalcular VencContasReceber
        try:
            with transaction.atomic():
                period_days = {'S': 7, 'Q': 14, 'M': 28}
                by_due_date = {}
                items_qs = ItensContasReceber.objects.filter(contas_receber=cab)
                for it in items_qs:
                    n_parc = int(getattr(it, 'parcela', 1) or 1)
                    per = str(getattr(it, 'periodo', 'S') or 'S').upper()
                    delta = period_days.get(per, 7)
                    valor_item = float(getattr(it, 'total', 0) or 0.0)
                    if n_parc <= 0:
                        n_parc = 1
                    if n_parc == 1:
                        shares = [round(valor_item, 2)]
                    else:
                        base = round(valor_item / n_parc, 2)
                        shares = [base] * (n_parc - 1)
                        last = round(valor_item - sum(shares), 2)
                        shares.append(last)
                    for idx in range(n_parc):
                        due = cab.data_fechamento + timedelta(days=delta * idx)
                        by_due_date[due] = float(by_due_date.get(due, 0.0) + shares[idx])
                # recriar
                VencContasReceber.objects.filter(contas_receber=cab).delete()
                seq = 1
                for due_date in sorted(by_due_date.keys()):
                    VencContasReceber.objects.create(
                        contas_receber=cab,
                        fechamento=None,
                        seq_vencimento=seq,
                        data_vencimento=due_date,
                        valor=round(by_due_date[due_date], 2),
                    )
                    seq += 1
        except Exception:
            pass

    return JsonResponse({'success': True, 'created': created, 'message': f'Contas a Receber atualizado com {created} itens. Total R$ {soma_total:.2f}.'})

@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@require_GET
def prestacao_contas_pdf(request):
    """
    Gera PDF de Prestação de Contas no servidor.
    Parâmetros:
      - data_fechamento: yyyy-mm-dd
      - placa: pode repetir múltiplas vezes (?placa=AAA&placa=BBB)
    Retorna application/pdf para download (arquivo único com todas as placas).
    """
    if pisa is None:
        return JsonResponse({'success': False, 'error': 'Biblioteca xhtml2pdf não instalada no servidor.'}, status=500)
    data_str = (request.GET.get('data_fechamento') or '').strip()
    placas = request.GET.getlist('placa') or []
    if not data_str or not placas:
        return JsonResponse({'success': False, 'error': 'Informe data_fechamento e ao menos uma placa.'}, status=400)
    # Reusa a lógica de gestao_fechamento_detalhes para cada placa
    docs = []
    for placa in placas:
        try:
            # construir contexto por placa
            req = request  # reutiliza timezone/locales
            # Copia essencial da função gestao_fechamento_detalhes
            dt = None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    dt = datetime.strptime(data_str, fmt).date()
                    break
                except Exception:
                    continue
            if dt is None:
                continue
            start_dt = dt
            end_dt = dt + timedelta(days=1)
            # Vencimentos CR/CP por data de fechamento (regra ajustada)
            cr_qs = VencContasReceber.objects.select_related('contas_receber', 'contas_receber__placa').filter(contas_receber__data_fechamento=dt)
            veic_qs = Veiculo.objects.select_related('placa').filter(placa__placa__iexact=placa)
            veic_ids = list(veic_qs.values_list('id_veiculo', flat=True))
            if veic_ids:
                cr_qs = cr_qs.filter(contas_receber__placa__in=veic_ids)
            cr_rows = []
            for v in cr_qs:
                cr_rows.append({
                    'seq': v.seq_vencimento,
                    'data': v.data_vencimento.strftime('%d/%m/%Y') if v.data_vencimento else '',
                    'valor': float(v.valor or 0),
                })
            cp_qs = VencContasPagar.objects.select_related('contas_pagar', 'contas_pagar__placa').filter(contas_pagar__data_fechamento=dt)
            if veic_ids:
                cp_qs = cp_qs.filter(contas_pagar__placa__in=veic_ids)
            cp_rows = []
            for v in cp_qs:
                cp_rows.append({
                    'seq': v.seq_vencimento,
                    'data': v.data_vencimento.strftime('%d/%m/%Y') if v.data_vencimento else '',
                    'valor': float(v.valor or 0),
                })
            # Lançamentos
            lanc_qs = Lancamento.objects.select_related('veiculo', 'veiculo__placa').filter(data=dt)
            if veic_ids:
                lanc_qs = lanc_qs.filter(veiculo__id_veiculo__in=veic_ids)
            lanc_rows = []
            for l in lanc_qs:
                lanc_rows.append({
                    'data': l.data.strftime('%d/%m/%Y') if l.data else '',
                    'categoria': getattr(l.categoria, 'nome', ''),
                    'valor': float(l.valor or 0),
                    'obs': l.obs or '',
                    'periodo': getattr(l, 'periodo', '') or '',
                    'parcela': getattr(l, 'parcela', 1) or 1,
                })
            # Itens CR/CP
            cr_itens_rows = []
            cp_itens_rows = []
            cr_cabs = ContasReceber.objects.filter(data_fechamento=dt)
            if veic_ids:
                cr_cabs = cr_cabs.filter(placa__id_veiculo__in=veic_ids)
            cr_ids = list(cr_cabs.values_list('id', flat=True))
            if cr_ids:
                for it in ItensContasReceber.objects.select_related().filter(contas_receber_id__in=cr_ids).order_by('data', 'ordemServico'):
                    cr_itens_rows.append({
                        'os': it.ordemServico,
                        'servico': it.nmServico,
                        'data': it.data.strftime('%d/%m/%Y') if it.data else '',
                        'item': it.nmItem,
                        'qtde': float(it.qtde or 0),
                        'un': it.unidade or '',
                        'valor': float(it.valor or 0),
                        'percentual': float(it.percentual or 0),
                        'valor_unit': float(it.valor_unitario or 0),
                        'total': float(it.total or 0),
                        'periodo': getattr(it, 'periodo', '') or '',
                        'parcela': getattr(it, 'parcela', 1) or 1,
                    })
            cp_cabs = ContasAPagarModel.objects.filter(data_fechamento=dt)
            if veic_ids:
                cp_cabs = cp_cabs.filter(placa__id_veiculo__in=veic_ids)
            cp_ids = list(cp_cabs.values_list('id', flat=True))
            if cp_ids and ItensContasAPagarModel:
                for it in ItensContasAPagarModel.objects.select_related().filter(**{'contas_pagar_id__in': cp_ids}).order_by('data', 'codigo'):
                    cp_itens_rows.append({
                        'empresa': it.empresa or '',
                        'codigo': it.codigo or '',
                        'placa': it.placa or '',
                        'data': it.data.strftime('%d/%m/%Y') if it.data else '',
                        'act': it.act or '',
                        'status': it.status or '',
                        'trecho': it.trecho or '',
                        'valor': float(it.valor or 0),
                        'adiantamento': float(it.adiantamento or 0),
                        'outros': float(it.outros or 0),
                        'saldo': float(it.saldo or 0),
                        'periodo': it.periodo or '',
                        'parcela': it.parcela or 1,
                    })
            # Totais (ótica do agregado, como no front):
            sCR = sum([float(x.get('valor', 0) or 0) for x in cr_rows])  # a pagar (agregado)
            sCP = sum([float(x.get('valor', 0) or 0) for x in cp_rows])  # a receber (agregado)
            sLN = sum([float(x.get('valor', 0) or 0) for x in lanc_rows])
            total_geral = (sCP - sCR + sLN)
            # Agregado (nome)
            ag_nome = ''
            try:
                veic = veic_qs.first()
                ag_nome = getattr(getattr(veic, 'placa', None), 'nm_agregado', '') or ''
            except Exception:
                ag_nome = ''
            docs.append({
                'placa': placa,
                'agregado': ag_nome,
                'data': data_str,
                'cr_itens': cr_itens_rows,
                'cp_itens': cp_itens_rows,
                'cr_venc': cr_rows,
                'cp_venc': cp_rows,
                'lanc': lanc_rows,
                'totais': {
                    'sCR': sCR, 'sCP': sCP, 'sLN': sLN, 'totalGeral': total_geral
                }
            })
        except Exception:
            continue
    if not docs:
        return JsonResponse({'success': False, 'error': 'Sem dados para gerar.'}, status=404)
    context = {
        'docs': docs,
        'logo_url': staticfiles_storage.url('img/logo.png'),
        'logo_src': (getattr(staticfiles_storage, 'base_url', None) or '/static/') + 'img/logo.png',
        'logo_data_uri': None,
        'logo_abs_path': None,
        'logo_file_uri': None,
        'hoje': date.today().strftime('%d/%m/%Y'),
    }
    # Converter logo para RGB (sem transparência) para evitar máscara escura no PDF
    try:
        logo_path = staticfiles_storage.path('img/logo.png')
        with Image.open(logo_path) as im:
            if im.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', im.size, (255, 255, 255))
                alpha = im.split()[-1]
                bg.paste(im, mask=alpha)
                im_rgb = bg
            else:
                im_rgb = im.convert('RGB')
            # Salvar como JPEG temporário (sem canal alpha) para evitar máscara
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            tmp.close()
            im_rgb.save(tmp.name, format='JPEG', quality=95)
            context['logo_abs_path'] = tmp.name
            try:
                context['logo_file_uri'] = Path(tmp.name).as_uri()
            except Exception:
                context['logo_file_uri'] = None
            # Além disso, disponibilizar como data URI (JPEG) para engines que preferem inline
            buf = BytesIO()
            im_rgb.save(buf, format='JPEG', quality=95)
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            context['logo_data_uri'] = f'data:image/jpeg;base64,{b64}'
    except Exception:
        pass
    html = render_to_string('operacional/prestacao_contas_pdf.html', context)
    result = BytesIO()
    def link_callback(uri, rel):
        try:
            base_url = getattr(staticfiles_storage, 'base_url', None) or '/static/'
            # map /static/... to filesystem path
            if uri.startswith(base_url):
                rel_path = uri.replace(base_url, '')
                return staticfiles_storage.path(rel_path)
            # file:/// scheme
            if uri.startswith('file://'):
                return uri.replace('file://', '')
            # absolute path on filesystem
            if os.path.isabs(uri) and os.path.exists(uri):
                return uri
            return uri
        except Exception:
            return uri
    pisa.CreatePDF(html, dest=result, link_callback=link_callback, encoding='utf-8')
    pdf = result.getvalue()
    if not pdf:
        return JsonResponse({'success': False, 'error': 'Falha ao montar PDF.'}, status=500)
    # Definir nome do arquivo
    def _sanitize(t: str) -> str:
        try:
            import re, unicodedata
            t = unicodedata.normalize('NFD', str(t))
            t = ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')
            t = re.sub(r'[^A-Za-z0-9_\\-]+', '_', t)
            t = re.sub(r'_+', '_', t).strip('_')
            return t
        except Exception:
            return str(t).replace(' ', '_')
    fname = f'prestacao_{data_str}.pdf'
    try:
        if len(placas) == 1 and docs:
            placa_fname = _sanitize(docs[0].get('placa') or placas[0] or '')
            ag_fname = _sanitize(docs[0].get('agregado') or '')
            parts = [p for p in [placa_fname, ag_fname, data_str] if p]
            if parts:
                fname = '_'.join(parts) + '.pdf'
    except Exception:
        pass
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp

class LancamentosListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View completa para gestão de lançamentos com filtros, paginação e funcionalidades CRUD
    """
    model = Lancamento
    template_name = 'operacional/lancamentos.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'lancamentos'
    paginate_by = 10
    ordering = ['-data', '-dt_criacao']
    
    def get_queryset(self):
        """
        Retorna queryset filtrado por veículo, categoria, data, período e usuário
        """
        queryset = super().get_queryset().select_related(
            'veiculo__placa', 'categoria', 'usuario'
        )
        
        # Filtros
        veiculo_filtro = self.request.GET.get('veiculo', '')
        categoria_filtro = self.request.GET.get('categoria', '')
        data_inicio = self.request.GET.get('data_inicio', '')
        data_fim = self.request.GET.get('data_fim', '')
        periodo_filtro = self.request.GET.get('periodo', '')
        usuario_filtro = self.request.GET.get('usuario', '')
        
        # Aplicar filtro por veículo
        if veiculo_filtro:
            queryset = queryset.filter(
                Q(veiculo__placa__placa__icontains=veiculo_filtro) |
                Q(veiculo__placa__nm_agregado__icontains=veiculo_filtro)
            )
        
        # Aplicar filtro por categoria
        if categoria_filtro:
            queryset = queryset.filter(categoria__id=categoria_filtro)
        
        # Aplicar filtro por período de data
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        
        # Aplicar filtro por período
        if periodo_filtro:
            queryset = queryset.filter(periodo=periodo_filtro)
        
        # Aplicar filtro por usuário
        if usuario_filtro:
            queryset = queryset.filter(usuario__id=usuario_filtro)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Adiciona contexto extra para os filtros, formulário e estatísticas
        """
        context = super().get_context_data(**kwargs)
        
        # Filtros atuais
        veiculo_filtro = self.request.GET.get('veiculo', '')
        categoria_filtro = self.request.GET.get('categoria', '')
        data_inicio = self.request.GET.get('data_inicio', '')
        data_fim = self.request.GET.get('data_fim', '')
        periodo_filtro = self.request.GET.get('periodo', '')
        usuario_filtro = self.request.GET.get('usuario', '')
        
        # Opções para filtros
        categorias_disponiveis = OpeCategoria.objects.all().order_by('nome')
        usuarios_disponiveis = User.objects.filter(
            lancamentos_id_usuario__isnull=False
        ).distinct().order_by('username')
        
        # Formulário para novo lançamento
        form = LancamentoForm()
        
        # Estatísticas
        queryset_filtrado = self.get_queryset()
        total_valor = queryset_filtrado.aggregate(total=Sum('valor'))['total'] or 0
        total_lancamentos = queryset_filtrado.count()
        
        context.update({
            'veiculo_filtro': veiculo_filtro,
            'categoria_filtro': categoria_filtro,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'periodo_filtro': periodo_filtro,
            'usuario_filtro': usuario_filtro,
            'categorias_disponiveis': categorias_disponiveis,
            'usuarios_disponiveis': usuarios_disponiveis,
            'form': form,
            'total_valor': total_valor,
            'total_lancamentos': total_lancamentos,
            'periodos_choices': Lancamento._meta.get_field('periodo').choices,
        })
        
        return context

@csrf_exempt
@require_http_methods(["POST"])
def criar_lancamento(request):
    """
    View AJAX para criar novo lançamento
    """
    if not request.user.has_perm('operacional.acessar_operacional'):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        form = LancamentoForm(data)
        
        if form.is_valid():
            lancamento = form.save(commit=False)
            lancamento.usuario = request.user
            lancamento.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Lançamento criado com sucesso!',
                'lancamento': {
                    'id': lancamento.id,
                    'veiculo': str(lancamento.veiculo.placa.placa),
                    'categoria': str(lancamento.categoria.nome),
                    'data': lancamento.data.strftime('%d/%m/%Y'),
                    'valor': float(lancamento.valor),
                    'periodo': lancamento.get_periodo_display(),
                    'parcela': lancamento.parcela,
                    'obs': lancamento.obs or '',
                    'usuario': lancamento.usuario.username
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def editar_lancamento(request, lancamento_id):
    """
    View AJAX para editar lançamento existente
    """
    if not request.user.has_perm('operacional.acessar_operacional'):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    try:
        lancamento = get_object_or_404(Lancamento, id=lancamento_id)
        data = json.loads(request.body)
        form = LancamentoForm(data, instance=lancamento)
        
        if form.is_valid():
            lancamento = form.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Lançamento atualizado com sucesso!',
                'lancamento': {
                    'id': lancamento.id,
                    'veiculo': str(lancamento.veiculo.placa.placa),
                    'categoria': str(lancamento.categoria.nome),
                    'data': lancamento.data.strftime('%d/%m/%Y'),
                    'valor': float(lancamento.valor),
                    'periodo': lancamento.get_periodo_display(),
                    'parcela': lancamento.parcela,
                    'obs': lancamento.obs or '',
                    'usuario': lancamento.usuario.username
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def excluir_lancamento(request, lancamento_id):
    """
    View AJAX para excluir lançamento
    """
    if not request.user.has_perm('operacional.acessar_operacional'):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    try:
        lancamento = get_object_or_404(Lancamento, id=lancamento_id)
        lancamento.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Lançamento excluído com sucesso!'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def obter_lancamento(request, lancamento_id):
    """
    View AJAX para obter dados de um lançamento específico
    """
    if not request.user.has_perm('operacional.acessar_operacional'):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    try:
        lancamento = get_object_or_404(Lancamento, id=lancamento_id)
        
        return JsonResponse({
            'success': True,
            'lancamento': {
                'id': lancamento.id,
                'veiculo': lancamento.veiculo.id_veiculo,  # mantém compatível com choices do form
                'categoria': lancamento.categoria.id,
                'data': lancamento.data.strftime('%Y-%m-%d'),
                    'natureza': getattr(lancamento, 'natureza', ''),
                'valor': float(lancamento.valor),
                'periodo': lancamento.periodo,
                'parcela': lancamento.parcela,
                'obs': lancamento.obs or ''
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)