import json
from datetime import datetime, timedelta, date
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import qrcode
import io
from .forms import CamposForm, OrdemServicoForm
from copral import connectionFactory as cf
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .processamento  import inserir_dados, processar, deletar_dados, id_carro

from .models import OrdemServico
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView
from .analitico import procedure, tempEventos

@login_required
def home(request):
    return render(request, 'home.html')


class cartao_visita(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Formulário de vCard e geração de QRCode com a lib qrcode.
    """
    permission_required = 'app.acessar_rh'
    template_name = 'app/cartao_visita.html'
    

    def post(self, request, *args, **kwargs):
        nome = request.POST.get('nome', '')
        sobrenome = request.POST.get('sobrenome', '')
        empresa = request.POST.get('empresa', '')
        titulo = request.POST.get('titulo', '')
        telefone = request.POST.get('telefone', '')
        email = request.POST.get('email', '')
        endereco = request.POST.get('endereco', '')
        website = request.POST.get('website', '')

        # Montar vCard no padrão v3.0
        vcard = (
            'BEGIN:VCARD\n'
            'VERSION:3.0\n'
            f'N:{sobrenome};{nome};;;\n'
            f'FN:{nome} {sobrenome}\n'
            f'ORG:{empresa}\n' if empresa else ''
        )
        if titulo:
            vcard += f'TITLE:{titulo}\n'
        if telefone:
            vcard += f'TEL;TYPE=CELL:{telefone}\n'
        if email:
            vcard += f'EMAIL;TYPE=INTERNET:{email}\n'
        if endereco:
            vcard += f'ADR;TYPE=WORK:;;{endereco};;;;\n'
        if website:
            vcard += f'URL:{website}\n'
        vcard += 'END:VCARD'

        try:
            # Gerar QRCode em memória
            img = qrcode.make(vcard)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            
            # Converter para base64 para envio via JSON
            import base64
            qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return JsonResponse({
                'success': True,
                'qr_code': qr_base64,
                'message': 'QR Code gerado com sucesso!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

        return render(request, self.template_name)

@login_required
def controleJornada(request):
    query_motorista = 'select distinct motoristaRAS from vw_consolidado'
    query_placa = 'select distinct placa from vw_consolidado'
    placas = cf.getAll(query_placa)
    motoristas = cf.getAll(query_motorista)

    form = CamposForm(request.POST)
    if request.method == 'POST':
        print(request.POST.get('nome_placa'))
        print(request.POST.get('data_inicial'))
        print(request.POST.get('data_final'))
        print(request.POST.get('selecao'))
        np = request.POST.get('nome_placa')
        da = request.POST.get('data_inicial')
        df = request.POST.get('data_final')
        slc = request.POST.get('selecao')

        global query, sql
        sql = f"set dateformat dmy select * from vw_consolidado where convert(date, data)  between '{da}' and '{df}'"
        query_placa = 'select distinct placa from vw_consolidado'
        query_motorista = 'select distinct motoristaRAS from vw_consolidado'
        
        if slc == 'todos':
            query = f"{sql}"
        elif slc == 'placa':
            query = f"{sql} and placa = '{np}'"
            print(query)
        elif slc == 'motorista':
            query = f"{sql} and motoristaRas = '{np}' "
        result = cf.getAll(query)
        if len(result) == 0:
            messages.info(request, "Ops... Nenhum registro encontrado :(")

        totais = procHoras(result)
        return render(request, 'app/controleJornada.html', {'sqlConnect': result, 'form': form,
                                              'tJornada': totais[0],
                                              'paradoLigado': totais[1],
                                              'veiMovimento': totais[2],
                                              'horarioAlmoco': totais[3],
                                              'tempoEspera': totais[4],
                                              'tempoDescanso': totais[5],
                                              'tempoNoturno': totais[6],
                                              'extrasDiurnas': totais[7],
                                              'extraNoturno': totais[8],
                                              'result_placa': placas,
                                              'result_motorista': motoristas,
                                              })
    else:
        return render(request, 'app/controleJornada.html', {'form': form, 'result_placa': placas, 'result_motorista': motoristas})


@login_required
def painel(request):
    return render(request, 'app/painel.html')


def procHoras(tabela):
    global paradoLigado

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
    print('erro aqui \n', str)
    str2 = str
    if str == None:
        str2 = '00:00:00'
    horasSegundos = int(str2[0:2]) * 3600
    minutosSegundos = int(str2[3:5]) * 60
    segundos = int(str2[6:9])

    total = horasSegundos + minutosSegundos + segundos
    return total


def horasFormatada(*args):
    list = []
    for i in range(9):
        horas = str(int(args[0][i] / 3600))
        minutos = ('0' + str(int((args[0][i] / 60) % 60)))[-2:3]
        segundos = ('0' + str((args[0][i] % 3600) % 60))[-2:3]
        tempo = f"{horas}:{minutos}:{segundos}"
        list.append(tempo)
        i = i + 1
    return list

@login_required
def relatorio(request):
    template_name = 'app/relatorio.html'
    query_processamento_analitico = f"""
        select * from processamentoAnalitico order by inicio
    """
    dados_pa = cf.getAll(query_processamento_analitico)
    context = {
        'dados': dados_pa,
    }

    if request.method == 'POST':
        v = True
        a = True
        te = True

        variacao = timedelta(days=0, hours=0, minutes=0, seconds=0)
        periodo_inicial = request.POST.get('data_inicial')
        periodo_final = request.POST.get('data_final')
        placa_carro = request.POST.get('placa')
        
        print(f"ID Placa - {placa_carro}")
        deletar_dados()
        processar(placa=placa_carro, dt_inicial=periodo_inicial, dt_final=periodo_final)
        p = id_carro(placa=placa_carro)
        
        query_resumos_diarios = f"select data, placa, horaAlmoco, tempoEspera, tempoDescanso from ResumoDiario where placa = '{placa_carro}' and data >= '{periodo_inicial}' and data <= '{periodo_final}'"
        dados_resumos_diarios = cf.getAll(query_resumos_diarios)
        query_pe = f"""
                    SELECT * from processamentoEventos where placa = '{p}' and data between '{periodo_inicial}' and '{periodo_final}' order by inicio
                    """
        dados = cf.getAll(query_pe)
        query_resumo = f"select * from ResumoDiario where placa = '{placa_carro}' and data = '{periodo_inicial}'"
        dados_resumo = cf.getAll(query_resumo)
        tempo_processado = timedelta(days=0, hours=0, minutes=0, seconds=0)
        
        evento = 'ESPERA'
        try:
            for r in dados_resumo:
                dt = r[2]
                dt_dia = dt.day
                dt_mes = dt.month
                dt_ano = dt.year
                dt_hr_ini_almoco = datetime(dt_ano, dt_mes, dt_dia, 11, 30, 0, 0)
                dt_hr_fim_almoco = datetime(dt_ano, dt_mes, dt_dia, 14, 00, 0, 0)

                inicio_jornada = r[6]
                hora_ij = int(r[6][0:2])
                minuto_ij = int(r[6][3:5])
                segundo_ij = int(r[6][6:8])
                ini_jornada = datetime(
                    day=dt_dia,
                    month=dt_mes,
                    year=dt_ano,
                    hour=hora_ij,
                    minute=minuto_ij,
                    second=segundo_ij
                )
                hora_almoco = datetime(
                    year=dt_ano,
                    month=dt_mes,
                    day=dt_dia,
                    hour=12,
                    minute=0,
                    second=0
                )

                tempo_inicio_jornada = r[6]
                hora_ij = int(r[6][0:2])
                minuto_ij = int(r[6][3:5])
                segundo_ij = int(r[6][6:8])
                tp_ini_jornada = timedelta(
                    days=0,
                    hours=hora_ij,
                    minutes=minuto_ij,
                    seconds=segundo_ij
                )

                resumo_almoco = r[12]
                hora_ra = int(r[12][0:2])
                minuto_ra = int(r[12][3:5])
                segundo_ra = int(r[12][6:8])

                intervalo_almoco = timedelta(
                    days=0,
                    hours=int(hora_ra),
                    minutes=int(minuto_ra),
                    seconds=int(segundo_ra)
                )

                tempo_espera = r[13]
                hora_rte = int(r[13][0:2])
                minuto_rte = int(r[13][3:5])
                segundo_rte = int(r[13][6:8])
                tp_espera = timedelta(
                    days=0,
                    hours=int(hora_rte),
                    minutes=int(minuto_rte),
                    seconds=int(segundo_rte)
                )

                tempo_descanso = r[14]
                hora_rtd = int(r[14][0:2])
                minuto_rtd = int(r[14][3:5])
                segundo_rtd = int(r[14][6:8])
                tp_descanso = timedelta(
                    days=0,
                    hours=int(hora_rtd),
                    minutes=int(minuto_rtd),
                    seconds=int(segundo_rtd)
                )

            for i in dados:
                inicio = i[2]
                fim = i[3]
                placa = i[0]
                data = i[1]

                tempo_total = intervalo_almoco + tp_espera + tp_descanso
                if dt != data:
                    print(f"Tempo processado: {tempo_processado}")
                    print(f"Tempo total: {tempo_total}")
                    print(f"Resumo geral {tempo_processado + variacao}")
                    tempo_processado = timedelta(days=0, hours=0, minutes=0, seconds=0)
                    print("Mudou de dia")
                else:
                    print(f"Tempo de almoço: {intervalo_almoco}")
                    print(f"Tempo de descanço: {tp_descanso}")
                    print(f"Tempo de espera: {tp_espera}")
                    print(f"Tempo processado: {tempo_processado}")
                    print(f"Tempo total: {tempo_total}")

                if dt != data:
                    query_resumo = f"select * from ResumoDiario where placa = '{placa}' and data = '{data.year}-{data.month}-{data.day}'"
                    dados_resumo = cf.getAll(query_resumo)
                    # renova os dados com a data atual
                    for r in dados_resumo:
                        dt = r[2]
                        dt_dia = dt.day
                        dt_mes = dt.month
                        dt_ano = dt.year
                        dt_hr_ini_almoco = datetime(dt_ano, dt_mes, dt_dia, 11, 30, 0, 0)
                        dt_hr_fim_almoco = datetime(dt_ano, dt_mes, dt_dia, 14, 00, 0, 0)
                        tempo_processado = timedelta(days=0, hours=0, minutes=0, seconds=0)

                        hora_almoco = datetime(
                            year=dt_ano,
                            month=dt_mes,
                            day=dt_dia,
                            hour=12,
                            minute=0,
                            second=0
                        )

                        inicio_jornada = r[6]
                        hora_ij = int(r[6][0:2])
                        minuto_ij = int(r[6][3:5])
                        segundo_ij = int(r[6][6:8])
                        ini_jornada = datetime(
                            day=dt_dia,
                            month=dt_mes,
                            year=dt_ano,
                            hour=hora_ij,
                            minute=minuto_ij,
                            second=segundo_ij
                        )

                        resumo_almoco = r[12]
                        hora_ra = int(r[12][0:2])
                        minuto_ra = int(r[12][3:5])
                        segundo_ra = int(r[12][6:8])
                        intervalo_almoco = timedelta(
                            days=0,
                            hours=int(hora_ra),
                            minutes=int(minuto_ra),
                            seconds=int(segundo_ra)
                        )

                        tempo_espera = r[13]
                        hora_rte = int(r[13][0:2])
                        minuto_rte = int(r[13][3:5])
                        segundo_rte = int(r[13][6:8])
                        tp_espera = timedelta(
                            days=0,
                            hours=int(hora_rte),
                            minutes=int(minuto_rte),
                            seconds=int(segundo_rte)
                        )

                        tempo_descanso = r[14]
                        hora_rtd = int(r[14][0:2])
                        minuto_rtd = int(r[14][3:5])
                        segundo_rtd = int(r[14][6:8])
                        tp_descanso = timedelta(
                            days=0,
                            hours=int(hora_rtd),
                            minutes=int(minuto_rtd),
                            seconds=int(segundo_rtd)
                        )
                        evento = "ESPERA"
                        v = True
                        a = True
                        te = True
                        inicio = i[2]
                        fim = i[3]
                        placa = i[0]
                        data = i[1]
                else:
                    print("")

                print(f"Inicio - {inicio} - Fim - {fim}")
                # verifica se houver horario ainda antes do tempo final de almoço
                if inicio <= dt_hr_fim_almoco and a == False:
                    print(fim - inicio)
                    tempo_processado += fim - inicio
                    inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=fim, tempoProcessado=fim - inicio)

                # essa parte trata dentro do o tempo de almoço
                if inicio >= dt_hr_ini_almoco and fim <= dt_hr_fim_almoco:
                    hora_final = hora_almoco + intervalo_almoco
                    tempo_processado += intervalo_almoco
                    a = False
                    print(f"Horario de almoço {hora_almoco} a {hora_final}")
                    inserir_dados(data=data, placa=placa, evento="ALMOCO", inicio=hora_almoco, fim=hora_final,
                                  tempoProcessado=hora_final - hora_almoco)

                    if inicio < hora_almoco:
                        print(f"Ficou em espera {inicio} a {hora_almoco}")
                        print(hora_almoco - inicio)
                        tempo_processado += (hora_almoco - inicio)

                        if tempo_processado > tp_espera and te == True:
                            print(tempo_processado - tp_espera)
                            sobra = tempo_processado - tp_espera
                            pro = tempo_processado - sobra
                            te_fim = inicio + pro
                            print(te_fim)
                            inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=te_fim,
                                          tempoProcessado=te_fim - inicio)
                            inicio = te_fim
                            evento = "DESCANCO"
                            te = False

                        inserir_dados(data=data, placa=placa, evento=evento, inicio=hora_final, fim=fim,
                                      tempoProcessado=hora_almoco - inicio)
                        if hora_final < dt_hr_fim_almoco:
                            print(f"{hora_final} a  {fim}")
                            print(fim - hora_final)
                            tempo_processado += (fim - hora_final)

                            if tempo_processado > tp_espera and te == True:
                                print(tempo_processado - tp_espera)
                                sobra = tempo_processado - tp_espera
                                pro = tempo_processado - sobra
                                te_fim = inicio + pro
                                print(te_fim)
                                inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=te_fim,
                                              tempoProcessado=te_fim - inicio)
                                inicio = te_fim
                                evento = "DESCANCO"
                                te = False

                            inserir_dados(data=data, placa=placa, evento=evento, inicio=hora_final, fim=fim,
                                          tempoProcessado=fim - hora_final)

                # essa parte trata o tempo antes e depois do almoço
                if inicio < dt_hr_ini_almoco and fim > dt_hr_fim_almoco:
                    hora_final = hora_almoco + intervalo_almoco
                    tempo_processado += intervalo_almoco
                    a = False
                    print(f"Horario de almoço {hora_almoco} a {hora_final}")
                    inserir_dados(data=data, placa=placa, evento="ALMOCO", inicio=hora_almoco, fim=hora_final,
                                  tempoProcessado=hora_final - hora_almoco)

                    # calculo de tempo antes do almoço ao inicio do almoço
                    if inicio < hora_almoco:
                        print(f"Ficou em espera {inicio} a {hora_almoco}")
                        print(hora_almoco - inicio)
                        tempo_processado += (hora_almoco - inicio)

                        if tempo_processado > tp_espera and te == True:
                            print(tempo_processado - tp_espera)
                            sobra = tempo_processado - tp_espera
                            pro = tempo_processado - sobra
                            te_fim = inicio + pro
                            print(te_fim)
                            inserir_dados(data=data, placa=placa, evento=evento, inicio=hora_final, fim=te_fim,
                                          tempoProcessado=hora_almoco - te_fim)
                            inicio = te_fim
                            evento = "DESCANCO"
                            te = False
                        inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=hora_almoco,
                                      tempoProcessado=hora_almoco - inicio)

                        # calculo de tempo depois do final do almoço
                        if hora_final < dt_hr_fim_almoco:
                            print(f"{hora_final} a  {dt_hr_fim_almoco}")
                            print(dt_hr_fim_almoco - hora_final)
                            tempo_processado += (dt_hr_fim_almoco - hora_final)

                            if tempo_processado > tp_espera and te == True:
                                print(tempo_processado - tp_espera)
                                sobra = tempo_processado - tp_espera
                                pro = tempo_processado - sobra
                                te_fim = hora_final + pro
                                print(te_fim)
                                inserir_dados(data=data, placa=placa, evento=evento, inicio=hora_final, fim=te_fim,
                                              tempoProcessado=te_fim - hora_final)
                                hora_final = te_fim
                                evento = "DESCANCO"
                                te = False

                            pro_dp_almoco = dt_hr_fim_almoco - hora_final
                            tempo_processado += pro_dp_almoco
                            inserir_dados(data=data, placa=placa, evento=evento, inicio=hora_final, fim=dt_hr_fim_almoco,
                                          tempoProcessado=pro_dp_almoco)

                            if tempo_processado > tp_espera and te == True:
                                print(tempo_processado - tp_espera)
                                sobra = tempo_processado - tp_espera
                                pro = tempo_processado - sobra
                                te_fim = dt_hr_fim_almoco + sobra
                                print(te_fim)
                                tempo_processado += te_fim - dt_hr_fim_almoco

                                inserir_dados(data=data, placa=placa, evento=evento, inicio=dt_hr_fim_almoco, fim=te_fim,
                                              tempoProcessado=te_fim - dt_hr_fim_almoco)
                                pro_dp_almoco = te_fim
                                evento = "DESCANCO"
                                te = False
                                tempo_processado += fim - pro_dp_almoco

                                inserir_dados(data=data, placa=placa, evento=evento, inicio=pro_dp_almoco, fim=fim,
                                              tempoProcessado=fim - pro_dp_almoco)

                                # tudo que for antes do almoço
                if inicio > ini_jornada and (inicio <= dt_hr_ini_almoco and fim <= dt_hr_ini_almoco):
                    print(f"Ficou em espera {inicio} a {fim}")
                    print(fim - inicio)
                    tempo_processado += (fim - inicio)

                    # variação de inicio ao primeiro registro
                    if v:
                        variacao = (inicio - ini_jornada)
                        print(f"Variação: {variacao}")
                        v = False

                    # tratar o tempo de espera
                    if tempo_processado > tp_espera and te == True:
                        print(tempo_processado - tp_espera)
                        sobra = tempo_processado - tp_espera
                        pro = tempo_processado - sobra
                        te_fim = inicio + pro
                        print(te_fim)
                        inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=te_fim,
                                      tempoProcessado=te_fim - inicio)
                        inicio = te_fim
                        evento = "DESCANCO"
                        te = False
                    inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=fim, tempoProcessado=fim - inicio)

                # tudo que for depois do limite do final do almoço
                if inicio > dt_hr_fim_almoco:
                    print(f"Ficou de {inicio} a {fim}")
                    print(fim - inicio)
                    tempo_processado += (fim - inicio)

                    if tempo_processado > tp_espera and te == True:
                        print(tempo_processado - tp_espera)
                        sobra = tempo_processado - tp_espera
                        print(f'Pro: {sobra}')
                        te_fim = fim - sobra
                        print(te_fim)
                        inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=te_fim,
                                      tempoProcessado=te_fim - inicio)
                        inicio = te_fim
                        evento = "DESCANCO"
                        te = False

                    inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=fim, tempoProcessado=fim - inicio)

                    # inicio for menor que horario de almoco e fim seja maior que horario de almoço
                if inicio < hora_almoco and fim > dt_hr_ini_almoco and a == True:
                    print(f"Ficou em espera {inicio} a {fim}")
                    print(fim - inicio)
                    tempo_processado += (fim - inicio)

                    if tempo_processado > tp_espera and te == True:
                        print(tempo_processado - tp_espera)
                        sobra = tempo_processado - tp_espera
                        pro = tempo_processado - sobra
                        te_fim = inicio + pro
                        print(te_fim)
                        inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=te_fim,
                                      tempoProcessado=te_fim - inicio)
                        inicio = te_fim
                        evento = "DESCANCO"
                        te = False

                    inserir_dados(data=data, placa=placa, evento=evento, inicio=inicio, fim=fim,
                                  tempoProcessado=fim - inicio)
        except NameError as erro:
            print(f"Ocorreu um erro interno - {erro}")


        query_processamento_analitico = f"""
                select * from processamentoAnalitico order by inicio
            """
        dados_pa = cf.getAll(query_processamento_analitico)
        context = {
            'dados': dados_pa,
            'resumos': dados_resumos_diarios
        }
        return render(request, template_name, context)
    else:
        return render(request, template_name)


@login_required
def atualizarDados(request):
    if request.method == 'POST' and request.is_ajax() :
        placa = request.POST.get('placa')
        data_op = request.POST.get('data_op')
        hr_almoco = request.POST.get('hr_almoco')
        tempo_espera = request.POST.get('tempo_espera')
        tempo_descanso = request.POST.get('tempo_descanso')

        query_data = f"select placa, data, horaAlmoco, tempoEspera, tempoDescanso, dtAlteracao, userAlteracao from vw_consolidado where placa = '{placa}' and data = '{data_op}'"
        sql = cf.getAll(query_data)[0]
        print(query_data)

        #processamento de Horas Banco
        hr_almoco_banco = datetime.strptime(sql[2], "%H:%M:%S")
        horaAlmoco = timedelta(days=0, hours=hr_almoco_banco.hour, minutes=hr_almoco_banco.minute, seconds=hr_almoco_banco.second)
        
        tempo_espera_banco = datetime.strptime(sql[3], "%H:%M:%S")
        tempoEspra = timedelta(days=0, hours=tempo_espera_banco.hour, minutes=tempo_espera_banco.minute, seconds=tempo_espera_banco.second)
        
        tempo_descanso_banco = datetime.strptime(sql[4], "%H:%M:%S")
        tempoDescanso = timedelta(days=0, hours=tempo_descanso_banco.hour, minutes=tempo_descanso_banco.minute, seconds=tempo_descanso_banco.second)
        
        total_horas_banco = horaAlmoco + tempoEspra + tempoDescanso
        print(f"Horas totais BD : {total_horas_banco}")

        #processamento de Horas Web
        hr_almoco_web = datetime.strptime(hr_almoco, "%H:%M:%S")
        horaAlmocoWeb = timedelta(days=0, hours=hr_almoco_web.hour, minutes=hr_almoco_web.minute, seconds=hr_almoco_web.second)

        tempo_espera_web = datetime.strptime(tempo_espera, "%H:%M:%S")
        tempoEsperaWeb = timedelta(days=0, hours=tempo_espera_web.hour, minutes=tempo_espera_web.minute, seconds=tempo_espera_web.second)
        
        tempo_descanso_web = datetime.strptime(tempo_descanso, "%H:%M:%S")
        tempoDescansoWeb = timedelta(days=0, hours=tempo_descanso_web.hour, minutes=tempo_descanso_web.minute, seconds=tempo_descanso_web.second)
        
        total_horas_web = horaAlmocoWeb + tempoEsperaWeb + tempoDescansoWeb
        print(f"Horas totais Web: {total_horas_web}")
        
        if total_horas_banco == total_horas_web:
            hoje = date.today()
            dt_alteracao = hoje.strftime("%d/%m/%Y")
            #query para atualizar dado
            up = f"update vw_consolidado SET horaAlmoco = '{hr_almoco}', tempoEspera = '{tempo_espera}', dtAlteracao = '{dt_alteracao}', userAlteracao = '{request.user}', tempoDescanso = '{tempo_descanso}' WHERE placa = '{placa}' and data = '{data_op}';"
            cf.query(up)
            print("Registro atualizado com sucesso.")
            mensagem = "Registro atualizado com sucesso."
            return JsonResponse({'info': mensagem}, status=200)
        elif total_horas_banco < total_horas_web:
            diferenca = total_horas_web - total_horas_banco
            print(f"Erro: Diferença maior {diferenca}")
            mensagem = f"ERRO. Diferença maior {diferenca}"
            return JsonResponse({"errors": mensagem}, status=500)
        elif total_horas_banco > total_horas_web:
            diferenca = total_horas_banco - total_horas_web
            print(f"Erro: Diferença menor {diferenca}")
            mensagem = f"ERRO. Diferencao menor {diferenca}"
            return JsonResponse({"errors": mensagem}, status=500)
        else:
            print("Erro não encontrado.")
            mensagem = f"ERRO. Falar com Admin."
            return JsonResponse({'info': mensagem}, status=500)
        
    return JsonResponse({"info": "OK"}, status=200)

@login_required
def ordemServicoList(request):
    template_name = 'app/ordem_servico/lista_os.html'
    lista_os = []
    query_placa = 'select distinct placa from vw_consolidado'
    placas = cf.getAll(query_placa)
    #lista_os = OrdemServico.objects.values('placa', 'data')
    form = OrdemServicoForm(request.POST or None)
    data_atual = date.today()
    
    if request.method == 'POST':
        data_inicial = request.POST.get('data_inicial')
        data_final = request.POST.get('data_final')
        placa = request.POST.get('consulta_placa')
        if placa == "":
            lista_os = OrdemServico.objects.filter(data__gte=data_inicial, data__lte=data_final)
        else:
            lista_os = OrdemServico.objects.filter(data__gte=data_inicial, data__lte=data_final, placa=placa)
        print(data_inicial)
        print(data_final)
        print(placa)
        print(lista_os)
        if lista_os:
            messages.success(request, 'Consulta realizada com sucesso.')
        else:
            messages.error(request, 'Nenhum dado encontrado.')
    context = {
        'form': form,
        'ordens_servicos': lista_os,
        'result_placa': placas
    }
    return render(request, template_name, context)

@login_required
def ordemServicoCreate(request):
    form = OrdemServicoForm(request.POST or None)
    if request.method == "POST":
        placa = request.POST.get('placa')
        os = request.POST.get('os')
        query_placa = f"select placa from vw_consolidado where placa = '{placa}'"
        placas = cf.getAll(query_placa)
        data_atual = date.today()
        if placas:
            if form.is_valid():
                post = form.save(commit=False)
                post.userInclusao = str(request.user)
                post.dtInclusao = data_atual
                print('salvo com sucesso.')
                post.save()
                mensagem = "Os cadastrada com sucesso."
                return JsonResponse({'info': mensagem}, status=200)
            else:
                mensagem = "Erro ao cadastrar, tente novamente."
                return JsonResponse({'errors': mensagem}, )
        else:
            mensagem = "Placa não encontrada."
            return JsonResponse({'errors': mensagem}, status=500)

@login_required
def ordemServicoUpdate(request, id):
    template_name = 'app/ordem_servico/atualizar_os.html'
    lista_os = OrdemServico.objects.all()
    obj = get_object_or_404(OrdemServico, id = id)
    form = OrdemServicoForm(request.POST or None, instance=obj)
    data_inclusao = obj.dtInclusao
    if form.is_valid():
        post = form.save(commit=False)
        post.userInclusao = str(request.user)
        post.dtInclusao = data_inclusao
        post.save()
        messages.success(request, "OS atualizada com sucesso.")
        return redirect('os')
    
    context = {
        'form': form,
        'ordens_servicos': lista_os
    }
    return render(request, template_name, context)

@login_required
def ordemServicoDelete(request, id):
    template_name = 'app/ordem_servico/deletar_os.html'
    lista_os = OrdemServico.objects.all()
    obj = get_object_or_404(OrdemServico, id = id)
    if request.method == "POST":
        messages.success(request, "OS excluida com sucesso.")
        obj.delete()
        return redirect('os')
    context = {
        'obj': obj,
        'ordens_servicos': lista_os
    }
    return render(request, template_name, context)

@login_required
def relatorio_movimento(request):
    query_placa = 'select distinct placa from vw_consolidado'
    placas = cf.getAll(query_placa)
    template_name = 'app/relatorio_mov.html'
    dados = []
    if request.method == 'POST':
        periodo_inicial = request.POST.get('data_inicial')
        periodo_final = request.POST.get('data_final')
        placa_carro = request.POST.get('placa')
        print(periodo_inicial, periodo_final, placa_carro)
        procedure(placa_carro, periodo_inicial, periodo_final)
        processamento = f'Placa: {placa_carro} - Data inicial: {periodo_inicial} Data Final: {periodo_final}'
        dados = tempEventos()
        if dados:
            horas_totais = dados[-1]['horas_totais']
        else:
            horas_totais = "Sem horas processadas"

        context = {
            'dados': dados,
            'horas_totais': horas_totais,
            'processamento': processamento
        }
        return render(request, template_name, context)
    else:
        context = {
            'dados': dados,
            'placas': placas
        }
        return render(request, template_name, context)