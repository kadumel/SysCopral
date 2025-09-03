import os
import time
import requests
from typing import Optional, Dict

# Opcional: cache em memória (troque por Redis em produção)
try:
    from cachetools import TTLCache
    token_cache = TTLCache(maxsize=4, ttl=3000)  # ~50 min
except Exception:
    token_cache = None

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SCOPE = "https://analysis.windows.net/powerbi/api/.default"

PBI_API_ROOT = "https://api.powerbi.com/v1.0/myorg"
PBI_WORKSPACE_ID = os.getenv("PBI_WORKSPACE_ID")
PBI_REPORT_ID = os.getenv("PBI_REPORT_ID")


class PowerBIError(Exception):
    print(Exception)

def _get_access_token() -> str:
    """Token de app (client credentials) no Azure AD."""
    if token_cache and "access_token" in token_cache:
        return token_cache["access_token"]

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
    }
    resp = requests.post(url, data=data, timeout=20)
    print(resp.json())
    if not resp.ok:
        raise PowerBIError(f"Falha ao obter access token: {resp.status_code} {resp.text}")
    
    access_token = resp.json()["access_token"]
    if token_cache:
        token_cache["access_token"] = access_token
    
    return access_token


def get_report_metadata(report_id: Optional[str] = None) -> Dict:
    """Recupera metadados do relatório para obter embedUrl e validar acesso."""
    report_id = report_id or PBI_REPORT_ID
    access_token = _get_access_token()
    url = f"{PBI_API_ROOT}/groups/{PBI_WORKSPACE_ID}/reports/{report_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    r = requests.get(url, headers=headers, timeout=20)
    print(r.json())
    if not r.ok:
        raise PowerBIError(f"Erro ao obter metadados do relatório: {r.status_code} {r.text}")
    
    return r.json()


def generate_embed_token(access_level: str = "View", report_id: Optional[str] = None, identities: Optional[list] = None) -> Dict:
    """Gera Embed Token (padrão: View). Suporta RLS via 'identities'."""
    report_id = report_id or PBI_REPORT_ID
    access_token = _get_access_token()

    url = f"{PBI_API_ROOT}/groups/{PBI_WORKSPACE_ID}/reports/{report_id}/GenerateToken"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {"accessLevel": access_level}
    if identities:
        payload["identities"] = identities

    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if not r.ok:
        raise PowerBIError(f"Erro ao gerar embed token: {r.status_code} {r.text}")
    
    return r.json()