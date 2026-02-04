import os
import sys
import textwrap
from datetime import date

import requests


def build_soap_envelope(operation: str, body_xml: str) -> str:
    """
    Gera um envelope SOAP 1.1 sem namespace no elemento da operação,
    seguindo o formato exemplificado no Postman.
    """
    return textwrap.dedent(f"""\
                                <?xml version="1.0" encoding="UTF-8"?>
                                <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                                <soap:Body>
                                    <{operation}>
                                    {body_xml}
                                    </{operation}>
                                </soap:Body>
                                </soap:Envelope>
                                """).strip()


def main():
    """
    Script de teste para enviar a requisição adiantamentoFornecedor ao AG.

    Ajuste as variáveis abaixo conforme necessário.
    """
    # Endereços padrão (conforme informado)
    base_url = os.environ.get("AG_BASE_URL", "http://172.16.1.40:8080/cgi-bin/AGWS.exe")
    wsdl_url = os.environ.get("AG_WSDL_URL", f"{base_url}/wsdl/IAG")
    soap_url = os.environ.get("AG_SOAP_URL", f"{base_url}/soap/IAG")

    # Operação a chamar (ajustável por env)
    operation = os.environ.get("AG_OPERATION", "IncluiAdiantamentoFornecedor")

    # SOAPAction (pode exigir o formato urn:Interface#Operacao)
    # Pelo exemplo do Postman, muitas vezes funciona usar apenas o nome da operação.
    soap_action = os.environ.get("AG_SOAP_ACTION", operation)

    # Exemplo de payload conforme solicitado (ajuste os nomes se o WSDL exigir):
    #   <Codigo>20279999999</Codigo>
    #   <Estabelecimento>0001</Estabelecimento>
    #   <ContaFinanceira>00030</ContaFinanceira>
    #   <Data>27/02/2026</Data>
    #   <CentroResultados>001003</CentroResultados>
    #   <DespesaAdiantamento>3030201010</DespesaAdiantamento>
    #   <Fornecedor>003405</Fornecedor>
    #   <FornecedorCNPJCPF></FornecedorCNPJCPF>
    #   <Valor>1</Valor>
    #   <Observacao>teste do sistema dos agregados</Observacao>
    #   <ExportaAC>0</ExportaAC>
    payload_fields = {
        "Codigo": os.environ.get("AG_CODIGO", "20279999999"),
        "Estabelecimento": os.environ.get("AG_ESTABELECIMENTO", "0001"),
        "ContaFinanceira": os.environ.get("AG_CONTA_FINANCEIRA", "00030"),
        "Data": os.environ.get("AG_DATA", "27/02/2026"),
        "CentroResultados": os.environ.get("AG_CENTRO_RESULTADOS", "001003"),
        "DespesaAdiantamento": os.environ.get("AG_DESPESA_ADIANTAMENTO", "3030201010"),
        "Fornecedor": os.environ.get("AG_FORNECEDOR", "003405"),
        "FornecedorCNPJCPF": os.environ.get("AG_FORNECEDOR_CNPJ_CPF", ""),
        "Valor": os.environ.get("AG_VALOR", "1"),
        "Observacao": os.environ.get("AG_OBSERVACAO", "teste do sistema dos agregados"),
        "ExportaAC": os.environ.get("AG_EXPORTA_AC", "0"),
    }

    # Monta o XML do corpo com os campos acima (simples, sem namespaces extras)
    body_parts = []
    for key, value in payload_fields.items():
        # Escape básico (para cenários simples). Se precisar, use xml.sax.saxutils.escape.
        value_str = str(value)
        body_parts.append(f"<{key}>{value_str}</{key}>")
    body_xml = "\n          ".join(body_parts)

    # Envelope SOAP 1.1
    envelope_xml = build_soap_envelope(operation=operation, body_xml=body_xml)

    headers = {
    'Content-Type': 'text/xml; charset=utf-8',
    'SOAPAction': 'urn:AGIntf-IAG#IncluiAdiantamentoFornecedor'
    }

    print("Enviando requisição SOAP para:", soap_url)
    print("WSDL:", wsdl_url)
    print("SOAPAction:", headers["SOAPAction"])
    print("--- Envelope ---")
    print(envelope_xml)
    print("---------------")

    try:
        resp = requests.post(soap_url, data=envelope_xml.encode("utf-8"), headers=headers, timeout=60)
    except requests.RequestException as exc:
        print("Falha ao enviar a requisição:", exc, file=sys.stderr)
        sys.exit(2)

    print("Status:", resp.status_code)
    print("Headers:", dict(resp.headers))
    print("--- Resposta ---")
    # Mostra texto completo (para inspeção inicial). Em produção, parseie o XML.
    print(resp.text)

    if resp.status_code >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()


