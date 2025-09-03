from copral import connectionFactory as cf

def id_carro(placa):
    if placa.isalpha() == False:
        print("Vai atrás do ID da placa")
        query_id_placa = f"select veiid from Veiculo where placa = 'OCB6296'"
        cursor = cf.conexao()
        placa = cursor.execute(query_id_placa).fetchone()[0]
        print(f"ID encontrado com sucesso - {placa}")
        return placa
    else:
        return placa
        
def deletar_dados():
    query_deletar = f"""
        delete from processamentoAnalitico 
    """
    cf.delete(query_deletar)
    print("Dados deletados com sucesso...")


def processar(placa, dt_inicial, dt_final):
    if placa.isalpha() == False:
        print("Vai atrás do ID da placa")
        query_id_placa = f"select veiid from Veiculo where placa = 'OCB6296'"
        cursor = cf.conexao()
        placa = cursor.execute(query_id_placa).fetchone()[0]
        print(f"ID encontrado com sucesso - {placa}")
    
    sql = f"exec sp_processamento_analitico '{placa}', '{dt_inicial}', '{dt_final}'"
    print(sql)
    cursor = cf.conexao()
    cursor.execute(sql)
    cursor.commit()
    cursor.close()
    print("sucesso.")
    

def inserir_dados(data, placa, evento, inicio, fim, tempoProcessado):
    query_inserir = f"""
    INSERT INTO processamentoAnalitico (data, placa, evento, inicio, fim, tempoProcessado) VALUES('{data}', '{placa}', '{evento}', '{inicio}', '{fim}', '{tempoProcessado}')"""
    cf.insert(query_inserir)
    print("Deu certo...")
