from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import json
from .models import TrucksVeiculos, TrucksPosicaoCarroApi, TrucksImportadosExcel
from .forms import JornadaFilterForm
from datetime import datetime, timedelta
from django.db.models import Count, Q, DateField
from django.db.models.functions import Cast
from django.utils import timezone
from django.contrib import messages
import diversos.importacao.connectionFactory as cf
from collections import defaultdict, OrderedDict
import pandas as pd
import os
from django.conf import settings
import logging
from django.contrib import messages
from xlrd import open_workbook, xldate
from datetime import datetime, timedelta
import copral.connectionFactory as cf
from .models import TrucksImportadosExcel

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



@login_required
def controleJornada(request):
    from datetime import datetime, timedelta
    
    # Calcular datas padrão: dia 21 do mês anterior ao dia 20 do mês atual
    hoje = datetime.now()
    
    # Data inicial: sempre dia 21 do mês anterior
    if hoje.month == 1:
        data_inicial_default = hoje.replace(year=hoje.year-1, month=12, day=21)
    else:
        data_inicial_default = hoje.replace(month=hoje.month-1, day=21)
    
    # Data final: sempre dia 20 do mês atual
    data_final_default = hoje.replace(day=20)
    
    query_motorista = 'select distinct motoristaRAS from vw_consolidado'
    query_placa = 'select distinct placa from vw_consolidado'
    placas = cf.getAll(query_placa)
    motoristas = cf.getAll(query_motorista)

    # Preparar dados iniciais do formulário com datas padrão
    initial_data = {
        'data_inicial': data_inicial_default.strftime('%Y-%m-%d'),
        'data_final': data_final_default.strftime('%Y-%m-%d'),
        'selecao': 'todos'
    }
    
    if request.method == 'POST':
        form = JornadaFilterForm(request.POST)
        if form.is_valid():
            np = form.cleaned_data.get('nome_placa', '')
            da = form.cleaned_data.get('data_inicial')
            df = form.cleaned_data.get('data_final')
            slc = form.cleaned_data.get('selecao', 'todos')

            # Formatar datas para SQL Server
            da_str = da.strftime('%d/%m/%Y') if da else data_inicial_default.strftime('%d/%m/%Y')
            df_str = df.strftime('%d/%m/%Y') if df else data_final_default.strftime('%d/%m/%Y')

            sql = f"set dateformat dmy select * from vw_consolidado where convert(date, data) between '{da_str}' and '{df_str}'"
            
            if slc == 'todos':
                query = f"{sql}"
            elif slc == 'placa':
                query = f"{sql} and placa = '{np.strip()}'"
            elif slc == 'motorista':
                query = f"{sql} and motoristaRas like '{np}'"
            
            try:
                result = cf.getAll(query)
                print(query)
                
                if len(result) == 0:
                    messages.info(request, "Ops... Nenhum registro encontrado :(")
                

                totais = procHoras(result)
                
                # Calcular estatísticas adicionais
                total_placas_distintas = len(set([registro[0] for registro in result if registro[0]]))  # Placa (index 0)
                
                # Veículos não identificados: contagem DISTINTA de placas que são números inteiros
                placas_nao_identificadas = set()
                for registro in result:
                    placa = registro[0] if registro[0] else ''
                    if placa:  # Só processar se a placa existe
                        try:
                            # Se a placa pode ser convertida para int, é não identificado
                            int(placa)
                            placas_nao_identificadas.add(placa)  # Adiciona ao set (distintas)
                        except (ValueError, TypeError):
                            # Se não pode ser convertida para int, é identificado (string)
                            pass
                veiculos_nao_identificados = len(placas_nao_identificadas)
                
                # Placas distintas com motorista "NÃO IDENTIFICADO" - VERSÃO ROBUSTA
                placas_nao_identificado = set()
                
                # Debug detalhado sempre
                print(f"\n=== DEBUG VEÍCULOS SEM MOTORISTAS ===")
                print(f"Query executada: {query}")
                print(f"Total de registros retornados: {len(result)}")
                
                if not result:
                    placas_sem_motorista = 0
                    print("AVISO: Nenhum registro retornado da consulta")
                else:
                    # Mostrar estrutura dos dados sempre
                    print(f"Estrutura do primeiro registro ({len(result[0])} campos):")
                    for i, campo in enumerate(result[0]):
                        print(f"  [{i}]: {repr(campo)} (tipo: {type(campo)})")
                    
                    # Estratégia dupla: busca específica + busca geral
                    motorista_ras_index = None
                    
                    # ETAPA 1: Buscar explicitamente por motoristaRAS em todos os registros
                    print("\nETAPA 1: Buscando campo motoristaRAS...")
                    indices_com_nao_identificado = {}
                    
                    for idx in range(len(result[0])):
                        count_nao_ident = 0
                        for registro in result:
                            if len(registro) > idx and registro[idx] == 'NÃO IDENTIFICADO':
                                count_nao_ident += 1
                        if count_nao_ident > 0:
                            indices_com_nao_identificado[idx] = count_nao_ident
                            print(f"  Índice {idx}: {count_nao_ident} ocorrências de 'NÃO IDENTIFICADO'")
                    
                    # Escolher o índice com mais ocorrências (provavelmente motoristaRAS)
                    if indices_com_nao_identificado:
                        motorista_ras_index = max(indices_com_nao_identificado.items(), key=lambda x: x[1])[0]
                        print(f"  Selecionado índice {motorista_ras_index} (maior número de ocorrências: {indices_com_nao_identificado[motorista_ras_index]})")
                    
                    # ETAPA 2: Contar placas distintas
                    if motorista_ras_index is not None:
                        print(f"\nETAPA 2: Contando placas com motoristaRAS[{motorista_ras_index}] = 'NÃO IDENTIFICADO'...")
                        
                        # Contar e listar algumas placas para debug
                        placas_encontradas = []
                        for registro in result:
                            placa = registro[0] if registro[0] else ''
                            motorista_ras = registro[motorista_ras_index] if len(registro) > motorista_ras_index else ''
                            
                            if placa and motorista_ras == 'NÃO IDENTIFICADO':
                                placas_nao_identificado.add(placa)
                                if len(placas_encontradas) < 5:  # Mostrar apenas as primeiras 5
                                    placas_encontradas.append(placa)
                        
                        placas_sem_motorista = len(placas_nao_identificado)
                        print(f"  Placas encontradas (primeiras 5): {placas_encontradas}")
                        print(f"  Total de placas DISTINTAS: {placas_sem_motorista}")
                        
                        # Validação cruzada com consulta SQL direta
                        try:
                            validacao_query = f"SELECT COUNT(DISTINCT placa) FROM vw_consolidado WHERE convert(date, data) BETWEEN '{da_str}' AND '{df_str}' AND motoristaRAS = 'NÃO IDENTIFICADO'"
                            validacao_result = cf.getAll(validacao_query)
                            if validacao_result and validacao_result[0]:
                                valor_sql_direto = validacao_result[0][0]
                                print(f"  VALIDAÇÃO SQL DIRETA: {valor_sql_direto}")
                                if placas_sem_motorista != valor_sql_direto:
                                    print(f"  ⚠️  INCONSISTÊNCIA: Python={placas_sem_motorista} vs SQL={valor_sql_direto}")
                                else:
                                    print(f"  ✅ CONSISTENTE: Python={placas_sem_motorista} = SQL={valor_sql_direto}")
                        except Exception as e:
                            print(f"  Erro na validação SQL: {e}")
                            
                    else:
                        placas_sem_motorista = 0
                        print("  ERRO: Não foi possível identificar o campo motoristaRAS")
                        
                        # Se não encontrou motoristaRAS, fazer busca geral
                        print("\nETAPA 3: Busca geral por 'NÃO IDENTIFICADO' em todos os campos...")
                        for registro in result:
                            placa = registro[0] if registro[0] else ''
                            for campo in registro:
                                if campo == 'NÃO IDENTIFICADO':
                                    placas_nao_identificado.add(placa)
                                    break
                        placas_sem_motorista = len(placas_nao_identificado)
                        print(f"  Total com busca geral: {placas_sem_motorista}")
                
                print(f"RESULTADO FINAL: {placas_sem_motorista} veículos sem motoristas")
                print("=== FIM DEBUG ===\n")
                
                return render(request, 'trucks/controleJornada.html', {
                    'sqlConnect': result, 
                    'form': form,
                    'tJornada': totais[0],
                    'paradoLigado': totais[1],
                    'veiMovimento': totais[2],
                    'horarioAlmoco': totais[3],
                    'tempoEspera': totais[4],
                    'tempoDescanso': totais[5],
                    'tempoNoturno': totais[6],
                    'extrasDiurnas': totais[7],
                    'extraNoturno': totais[8],
                    'total_placas_distintas': total_placas_distintas,
                    'veiculos_nao_identificados': veiculos_nao_identificados,
                    'placas_sem_motorista': placas_sem_motorista,
                    'result_placa': placas,
                    'result_motorista': motoristas,
                })
            except Exception as e:
                messages.error(request, f"Erro ao processar busca: {str(e)}")
                form = JornadaFilterForm(initial=initial_data)
    else:
        form = JornadaFilterForm(initial=initial_data)
    
    return render(request, 'trucks/controleJornada.html', {
        'form': form, 
        'result_placa': placas, 
        'result_motorista': motoristas
    })


def procHoras(tabela):
    """Função para processar horas dos dados de jornada"""
    paradoLigado = 0
    veiMovimento = 0
    tempoNoturno = 0
    horarioAlmoco = 0
    extraNoturno = 0
    tempoEspera = 0
    tempoJornada = 0
    extrasDiurnas = 0
    tempoDescaso = 0

    for i in tabela:
        tempoJornada = tempoJornada + int(convertSegundo(i[8]))
        paradoLigado = paradoLigado + int(convertSegundo(i[9]))
        veiMovimento = veiMovimento + int(convertSegundo(i[10]))
        horarioAlmoco = horarioAlmoco + int(convertSegundo(i[11]))
        tempoEspera = tempoEspera + int(convertSegundo(i[12]))
        tempoDescaso = tempoDescaso + int(convertSegundo(i[13]))
        tempoNoturno = tempoNoturno + int(convertSegundo(i[16]))
        extrasDiurnas = extrasDiurnas + int(convertSegundo(i[17]))
        extraNoturno = extraNoturno + int(convertSegundo(i[18]))
    
    listFormatada = horasFormatada(
        [tempoJornada, paradoLigado, veiMovimento, horarioAlmoco, tempoEspera, tempoDescaso, tempoNoturno,
         extrasDiurnas, extraNoturno])

    return listFormatada


def convertSegundo(str):
    """Converte string de hora para segundos"""
    str2 = str
    if str == None:
        str2 = '00:00:00'
    horasSegundos = int(str2[0:2]) * 3600
    minutosSegundos = int(str2[3:5]) * 60
    segundos = int(str2[6:9])

    total = horasSegundos + minutosSegundos + segundos
    return total


def horasFormatada(*args):
    """Formata segundos de volta para formato de horas"""
    list = []
    for i in range(9):
        horas = str(int(args[0][i] / 3600))
        minutos = ('0' + str(int((args[0][i] / 60) % 60)))[-2:3]
        segundos = ('0' + str((args[0][i] % 3600) % 60))[-2:3]
        tempo = f"{horas}:{minutos}:{segundos}"
        list.append(tempo)
        i = i + 1
    return list

class ControleJornadaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View para controle de jornadas de motoristas.
    """
    permission_required = 'app.acessar_jornada'
    template_name = 'trucks/controleJornada.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Criar instância do formulário
        form = JornadaFilterForm(self.request.GET or None)
        context['form'] = form
        
        # Obter dados básicos para autocomplete
        try:
            # Buscar placas e motoristas disponíveis (simulando a estrutura original)
            context['result_placa'] = TrucksVeiculos.objects.values_list('placa', flat=True).distinct().order_by('placa')
            context['result_motorista'] = TrucksVeiculos.objects.exclude(mot__isnull=True).exclude(mot='').values_list('mot', flat=True).distinct().order_by('mot')
        except Exception as e:
            logging.error(f'Erro ao carregar dados básicos: {str(e)}')
            context['result_placa'] = []
            context['result_motorista'] = []
        
        # Inicializar dados vazios para totalizadores
        context.update({
            'sqlConnect': [],
            'tJornada': '--:--',
            'paradoLigado': '--:--',
            'veiMovimento': '--:--',
            'horarioAlmoco': '--:--',
            'tempoEspera': '--:--',
            'tempoDescanso': '--:--',
            'tempoNoturno': '--:--',
            'extrasDiurnas': '--:--',
            'extraNoturno': '--:--',
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Processar formulário de busca de jornadas.
        """
        form = JornadaFilterForm(request.POST)
        context = self.get_context_data()
        
        if form.is_valid():
            # Extrair dados do formulário
            nome_placa = form.cleaned_data.get('nome_placa', '')
            data_inicial = form.cleaned_data.get('data_inicial')
            data_final = form.cleaned_data.get('data_final')
            selecao = form.cleaned_data.get('selecao', 'todos')
            
            try:
                # Implementar lógica de busca real
                context['form'] = form
                
                # Log para debug
                logging.info(f'Busca de jornadas: {selecao} - {nome_placa} - {data_inicial} a {data_final}')
                
                # Buscar dados reais usando a lógica original
                dados_busca = self.executar_busca_jornadas(nome_placa, data_inicial, data_final, selecao)
                
                # Atualizar contexto com os dados encontrados
                context.update(dados_busca)
                
                # Mensagem de sucesso
                total_encontrados = len(dados_busca.get('sqlConnect', []))
                if total_encontrados > 0:
                    messages.success(request, f"Busca concluída: {total_encontrados} registros encontrados.")
                else:
                    messages.info(request, "Nenhum registro encontrado para os filtros especificados.")
                
            except Exception as e:
                logging.error(f'Erro na busca de jornadas: {str(e)}')
                messages.error(request, f"Erro ao processar a busca: {str(e)}")
        
        return self.render_to_response(context)
    
    def executar_busca_jornadas(self, nome_placa, data_inicial, data_final, selecao):
        """
        Executa busca de jornadas mantendo o formato original esperado pelo template.
        """
        from django.db.models import Q
        from datetime import datetime, timedelta
        
        # Definir datas padrão se não fornecidas
        if not data_final:
            data_final = datetime.now().date()
        if not data_inicial:
            data_inicial = data_final - timedelta(days=7)  # Últimos 7 dias por padrão
        
        # Construir query base
        query = Q()
        
        # Filtrar por data
        if data_inicial and data_final:
            query &= Q(dt__date__gte=data_inicial) & Q(dt__date__lte=data_final)
        
        # Filtrar por placa/motorista
        if nome_placa:
            if selecao == 'placa':
                # Buscar pela placa através da relação com TrucksVeiculos
                veiculos_placa = TrucksVeiculos.objects.filter(
                    placa__icontains=nome_placa
                ).values_list('veiid', flat=True)
                query &= Q(veiid__in=veiculos_placa)
            elif selecao == 'motorista':
                # Buscar pelo motorista
                query &= Q(mot__icontains=nome_placa)
            else:  # 'todos'
                # Buscar tanto por placa quanto por motorista
                veiculos_placa = TrucksVeiculos.objects.filter(
                    placa__icontains=nome_placa
                ).values_list('veiid', flat=True)
                query &= (Q(veiid__in=veiculos_placa) | Q(mot__icontains=nome_placa))
        
        # Buscar registros de posição
        registros = TrucksPosicaoCarroApi.objects.filter(query).order_by('-dt')[:50]
        
        # Buscar informações de veículos relacionados
        veiculos_relacionados = {}
        for registro in registros:
            if registro.veiid and registro.veiid not in veiculos_relacionados:
                try:
                    veiculo = TrucksVeiculos.objects.get(veiid=registro.veiid)
                    veiculos_relacionados[registro.veiid] = {
                        'placa': veiculo.placa,
                        'motorista': veiculo.mot
                    }
                except TrucksVeiculos.DoesNotExist:
                    veiculos_relacionados[registro.veiid] = {
                        'placa': 'N/A',
                        'motorista': 'N/A'
                    }
        
        # Simular dados de jornada no formato esperado pelo template original
        sql_connect_data = []
        for registro in registros:
            veiculo_info = veiculos_relacionados.get(registro.veiid, {'placa': 'N/A', 'motorista': 'N/A'})
            
            # Criar objeto simulado com as propriedades esperadas pelo template
            class JornadaData:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            
            jornada_data = JornadaData(
                placa=veiculo_info['placa'],
                data=registro.dt.strftime('%d/%m/%Y') if registro.dt else 'N/A',
                motoristaRAS=veiculo_info['motorista'] or registro.mot or 'N/A',
                diaSemana=registro.dt.strftime('%A') if registro.dt else 'N/A',
                InicioJornada='08:00:00',  # Dados simulados para manter compatibilidade
                FimJornada='17:00:00',
                Jornada='09:00:00',
                ligadoParado='01:30:00',
                veiMovi='07:30:00',
                horaAlmoco='01:00:00',
                tempoEspera='00:30:00',
                tempoDescanso='00:15:00',
                estouroJornada='00:00:00',
                tempoNoturno='00:00:00',
                TempoExtra='00:00:00',
                tempoNoturnoExtra='00:00:00'
            )
            sql_connect_data.append(jornada_data)
        
        # Calcular totalizadores simulados
        total_jornada = len(sql_connect_data) * 9  # 9 horas por registro
        horas_jornada = f"{total_jornada // len(sql_connect_data) if sql_connect_data else 0}:00:00"
        
        return {
            'sqlConnect': sql_connect_data,
            'tJornada': horas_jornada,
            'paradoLigado': '01:30:00',
            'veiMovimento': '07:30:00',
            'horarioAlmoco': '01:00:00',
            'tempoEspera': '00:30:00',
            'tempoDescanso': '00:15:00',
            'tempoNoturno': '00:00:00',
            'extraNoturno': '00:00:00',
            'extrasDiurnas': '00:00:00'
        }

class DashboardJornadaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Dashboard para acompanhamento das importações de posições dos veículos.
    Mostra uma matriz com veículos nas linhas e dias nas colunas.
    """
    permission_required = 'app.acessar_jornada'
    template_name = 'trucks/dashboardJornada.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter parâmetros de filtro
        placa_filtro = self.request.GET.get('placa', '')
        data_inicial = self.request.GET.get('data_inicial', '')
        data_final = self.request.GET.get('data_final', '')
        
        # Configurar datas padrão (últimos 31 dias)
        if not data_inicial or not data_final:
            data_final_default = timezone.now().date()
            data_inicial_default = data_final_default - timedelta(days=30)
            data_inicial = data_inicial or data_inicial_default.strftime('%Y-%m-%d')
            data_final = data_final or data_final_default.strftime('%Y-%m-%d')
        
        # Converter strings para objetos de data
        try:
            data_inicial_obj = datetime.strptime(data_inicial, '%Y-%m-%d').date()
            data_final_obj = datetime.strptime(data_final, '%Y-%m-%d').date()
        except ValueError:
            # Se houver erro na conversão, usar padrão
            data_final_obj = timezone.now().date()
            data_inicial_obj = data_final_obj - timedelta(days=30)
            data_inicial = data_inicial_obj.strftime('%Y-%m-%d')
            data_final = data_final_obj.strftime('%Y-%m-%d')
        
        # Obter lista de veículos
        veiculos_query = TrucksVeiculos.objects.all()
        if placa_filtro:
            veiculos_query = veiculos_query.filter(placa__icontains=placa_filtro)
        
        veiculos = list(veiculos_query.order_by('placa'))
        
        # Gerar lista de dias no período
        dias = []
        current_date = data_inicial_obj
        while current_date <= data_final_obj:
            dias.append(current_date)
            current_date += timedelta(days=1)
        
        # Consultar dados de posições agrupados por veiid e data
        posicoes_data = TrucksPosicaoCarroApi.objects.filter(
            dt__date__gte=data_inicial_obj,
            dt__date__lte=data_final_obj
        )

        print(posicoes_data.query)  # Debug: imprimir a query SQL
        print('--------------------------------')
        
        # Se há filtro de placa, filtrar também as posições
        if placa_filtro:
            veiids_filtrados = [v.veiid for v in veiculos if v.veiid]
            posicoes_data = posicoes_data.filter(veiid__in=veiids_filtrados)
        
        # Agrupar por veiid e data, contando registros
        posicoes_agrupadas = (
            posicoes_data
            .annotate(data=Cast('dt', DateField()))
            .values('veiid', 'data')
            .annotate(count=Count('id'))
            .order_by('veiid', 'data')
        )
        
        # Criar matriz de dados
        matriz = defaultdict(lambda: defaultdict(int))
        for item in posicoes_agrupadas:
            matriz[item['veiid']][item['data']] = item['count']
        
        # Consultar dados de importação Excel para os mesmos critérios
        # Para usar quando TrucksPosicaoCarroApi tiver count = 0
        importacao_data = TrucksImportadosExcel.objects.filter(
            datahora__date__gte=data_inicial_obj,
            datahora__date__lte=data_final_obj
        ).values('placa', 'datahora')

        print(importacao_data)  # Debug: imprimir a query SQL
        print('--------------------------------')
        
        # Se há filtro de placa, aplicar também nos dados de importação
        if placa_filtro:
            importacao_data = importacao_data.filter(placa__icontains=placa_filtro)
        
        # Agrupar dados de importação por placa e data
        matriz_importacao = defaultdict(lambda: defaultdict(int))
        try:
            # Usar raw SQL para contornar problemas com managed=False
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT placa, CAST(dataHora AS DATE) as data_import, COUNT(*) as count_import
                    FROM trucks_ImportadosExcel 
                    WHERE CAST(dataHora AS DATE) BETWEEN %s AND %s
                    {} 
                    GROUP BY placa, CAST(dataHora AS DATE)
                    ORDER BY placa, data_import
                """.format("AND placa LIKE %s" if placa_filtro else ""), 
                [data_inicial_obj, data_final_obj] + ([f"%{placa_filtro}%"] if placa_filtro else []))
                
                for row in cursor.fetchall():
                    placa, data_import, count_import = row
                    # Encontrar veiid baseado na placa
                    veiculo_match = next((v for v in veiculos if v.placa == placa), None)
                    if veiculo_match and veiculo_match.veiid:
                        matriz_importacao[veiculo_match.veiid][data_import] = count_import
        except Exception as e:
            print(f"Erro ao consultar dados de importação: {e}")
            matriz_importacao = defaultdict(lambda: defaultdict(int))
        
        # Preparar dados para o template
        dados_matriz = []
        total_por_dia = defaultdict(int)
        
        for veiculo in veiculos:
            linha = {
                'veiculo': veiculo,
                'dias': []
            }
            total_veiculo = 0
            
            for dia in dias:
                count = matriz[veiculo.veiid].get(dia, 0) if veiculo.veiid else 0
                count_importacao = matriz_importacao[veiculo.veiid].get(dia, 0) if veiculo.veiid else 0
                
                # Se count principal é 0, usar dados de importação
                is_from_import = count == 0 and count_importacao > 0
                final_count = count if count > 0 else count_importacao
                
                linha['dias'].append({
                    'data': dia,
                    'count': final_count,
                    'is_from_import': is_from_import  # Flag para identificar origem dos dados
                })
                total_veiculo += final_count
                total_por_dia[dia] += final_count
            
            linha['total'] = total_veiculo
            
            # Só adicionar veículos que têm pelo menos 1 registro no período
            if total_veiculo > 0:
                dados_matriz.append(linha)
        
        # Calcular totais
        total_geral = sum(total_por_dia.values())
        total_veiculos = len(dados_matriz)  # Apenas veículos com registros
        
        # Calcular métricas
        dias_periodo = (data_final_obj - data_inicial_obj).days + 1
        media_registros_dia = total_geral / dias_periodo if dias_periodo > 0 else 0
        media_registros_veiculo = total_geral / total_veiculos if total_veiculos > 0 else 0
        
        # Calcular dias com total zerado
        dias_zerados = 0
        for dia in dias:
            if total_por_dia.get(dia, 0) == 0:
                dias_zerados += 1
        
        context.update({
            'dados_matriz': dados_matriz,
            'dias': dias,
            'total_por_dia': total_por_dia,
            'total_geral': total_geral,
            'total_veiculos': total_veiculos,
            'dias_periodo': dias_periodo,
            'dias_zerados': dias_zerados,
            'media_registros_dia': round(media_registros_dia, 1),
            'media_registros_veiculo': round(media_registros_veiculo, 1),
            'placa_filtro': placa_filtro,
            'data_inicial': data_inicial,
            'data_final': data_final,
            'todas_placas': TrucksVeiculos.objects.values_list('placa', flat=True).order_by('placa')
        })
        
        return context


class ImportacaoExcelView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View para importação de arquivos Excel para o modelo TrucksImportadosExcel.
    Permite selecionar múltiplos arquivos Excel e processar cada um individualmente.
    """
    permission_required = 'app.acessar_jornada'
    template_name = 'trucks/importacaoExcel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Não carregamos estatísticas gerais, apenas resultados da importação se houver
        return context
    
    def post(self, request, *args, **kwargs):
        arquivos_excel = request.FILES.getlist('excel_files')
        
        if not arquivos_excel:
            messages.error(request, 'Por favor, selecione pelo menos um arquivo Excel.')
            return self.get(request, *args, **kwargs)
        
        try:
            resultados = self.processar_arquivos_excel(arquivos_excel, request.user)
            
            # Adicionar resultados ao contexto para exibição
            context = self.get_context_data()
            context['import_results'] = resultados
            
            if resultados['total_arquivos'] > 0:
                if resultados['arquivos_processados'] == resultados['total_arquivos']:
                    messages.success(
                        request, 
                        f'Importação concluída com sucesso! {resultados["total_arquivos"]} arquivos processados, '
                        f'{resultados["total_registros"]} registros importados.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Importação parcial: {resultados["arquivos_processados"]} de {resultados["total_arquivos"]} '
                        f'arquivos processados com sucesso. {resultados["total_registros"]} registros importados.'
                    )
                
                if resultados['erros']:
                    for erro in resultados['erros']:
                        messages.error(request, erro)
            else:
                messages.error(request, 'Nenhum arquivo pôde ser processado.')
        
        except Exception as e:
            logging.error(f'Erro na importação Excel: {str(e)}')
            messages.error(request, f'Erro durante a importação: {str(e)}')
            context = self.get_context_data()
        
        return self.render_to_response(context)
    
    def processar_arquivos_excel(self, arquivos_excel, usuario):
        """
        Processa uma lista de arquivos Excel enviados via upload.
        """
        resultados = {
            'total_arquivos': len(arquivos_excel),
            'arquivos_processados': 0,
            'total_registros': 0,
            'erros': [],
            'detalhes_arquivos': []
        }
        
        for arquivo in arquivos_excel:
            detalhes_arquivo = {
                'nome': arquivo.name,
                'sucesso': False,
                'registros': 0,
                'erro': None
            }
            
            try:
                # Salvar arquivo temporariamente
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                    for chunk in arquivo.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                try:
                    # Processar arquivo
                    registros_importados = self.processar_arquivo_excel_uploaded(temp_file_path, arquivo.name)
                    
                    detalhes_arquivo['sucesso'] = True
                    detalhes_arquivo['registros'] = registros_importados
                    
                    resultados['arquivos_processados'] += 1
                    resultados['total_registros'] += registros_importados
                    
                    logging.info(f'Arquivo {arquivo.name}: {registros_importados} registros importados')
                    
                finally:
                    # Limpar arquivo temporário
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                    
            except Exception as e:
                detalhes_arquivo['erro'] = str(e)
                resultados['erros'].append(f'{arquivo.name}: {str(e)}')
                logging.error(f'Erro ao processar {arquivo.name}: {str(e)}')
            
            resultados['detalhes_arquivos'].append(detalhes_arquivo)
        
        return resultados
    
    def processar_arquivo_excel_uploaded(self, caminho_arquivo, nome_original):
        """
        Processa um arquivo Excel enviado via upload usando o código de importação específico.
        """
        try:
            # Importar dados usando o método específico do sistema
            registros_importados = self.importar_dados_excel(caminho_arquivo, nome_original)
            
            logging.info(f'Arquivo {nome_original}: {registros_importados} registros importados')
            return registros_importados
            
        except Exception as e:
            logging.error(f'Erro ao processar arquivo {nome_original}: {str(e)}')
            raise Exception(f'Erro no arquivo {nome_original}: {str(e)}')
    
    
    def importar_dados_excel(self, caminho_arquivo, nome_original):
        """
        Importa dados de arquivo Excel usando a lógica específica do sistema.
        Inclui verificação e exclusão de dados existentes para a mesma placa e intervalo de datas.
        Baseado no código original do sistema.
        """
        
        
        try:
            # Abrir workbook usando xlrd
            wb = open_workbook(caminho_arquivo)
            ws = wb.sheet_by_index(0)
            
            # Identificar colunas do cabeçalho (linha 0)
            listColCab = []
            countColCab = 0
            
            for i in ws.row(0):
                if i.value != '':
                    listColCab.append(countColCab)
                countColCab += 1
            
            # Identificar colunas do corpo (linha 2)
            listColCorpo = []
            countColCorpo = 0
            
            for i in ws.row(2):
                if i.value != '' and i.value != 'Ponto de Referência':
                    listColCorpo.append(countColCorpo)
                if len(listColCorpo) > 10:
                    break
                countColCorpo += 1
            

            print(listColCab)
            print(listColCorpo)
            # Extrair cabeçalho (linha 1)
            listCab = []
            for i in listColCab:
                valor_cabecalho = str(ws.cell(1, i).value)[0:30]
                listCab.append(valor_cabecalho)

            print('--------------------------------')
            print(listCab[0])
            print('--------------------------------')
            
            # Extrair dados do corpo (a partir da linha 3)
            listCorpo = []
            placas_encontradas = set()
            datas_encontradas = []
            
            for r in range(ws.nrows - 3):
                dados = []
                for j in listColCorpo:
                    if j == 1:  # Coluna de data
                        try:
                            # Converter data do Excel
                            a1_as_datetime = xldate.xldate_as_datetime(ws.cell(r + 3, j).value, wb.datemode)
                            dados.append(a1_as_datetime)
                            datas_encontradas.append(a1_as_datetime)
                        except:
                            # Se falhar, usar valor original
                            dados.append(ws.cell(r + 3, j).value)
                            if ws.cell(r + 3, j).value:
                                datas_encontradas.append(ws.cell(r + 3, j).value)
                    else:
                        dados.append(ws.cell(r + 3, j).value)
                
                # Identificar placa (primeiro campo do cabeçalho + primeiro campo dos dados)
                if len(listCab) > 0 and len(dados) > 0:
                    placa = listCab[0]
                    
                # Combinar cabeçalho + dados + metadados (data import, arquivo, null)
                registro_completo = listCab + dados + [datetime.today(), nome_original, None]
                listCorpo.append(registro_completo)
            
            # Antes de inserir, verificar e excluir dados existentes
            if placa and datas_encontradas:
                self.limpar_dados_existentes(placa, datas_encontradas, nome_original)
            
            # Inserir no banco usando connectionFactory
            if listCorpo:
                sql = 'insert into trucks_ImportadosExcel values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
                cf.insertLote(sql, listCorpo)
                
                logging.info(f'Processado arquivo {nome_original}: {len(listCorpo)} registros inseridos')
                return len(listCorpo)
            else:
                logging.warning(f'Arquivo {nome_original} não contém dados válidos')
                return 0
                
        except Exception as e:
            logging.error(f'Erro ao importar dados do arquivo {nome_original}: {str(e)}')
            raise Exception(f'Erro na importação: {str(e)}')

    def limpar_dados_existentes(self, placa_encontrada, datas_encontradas, nome_arquivo):
        """
        Verifica e exclui dados existentes para as placas e intervalo de datas encontrados no arquivo.
        """
        
        try:
            if not placa_encontrada or not datas_encontradas:
                logging.info('Nenhuma placa ou data encontrada para limpeza')
                return
            
            # Converter datas para datetime se necessário e encontrar intervalo
            datas_datetime = []
            for data in datas_encontradas:
                if isinstance(data, datetime):
                    datas_datetime.append(data)
                elif hasattr(data, 'strftime'):  # Se for date
                    datas_datetime.append(datetime.combine(data, datetime.min.time()))
                else:
                    try:
                        # Tentar converter string para datetime
                        if isinstance(data, str):
                            data_convertida = datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
                            datas_datetime.append(data_convertida)
                    except:
                        continue
            
            if not datas_datetime:
                logging.warning('Nenhuma data válida encontrada para limpeza')
                return
            
            # Determinar intervalo de datas
            data_inicial = min(datas_datetime)
            data_final = max(datas_datetime)

                
            # print(placas_encontradas)
            print(nome_arquivo)
            print('--------------------------------')
            print(placa_encontrada)

            # Tirar 3 horas devido ao timezone de data_inicial e data_final
            data_inicial = data_inicial - timedelta(hours=3)
            data_final = data_final - timedelta(hours=3)
            print(data_inicial)
            print(data_final)
            print('--------------------------------')
            logging.info(f'Limpando dados existentes para placas: {placa_encontrada}')
            logging.info(f'Intervalo de datas: {data_inicial.strftime("%Y-%m-%d %H:%M:%S")} até {data_final.strftime("%Y-%m-%d %H:%M:%S")}')
            
                        
            # Contar registros existentes
            try:
                count_existentes  = TrucksImportadosExcel.objects.filter(placa=placa_encontrada, datahora__range=[data_inicial, data_final]).count()
                print('--------------------------------')
                print(count_existentes)
                print('--------------------------------')
            except:
                count_existentes = 0
            
            if count_existentes > 0:
                # Construir query de exclusão
                print('--------------------------------')
                print('Excluindo registros existentes')
                print('--------------------------------')
                resultado_delete = TrucksImportadosExcel.objects.filter(placa=placa_encontrada, datahora__range=[data_inicial, data_final]).delete()

                
                if resultado_delete:
                    logging.info(f'Excluídos {count_existentes} registros existentes para as placas {placa_encontrada} no intervalo especificado')
                else:
                    logging.error('Falha ao excluir registros existentes')
            else:
                logging.info('Nenhum registro existente encontrado para exclusão')
                
        except Exception as e:
            logging.error(f'Erro ao limpar dados existentes: {str(e)}')
            # Não fazer raise aqui para não interromper a importação
            # apenas loggar o erro e continuar


    
@login_required
def processar_arquivo_individual(request):
    """
    View para processar um arquivo individual e retornar o progresso.
    """
    if request.method == 'POST':
        try:
            # Recuperar arquivo enviado
            arquivo = request.FILES.get('arquivo')
            index_arquivo = int(request.POST.get('index', 0))
            total_arquivos = int(request.POST.get('total', 1))
            
            if not arquivo:
                return JsonResponse({
                    'success': False,
                    'error': 'Arquivo não encontrado'
                })
            
            # Salvar arquivo temporariamente
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                for chunk in arquivo.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            try:
                # Usar a instância da view para processar o arquivo

                view_instance = ImportacaoExcelView()
                view_instance.request = request  # Definir request se necessário
                registros_importados = view_instance.importar_dados_excel(temp_file_path, arquivo.name)
                
                print(registros_importados)
                # Calcular progresso
                progresso_percentual = ((index_arquivo + 1) / total_arquivos) * 100
                
                return JsonResponse({
                    'success': True,
                    'arquivo_nome': arquivo.name,
                    'registros_importados': registros_importados,
                    'index_atual': index_arquivo + 1,
                    'total_arquivos': total_arquivos,
                    'progresso_percentual': round(progresso_percentual, 1),
                    'concluido': (index_arquivo + 1) >= total_arquivos
                })
                
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logging.error(f'Erro ao processar arquivo individual: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': str(e),
                'arquivo_nome': request.FILES.get('arquivo', {}).name if request.FILES.get('arquivo') else 'Desconhecido'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


class ProcessamentoExcelView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View para processamento de dados Excel através de procedure no banco
    """
    template_name = 'trucks/processamentoExcel.html'
    permission_required = 'app.acessar_jornada'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dados padrão para o template
        context.update({
            'page_title': 'Processamento Excel',
            'total_processados': 0,
            'tempo_processamento': 0,
            'resultado_processamento': None,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Processar dados através de procedure"""
        try:
            # Obter dados do formulário
            data_inicial = request.POST.get('data_inicial')
            data_final = request.POST.get('data_final')
            tipo_processamento = request.POST.get('tipo_processamento', 'todos')
            placa_especifica = request.POST.get('placa_especifica', '')
            
            # Validar dados obrigatórios
            if not data_inicial or not data_final:
                messages.error(request, 'Data inicial e final são obrigatórias')
                return self.get(request)
            
            # Validar se placa foi informada quando tipo é "por_placa"
            if tipo_processamento == 'por_placa' and not placa_especifica:
                messages.error(request, 'Placa deve ser informada quando selecionado "Por Placa"')
                return self.get(request)
            
            # Converter datas
            try:
                from datetime import datetime
                data_inicial_obj = datetime.strptime(data_inicial, '%Y-%m-%d').date()
                data_final_obj = datetime.strptime(data_final, '%Y-%m-%d').date()
                
                if data_inicial_obj > data_final_obj:
                    messages.error(request, 'Data inicial deve ser menor ou igual à data final')
                    return self.get(request)
                    
            except ValueError:
                messages.error(request, 'Formato de data inválido')
                return self.get(request)
            
            # Executar procedure no banco
            resultado = self.executar_procedure(data_inicial_obj, data_final_obj, tipo_processamento, placa_especifica)
            
            if resultado['success']:
                messages.success(request, f'Processamento concluído com sucesso! {resultado["message"]}')
                
                # Atualizar contexto com resultado
                context = self.get_context_data()
                context.update({
                    'total_processados': resultado.get('total_processados', 0),
                    'tempo_processamento': resultado.get('tempo_processamento', 0),
                    'resultado_processamento': resultado,
                    'data_inicial': data_inicial,
                    'data_final': data_final,
                    'tipo_processamento': tipo_processamento,
                    'placa_especifica': placa_especifica,
                })
                
                return render(request, self.template_name, context)
            else:
                messages.error(request, f'Erro no processamento: {resultado["error"]}')
                return self.get(request)
                
        except Exception as e:
            messages.error(request, f'Erro interno: {str(e)}')
            return self.get(request)
    
    def executar_procedure(self, data_inicial, data_final, tipo_processamento, placa_especifica):
        """
        Executar procedure no banco de dados
        """
        from django.db import connection
        import time
        
        try:
            inicio = time.time()
            
            with connection.cursor() as cursor:
                # Parâmetros da procedure
                if tipo_processamento == 'por_placa' and placa_especifica:
                    # Procedure para placa específica
                    sql_comando = """
                        EXEC SP_PROCESSAMENTO_EXCEL_DATA_GERAL_PLACA 
                            @DTINI = %s, 
                            @DTFIM = %s, 
                            @PLACA = %s
                    """
                    parametros = [data_inicial, data_final, placa_especifica]
                    print(f"DEBUG: Executando procedure para placa: {placa_especifica}")
                    print(f"DEBUG: Parâmetros: {parametros}")
                    
                    cursor.execute(sql_comando, parametros)
                else:
                    # Procedure para todos
                    sql_comando = """
                        EXEC SP_PROCESSAMENTO_EXCEL_DATA_GERAL 
                            @DTINI = %s, 
                            @DTFIM = %s
                    """
                    parametros = [data_inicial, data_final]
                    print(f"DEBUG: Executando procedure para todos")
                    print(f"DEBUG: Parâmetros: {parametros}")
                    
                    cursor.execute(sql_comando, parametros)
                
                print("DEBUG: Procedure executada com sucesso")
                
                # Obter resultado da procedure (número de placas processadas)
                total_processados = 0
                try:
                    # A procedure retorna o número de placas processadas
                    resultado_raw = cursor.fetchone()
                    print(f"DEBUG: Resultado raw da procedure: {resultado_raw}")
                    
                    if resultado_raw and resultado_raw[0] is not None:
                        # Pegar o primeiro valor retornado (número de placas)
                        total_processados = int(resultado_raw[0])
                        print(f"DEBUG: Placas processadas: {total_processados}")
                    else:
                        print("DEBUG: Procedure não retornou valor ou retornou NULL")
                        total_processados = 0
                        
                except Exception as fetch_error:
                    print(f"DEBUG: Erro ao capturar resultado: {fetch_error}")
                    total_processados = 0
                
            fim = time.time()
            tempo_processamento = round(fim - inicio, 2)
            
            return {
                'success': True,
                'message': f'Processamento concluído! {total_processados} placa(s) processada(s) em {tempo_processamento}s',
                'total_processados': total_processados,
                'tempo_processamento': tempo_processamento,
                'data_inicial': data_inicial,
                'data_final': data_final,
                'tipo_processamento': tipo_processamento,
                'placa_especifica': placa_especifica if tipo_processamento == 'por_placa' else None
            }
            
        except Exception as e:
            print(f"DEBUG: Erro na execução da procedure: {str(e)}")
            print(f"DEBUG: Tipo do erro: {type(e)}")
            
            return {
                'success': False,
                'error': f'Erro na execução da procedure: {str(e)}',
                'total_processados': 0,
                'tempo_processamento': 0
            }

    