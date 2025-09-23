from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import connection, transaction
from django.contrib import messages
from .models import Veiculo, Servico, Item, Abastecimento, Atualizações
from datetime import date, timedelta, datetime
from django.utils import timezone
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
        
        # Aplicar filtro por código do item se fornecido
        if cd_item_filtro:
            queryset = queryset.filter(
                Q(cd_item__icontains=cd_item_filtro)
            )
        
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
        new_percentage = data.get('percentage')
        
        if not item_id or new_percentage is None:
            return JsonResponse({
                'success': False,
                'message': 'Dados incompletos'
            }, status=400)
        
        # Validar se o percentual é um número válido
        try:
            percentage_value = float(new_percentage)
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
        try:
            item = Item.objects.get(cd_item=item_id)
            item.percentual = percentage_value
            item.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Percentual atualizado com sucesso',
                'new_percentage': percentage_value
            })
        except Item.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Item não encontrado'
            }, status=404)
            
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
        item_id = data.get('item_id')
        new_value = data.get('value')

        if not item_id or new_value is None:
            return JsonResponse({
                'success': False,
                'message': 'Dados incompletos'
            }, status=400)

        # Validar valor numérico
        try:
            value_float = float(new_value)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Valor deve ser um número válido'
            }, status=400)

        # Atualizar item
        try:
            item = Item.objects.get(cd_item=item_id)
            item.vl_sistema = value_float
            item.save()
            return JsonResponse({
                'success': True,
                'message': 'Valor do sistema atualizado com sucesso',
                'new_value': value_float
            })
        except Item.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Item não encontrado'
            }, status=404)

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
    View para listar serviços relacionados a movimentações
    """
    model = Servico
    template_name = 'operacional/servicos_movimentos.html'
    permission_required = 'operacional.acessar_operacional'
    context_object_name = 'servicos'
    paginate_by = 10
    ordering = ['nm_servico']
    
    def get_queryset(self):
        """
        Retorna queryset de serviços com filtros aplicados
        """
        queryset = super().get_queryset()
        
        nm_servico_filtro = self.request.GET.get('nm_servico', '')
        tipo_servico_filtro = self.request.GET.get('tipo_servico', '')
        cd_servico_filtro = self.request.GET.get('cd_servico', '')
        
        if nm_servico_filtro:
            queryset = queryset.filter(nm_servico__icontains=nm_servico_filtro)
        
        if tipo_servico_filtro:
            queryset = queryset.filter(nm_tipo_servico__icontains=tipo_servico_filtro)
            
        if cd_servico_filtro:
            queryset = queryset.filter(cd_servico__icontains=cd_servico_filtro)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter valores distintos para os filtros
        tipos_servico_disponiveis = Servico.objects.values_list('nm_tipo_servico', flat=True).distinct().exclude(nm_tipo_servico__isnull=True).exclude(nm_tipo_servico__exact='').order_by('nm_tipo_servico')
        
        context.update({
            'nm_servico_filtro': self.request.GET.get('nm_servico', ''),
            'tipo_servico_filtro': self.request.GET.get('tipo_servico', ''),
            'cd_servico_filtro': self.request.GET.get('cd_servico', ''),
            'tipos_servico_disponiveis': tipos_servico_disponiveis,
            'total_servicos': self.get_queryset().count(),
        })
        
        return context
