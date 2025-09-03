import json
from copral import connectionFactory as cf
from datetime import datetime, timedelta

def procedure(placa, data_inicial, data_final):
    if placa.isalpha() == False:
        print("Vai atrás do ID da placa")
        query_id_placa = f"select veiid from Veiculo where placa = '{placa}'"
        cursor = cf.conexao()
        placa = cursor.execute(query_id_placa).fetchone()[0]
        print(f"ID encontrado com sucesso - {placa}")
        query_procedute = f"exec SP_PROCESSAMENTO_ANALITICO {placa}, '{data_inicial} 00:00:00', '{data_final} 23:59:59'"
        print(query_procedute)
        cf.query(query_procedute)

        return 'Tudo certo'
    else:
        return 'Error'

def tempEventos():
    sql = 'select * from tempEventos order by DATAHORA'
    cursor = cf.conexao()
    query = cursor.execute(sql).fetchall()
    acumulo_parado = []
    acumulo_movimento = []
    parado = 1
    movimento = 1
    p = False
    dic = []
    for i in query:
        id_placa = i[0]
        data_hora = i[1]
        velocidade = i[2]
        latitude = i[3].replace(',','.')
        longitude = i[4].replace(',','.')
        meu_dic = {
            'id': id_placa,
            'data': data_hora,
            'velocidade': velocidade,
            'latitude': latitude,
            'longitude': longitude
        }
        if velocidade < 5:
            if len(acumulo_movimento) >= 1 and parado == 3:
                data_final_movimento = acumulo_movimento[-1]['data']
                velocidade_final_movimento = acumulo_movimento[-1]['velocidade']
                latitude_final_movimento = acumulo_movimento[-1]['latitude']
                longitude_final_moviemento = acumulo_movimento[-1]['longitude']
                #print(f'FINAL MOVIMENTADO: {data_final_movimento}')
                mensagem = 'FIM DIREÇÃO'
                meu_dic = {
                    'id': id_placa,
                    'data': data_final_movimento,
                    'mensagem': mensagem,
                    'velocidade': velocidade_final_movimento,
                    'latitude': latitude_final_movimento,
                    'longitude': longitude_final_moviemento
                }
                dic.append(meu_dic)
                acumulo_movimento = []

            if parado == 3:
                data_inicial_parado = acumulo_parado[0]['data']
                velocidade_parado = acumulo_parado[0]['velocidade']
                latitude_parado = acumulo_parado[0]['latitude']
                longitude_parado = acumulo_parado[0]['longitude']
                #print(acumulo_parado[1])
                #print(f'INICIAL PARADO: {data_inicial_parado}')
                acumulo_movimento = []
                mensagem = f'INICIO PARADO'
                meu_dic = {
                    'id': id_placa,
                    'data': data_inicial_parado,
                    'mensagem': mensagem,
                    'velocidade': velocidade_parado,
                    'latitude': latitude_parado,
                    'longitude': longitude_parado
                }
                #dic.append(meu_dic)
                acumulo_movimento = []
            acumulo_parado.append(meu_dic)
            parado += 1

        elif velocidade > 5:
            acumulo_movimento.append(meu_dic)
            if len(acumulo_parado) >= 3:
                velocidade_final_parado = acumulo_parado[-1]['velocidade']
                data_final_parado = acumulo_parado[-1]['data']
                latitude_final_parado = acumulo_parado[-1]['latitude']
                longitude_final_parado = acumulo_parado[-1]['longitude']
                #print(f'FINAL PARADO {data_final_parado}')
                #print(acumulo_parado)
                mensagem = f'FIM PARADO'
                meu_dic = {
                    'id': id_placa,
                    'data': data_final_parado,
                    'mensagem': mensagem,
                    'velocidade': velocidade_final_parado,
                    'latitude': latitude_final_parado,
                    'longitude': longitude_final_parado
                }
                #dic.append(meu_dic)
                acumulo_parado = []
                parado = 1

            if len(acumulo_movimento) == 1:
                data_inicial_movimento = acumulo_movimento[0]['data']
                velocidade_inicial_movimento = acumulo_movimento[0]['velocidade']
                latitude_inicial_movimento = acumulo_movimento[0]['latitude']
                longitude_inicial_movimento = acumulo_movimento[0]['longitude']
                #print(f'INICIAL MOVIMENTO: {data_inicial_movimento}')
                mensagem = f'INICIO DIREÇÃO'
                meu_dic = {
                    'id': id_placa,
                    'data': data_inicial_movimento,
                    'mensagem': mensagem,
                    'velocidade': velocidade_inicial_movimento,
                    'latitude': latitude_inicial_movimento,
                    'longitude': longitude_inicial_movimento
                }
                dic.append(meu_dic)
                acumulo_parado = []
                parado = 1
            acumulo_parado = []
            parado = 1

    if acumulo_movimento:
        mensagem = 'FIM DIREÇÃO'
        meu_dic = {
            'id': id_placa,
            'data': data_hora,
            'mensagem': mensagem,
            'velocidade': velocidade,
            'latitude': latitude,
            'longitude': longitude
        }
        dic.append(meu_dic)

    if acumulo_parado:
        mensagem = 'FIM PARADO'
        meu_dic = {
            'id': id_placa,
            'data': data_hora,
            'mensagem': mensagem,
            'velocidade': velocidade,
            'latitude': latitude,
            'longitude': longitude
        }
        #dic.append(meu_dic)
    horas_movimentadas = []
    hr = timedelta(0, 0, 0, 0, 0, 0)
    p = 1
    for i in range(len(dic)):
        if p == len(dic):
            print('ACABOU')
        else:
            dt1 = dic[i]['data']
            dt2 = dic[p]['data']
            resultado = dt2 - dt1
            horas_movimentadas.append(resultado)
            print(resultado)
            p += 1
            hr += resultado
    print(f"Total de horas: {hr}")

    if horas_movimentadas:
        dic[-1]['horas_totais'] = hr

    return dic
