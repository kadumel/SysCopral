import pyodbc
import pandas as pd

def conexao():
    try:
        conn = pyodbc.connect(
            'Driver={ODBC Driver 18 for SQL Server};'
            'Server=SRV-BI;'
            'uid=sa;'
            'pwd=123!@#qwe;'
            'Database=DW_COPRAl;'
            'Encrypt=yes;'
            'TrustServerCertificate=yes;'
        )
        # print("Conexão bem-sucedida!")
        return conn
    except pyodbc.Error as ex:
        print("Erro ao conectar ao banco de dados:")
        print(f"Código do erro: {ex.args[0]}")
        print(f"Mensagem de erro: {ex.args[1]}")
        conn = None  # Certifique-se de que conn não seja usado incorretamente depois
    except Exception as e:
        print("Erro inesperado:", e)


def truncateTable(sql):
    cursor = conexao()
    cursor.execute(sql)
    cursor.commit()
    cursor.close()

def query(sql):
    cursor = conexao()
    cursor.execute(sql)
    cursor.commit()
    cursor.close()

def insert(sql, *args):
    cursor = conexao()
    cursor.execute(sql, *args)
    cursor.commit()
    cursor.close()


def delete(sql, *args):
    cursor = conexao()
    cursor.execute(sql, *args)
    cursor.commit()
    cursor.close()

def insertLote(sql, args):
    cursor = conexao()
    lista = args
    for i in lista:
        cursor.execute(sql, i)
    cursor.commit()
    cursor.close()


def getId(sql):
    cursor = conexao()
    row = cursor.execute(sql)
    id = 0
    for i in row:
        if i.id != None:
            id = i.id

    cursor.close()
    return id


def getAll(sql):
    cursor = conexao()
    row = cursor.execute(sql)
    List = []
    for i in row:
        List.append(i)
    cursor.close()
    return List

