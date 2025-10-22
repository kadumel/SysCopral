from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView
from django.db.models import Q, Sum, F
from django.db import models
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db import connection, transaction
from django.contrib import messages
from .models import Veiculo, Servico, Item, Abastecimento, Atualizações, Lancamento, OpeCategoria, Fechamento, ItensFechamento, tipo_periodo
from datetime import date, timedelta, datetime  
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
            item = Item.objects.get(id_item=item_id)
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
            item = Item.objects.get(id_item=item_id)
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
        if item_ids:
            # tentar por id_item
            for it in Item.objects.filter(id_item__in=list(item_ids)).values('id_item', 'percentual'):
                item_id_to_percent[it['id_item']] = it['percentual'] or 0
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
            for it in Item.objects.filter(pro_codigo__in=list(item_codes_str)).values('pro_codigo', 'percentual'):
                item_code_to_percent[str(it['pro_codigo']).strip()] = it['percentual'] or 0
        if item_names_str:
            for it in Item.objects.filter(nm_item__in=list(item_names_str)).values('nm_item', 'percentual'):
                item_name_to_percent[str(it['nm_item']).strip().upper()] = it['percentual'] or 0

        # Preparar mapa de status "fechado" por item (ordem, cd_item, data, placa)
        placas_str = set([ (r.get('placa') or '').strip() for r in rows if r.get('placa') ])
        plate_to_veic = {}
        if placas_str:
            for v in Veiculo.objects.select_related('placa').filter(placa__placa__in=list(placas_str)).values('id_veiculo','placa__placa'):
                plate_to_veic[v['placa__placa']] = v['id_veiculo']

        # Intervalo de datas
        di = self.request.GET.get('data_inicio') or data_inicio
        df = self.request.GET.get('data_fim') or data_fim
        items_qs = ItensFechamento.objects.select_related('fechamento','fechamento__placa','fechamento__placa__placa')
        if di:
            items_qs = items_qs.filter(data__date__gte=di)
        if df:
            items_qs = items_qs.filter(data__date__lte=df)
        if plate_to_veic:
            items_qs = items_qs.filter(fechamento__placa__in=list(plate_to_veic.values()))

        # Conjuntos de itens fechados por item e por serviço
        closed_by_item = set()
        closed_by_serv = set()
        for it in items_qs.values('ordemServico','cdItem','cdServico','data','fechamento__placa__placa__placa'):
            plate_txt = it['fechamento__placa__placa__placa']
            date_only = it['data'].date() if hasattr(it['data'],'date') else it['data']
            closed_by_item.add((it['ordemServico'], it.get('cdItem'), date_only, plate_txt))
            closed_by_serv.add((it['ordemServico'], it.get('cdServico'), date_only, plate_txt))

        for r in rows:
            placa = (r.get('placa') or '').strip() if r.get('placa') else 'SEM PLACA'
            tipo_raw = (r.get('nm_tipo_servico') or '').strip() if r.get('nm_tipo_servico') else ''
            tipo_norm = tipo_raw.lower().replace('ç','c').replace('õ','o').replace('ó','o').replace('á','a').replace('é','e').replace('í','i').replace('ú','u').replace('â','a').replace('ê','e').replace('ô','o')
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
                # Demais tipos: cobrar = TOTAL + (percentual * TOTAL). Se percentual vazio/zero, cobrar = TOTAL.
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
                base_total = float(total_item or 0)
                if perc_f == 0.0:
                    cobrar_val = base_total
                    perc_display = 0.0
                else:
                    fator = perc_f if perc_f <= 1 else (perc_f / 100.0)
                    cobrar_val = base_total + (fator * base_total)
                    perc_display = perc_f if perc_f > 1 else (perc_f * 100.0)

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

        # Calcular data de fechamento +15 dias
        fechamento_display = ''
        fechamento_raw = ''
        data_fim_ctx = self.request.GET.get('data_fim', '').strip()
        if data_fim_ctx:
            try:
                dt_fim = datetime.strptime(data_fim_ctx, '%Y-%m-%d').date()
                dt_fech = dt_fim + timedelta(days=14)
                fechamento_display = dt_fech.strftime('%d/%m/%Y')
                fechamento_raw = dt_fech.strftime('%Y-%m-%d')
            except Exception:
                fechamento_display = ''
                fechamento_raw = ''

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
            'data_fechamento_calculada': fechamento_display,
            'data_fechamento_raw': fechamento_raw,
            # Campos padrão para período/parcelas
            'periodos_choices': tipo_periodo,
            'periodo_selecionado': self.request.GET.get('periodo', 'M'),
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
        qs = Fechamento.objects.select_related('placa', 'placa__placa').all().order_by('-datafechamento')
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
                qs = qs.filter(datafechamento__date=dt)
            except Exception:
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Opções para selects
        datas_distintas = (
            Fechamento.objects.order_by('-datafechamento')
            .values_list('datafechamento__date', flat=True)
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

        context.update({
            'cod_ag_filtro': self.request.GET.get('cod_ag', ''),
            'agregado_filtro': agregado_sel,
            'placa_filtro': self.request.GET.get('placa', ''),
            'data_fechamento': self.request.GET.get('data_fechamento', ''),
            'total_registros': self.get_queryset().count(),
            'datas_fechamento_opcoes': datas_opcoes,
            'agregados_disponiveis': agregados_disponiveis,
            'placas_disponiveis': placas_disponiveis,
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
        novo_total = (float(cab.valor_cargas or 0) - total_item)
        cab.valor_cargas = novo_total if novo_total > 0 else 0.0
        cab.save(update_fields=['valor_cargas'])
    return JsonResponse({'success': True, 'message': 'Item excluído com sucesso.', 'novo_total': float(cab.valor_cargas or 0)})

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
    cab.datafechamento = dt
    cab.save(update_fields=['datafechamento'])
    return JsonResponse({'success': True, 'message': 'Data de fechamento atualizada.'})

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
    """Verifica se já existe fechamento para uma placa em determinada data de fechamento (dd/mm/yyyy)."""
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

    # Resolve possíveis veículos pela placa de texto para evitar lookup 
    veic_ids = list(Veiculo.objects.select_related('placa')
                    .filter(placa__placa__iexact=placa)
                    .values_list('id_veiculo', flat=True))
    print(placa, '*'*100)
    print(veic_ids)

    # Verifica por cabeçalho e por itens (qualquer um que existir)
    header_qs = Fechamento.objects.select_related('placa', 'placa__placa').filter(datafechamento__date=dt.date())
    
    if veic_ids:
        header_qs = header_qs.filter(Q(placa__in=veic_ids))
    
    header_exists = header_qs.exists()

    return JsonResponse({'success': True, 'exists': header_exists})


@login_required
@permission_required('operacional.acessar_operacional', raise_exception=True)
@csrf_exempt
@require_POST
def fechar_caixa(request):
    """
    Insere registros na tabela de Fechamento com base nos dados exibidos na tela (VW_MOVIMENTACOES),
    agrupando por placa/tipo/item conforme o período selecionado.
    Espera JSON: { placa, data_inicio, data_fim, data_fechamento (dd/mm/yyyy), periodo, parcela, itens_tabela? }
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    placa = (payload.get('placa') or '').strip()
    data_inicio = (payload.get('data_inicio') or '').strip()
    data_fim = (payload.get('data_fim') or '').strip()
    data_fech = (payload.get('data_fechamento') or '').strip()  # dd/mm/yyyy
    periodo = (payload.get('periodo') or '').strip() or 'M'
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

    # Se já existir fechamento no dia/placa, vamos anexar APENAS itens ainda não fechados (com base nos dados enviados da tela)
    existing_header = Fechamento.objects.select_related('placa', 'placa__placa').filter(datafechamento__date=dt_fech.date(), placa=veiculo_obj).first()

    # Utilizar exclusivamente os dados da TABELA (payload), conforme requisito
    rows = itens_da_tela

    # Não consultar a view; usar somente os dados da tabela (payload)

    if not rows:
        return JsonResponse({'success': False, 'error': 'Nenhum dado para fechar neste período.'}, status=404)

    # Criar cabeçalho e itens
    created = 0
    soma_total = 0.0
    with transaction.atomic():
        cab = existing_header or Fechamento.objects.create(
            placa=veiculo_obj,
            datafechamento=dt_fech,
            cod_ag=None,
            valor_cargas=0.0,
            usuario=request.user,
        )
        for d in rows:
            # d vem do DOM com chaves: data, ordem_servico, cd_item, nm_item, quantidade, valor_unitario, valor, perc, cobrar, tipo?
            unit_val = float(d.get('valor_unitario') or 0)
            qty_val = float(d.get('quantidade') or 1)
            raw_total = float(d.get('valor') or (unit_val * qty_val))
            perc_mv = d.get('perc')
            try:
                perc_val = float(perc_mv) if perc_mv is not None else 0.0
            except Exception:
                perc_val = 0.0

            tipo_txt = (d.get('tipo') or d.get('type_col') or '')
            tipo_norm = str(tipo_txt).lower()
            # Garantir mapeamento correto de serviço x item
            cd_serv = d.get('cd_servico') or d.get('code_col') or 0
            cobrar_val = 0.0
            if ('servic' in tipo_norm) or (str(d.get('is_servico')).lower() == 'true'):
                # manter o valor de cobrar vindo da tela (já reflete regras e edições)
                cobrar_val = float(d.get('cobrar') or raw_total)
            else:
                # Outros: manter o valor cobrar da tela (calculado com percentual editado)
                cobrar_val = float(d.get('cobrar') or raw_total)

            soma_total += cobrar_val

            # pular itens já fechados (existentes) para este cabeçalho na mesma OS + cd_item + data
            data_only = None
            try:
                val = d.get('data')
                if hasattr(val, 'date'):
                    data_only = val.date()
                elif isinstance(val, str) and val:
                    # tentar dd/mm/YYYY e YYYY-MM-DD
                    try:
                        data_only = datetime.strptime(val, '%d/%m/%Y').date()
                    except Exception:
                        try:
                            data_only = datetime.strptime(val, '%Y-%m-%d').date()
                        except Exception:
                            data_only = None
            except Exception:
                data_only = None
            # Determinar chaves para duplicidade por tipo de lançamento
            tipo_txt = (d.get('tipo') or d.get('type_col') or '')
            tipo_norm = str(tipo_txt).lower()
            is_serv = (str(d.get('is_servico')).lower() == 'true') or ('servi' in tipo_norm)
            def safe_int(v, default=0):
                try:
                    return int(v)
                except Exception:
                    return default
            cd_item_key = safe_int(d.get('item_code_col') or d.get('cd_item') or 0, 0)
            # Para serviços, se não vier cd_servico usar fallback para o código visível (cd_item)
            cd_serv_key = safe_int(d.get('cd_servico') or d.get('code_col') or (d.get('cd_item') if is_serv else 0), 0)

            # sem checagem de duplicidade: sempre insere conforme a tabela
            # normalizar data datetime para o item
            item_dt = None
            try:
                val = d.get('data')
                if hasattr(val, 'date'):
                    item_dt = val
                elif isinstance(val, str) and val:
                    try:
                        item_dt = datetime.strptime(val, '%d/%m/%Y')
                    except Exception:
                        try:
                            item_dt = datetime.strptime(val, '%Y-%m-%d')
                        except Exception:
                            item_dt = datetime.combine(dt_fim, datetime.min.time())
                else:
                    item_dt = datetime.combine(dt_fim, datetime.min.time())
            except Exception:
                item_dt = datetime.combine(dt_fim, datetime.min.time())

            # Garantir preenchimento de ambos conjuntos de campos (serviço e item)
            # Fallback cruzado para evitar vazios quando a origem não envia um dos códigos
            nm_item_val = d.get('nm_item') or d.get('item_name_col') or ''
            nm_serv_val = d.get('nm_servico') or d.get('name_col') or ''
            if not nm_serv_val:
                nm_serv_val = nm_item_val
            if not nm_item_val and nm_serv_val:
                nm_item_val = nm_serv_val

            create_kwargs = {
                'fechamento': cab,
                'ordemServico': d.get('ordem_servico') or d.get('os_col') or 0,
                'cdServico': (cd_serv_key or cd_item_key),
                'nmServico': nm_serv_val,
                'data': item_dt,
                'tipo': d.get('tipo') or d.get('type_col') or '',
                'cdItem': (cd_item_key or cd_serv_key),
                'nmItem': nm_item_val,
                'qtde': float(d.get('quantidade') or d.get('qty_col') or 0),
                'unidade': (d.get('unidade') or '').strip() if isinstance(d.get('unidade'), str) else '',
                'valor_unitario': unit_val,
                'percentual': perc_val,
                'valor': raw_total,
                'total': cobrar_val,
                'periodo': periodo,
                'parcela': parcela,
            }
            for fld, val in (
                ('placa', d.get('plate_col') or placa),
                ('frota', ''),
                ('carreta', None),
                ('km', 0),
            ):
                if any(getattr(f, 'name', '') == fld for f in ItensFechamento._meta.get_fields()):
                    create_kwargs[fld] = val
            ItensFechamento.objects.create(**create_kwargs)
            created += 1
        # Atualiza valor total do cabeçalho somando novamente do banco (mais confiável), caso já existisse
        total_cab = ItensFechamento.objects.filter(fechamento=cab).aggregate(s=models.Sum('total'))['s'] or 0.0
        cab.valor_cargas = float(total_cab)
        cab.save(update_fields=['valor_cargas'])

    return JsonResponse({'success': True, 'created': created, 'message': f'Fechamento criado com {created} registros. Total R$ {soma_total:.2f}.'})

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