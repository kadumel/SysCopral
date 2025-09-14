import pyodbc
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()


def conexao():
    try:
        conn = pyodbc.connect(
            f'Driver={{{os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")}}};'
            f'Server={os.getenv("DB_HOST", "localhost")};'
            f'uid={os.getenv("DB_USER", "")};'
            f'pwd={os.getenv("DB_PASSWORD", "")};'
            f'Database={os.getenv("DB_NAME", "")};'
            f'Encrypt={os.getenv("DB_ENCRYPT", "yes")};'
            f'TrustServerCertificate={os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")};'
        )
        # print("Conexão bem-sucedida!")
        return conn
    except pyodbc.Error as ex:
        print("Erro ao conectar ao banco de dados:")
        print(f"Código do erro: {ex.args[0]}")
        print(f"Mensagem de erro: {ex.args[1]}")
        return None
    except Exception as e:
        print("Erro inesperado:", e)
        return None


def truncateTable(sql):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao executar truncateTable: {e}")
        conn.close()
        return False

def query(sql):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao executar query: {e}")
        conn.close()
        return False

def insert(sql, *args):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql, *args)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao executar insert: {e}")
        conn.close()
        return False

def delete(sql, *args):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(sql, *args)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao executar delete: {e}")
        conn.close()
        return False

def insertLote(sql, args):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    try:
        cursor = conn.cursor()
        lista = args
        for i in lista:
            cursor.execute(sql, i)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao executar insertLote: {e}")
        conn.close()
        return False


def getId(sql):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchall()
        id = 0
        for i in row:
            if hasattr(i, 'id') and i.id is not None:
                id = i.id
        cursor.close()
        conn.close()
        return id
    except Exception as e:
        print(f"Erro ao executar getId: {e}")
        conn.close()
        return 0


def getAll(sql):
    conn = conexao()
    if conn is None:
        print("Erro: Não foi possível conectar ao banco de dados")
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchall()
        List = []
        for i in row:
            List.append(i)
        cursor.close()
        conn.close()
        return List
    except Exception as e:
        print(f"Erro ao executar getAll: {e}")
        conn.close()
        return []

