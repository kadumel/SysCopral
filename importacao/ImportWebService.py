import requests
import xml.etree.ElementTree as ET
import zipfile, io, sys, os, time, datetime

import connectionFactory as cf

# Adicionar a pasta "folder" ao sys.paths


def getData(id):
    # URL do serviço
    url = "http://webservice.newrastreamentoonline.com.br/"

    # Corpo da requisição em XML
    xml_data = f"""
                <RequestMensagemCB>
                    <login>07269707000147</login>
                    <senha>683333</senha>
                    <mId>{id}</mId>
                </RequestMensagemCB>
    """

    # Converter o XML para bytes
    xml_bytes = xml_data.encode('utf-8')

    # Cabeçalhos HTTP
    headers = {
        "Content-Type": "application/xml",
        "Content-Length": str(len(xml_bytes))
    }

    # Enviar a requisição POST
    response = requests.post(url, data=xml_bytes, headers=headers)

    if response.status_code == 200:
        dados = unzip(response.content)
        insertDados(dados)
    else:
        return False

def unzip(data):
    # Criar um buffer em memória com os bytes recebidos
    zip_buffer = io.BytesIO(data)
    # Abrir o arquivo ZIP diretamente do buffer
    with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
        # Listar os arquivos no ZIP
        # print("Arquivos no ZIP:", zip_ref.namelist())
        # Ler um arquivo específico do ZIP sem salvar no disco
        file_name = zip_ref.namelist()[0]  # Pega o primeiro arquivo
        with zip_ref.open(file_name) as file:
            content = file.read()
            # print(f"Conteúdo do arquivo {file_name}:", content.decode('utf-8'))
            return content.decode('utf-8')

def insertDados(xml):
    root = ET.fromstring(xml)
    listdata = []
    for item in root.findall("MensagemCB"):
        
        mId = item.find("mId").text if item.find("mId") is not None else None
        veiID = item.find("veiID").text  if item.find("veiID")  is not None else None
        dt = str(item.find("dt").text)[:18].replace('T',' ') if item.find("dt")  is not None else None
        lat = item.find("lat").text if item.find("lat")  is not None else None
        lon = item.find("lon").text if item.find("lon")  is not None else None
        mun = item.find("mun").text if item.find("mun")  is not None else None
        uf = item.find("uf").text if item.find("uf")  is not None else None
        rod = item.find("rod").text if item.find("rod")  is not None else None
        rua = item.find("rua").text if item.find("rua")  is not None else None
        vel = item.find("vel").text if item.find("vel")  is not None else 0
        ori = item.find("ori").text if item.find("ori")  is not None else 0
        tpMsg = item.find("tpMsg").text if item.find("tpMsg")  is not None else None
        dtInc  = str(item.find("dtInc").text)[:18].replace('T',' ') if item.find("dtInc")  is not None else None
        evtG = item.find("evtG").text if item.find("evtG")  is not None else 0
        rpm = item.find("rpm").text if item.find("rpm")  is not None else 0
        odm = item.find("odm").text if item.find("odm")  is not None else 0
        lt = item.find("lt").text if item.find("lt")  is not None else None
        mLog = item.find("mLog").text if item.find("mLog")  is not None else None
        pcNome = item.find("pcNome").text if item.find("pcNome")  is not None else None
        mot = item.find("mot").text if item.find("mot") is not None else None
        motID = item.find("motID").text if item.find("motID")  is not None else None
        prNome = item.find("prNome").text if item.find("prNome") is not None else None
        listdata.append([mId, veiID, dt, lat, lon, mun, uf, rod, rua, vel, ori, 
                         tpMsg, dtInc, evtG, rpm, odm, lt,mLog, pcNome, mot, motID, prNome])
                                
    sql ="""
            INSERT INTO [dbo].[PosicaoCarroAPI]
			    ([mId],[veiID],[dt],[lat],[lon],[mun],[uf],[rod],[rua],[vel],[ori],[tpMsg],
			    [dtInc],[evtG],[rpm],[odm],[lt],[mLog],[pcNome],[mot],[motID],[prNome])
            VALUES
           (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          """
    
    cf.insertLote(sql, listdata)
    print(f'Total de registros importados: {len(listdata)}')
    print('Importaçao Finalizada...')
    print(100*'*')


def getUltimoId():
   print('Executando Tarefa...\n',datetime.datetime.today())
   id = cf.getId('select max(Mid) id from PosicaoCarroAPI') 
   getData(id)


while True:
    getUltimoId()
    time.sleep(310)