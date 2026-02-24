from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os

ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/zabbix/api_jsonrpc.php")
ZABBIX_USER = os.environ.get("ZABBIX_USER", "apiuser")
ZABBIX_PASS = os.environ.get("ZABBIX_PASS", "apipass")

router = APIRouter(prefix="/api/zabbix", tags=["zabbix"])

class ZabbixAuthRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str = "user.login"
    params: dict = {"user": ZABBIX_USER, "password": ZABBIX_PASS}
    id: int = 1

class ZabbixHostRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str = "host.get"
    params: dict = {"output": ["hostid", "host", "name", "status"]}
    auth: str
    id: int = 2

@router.get("/hosts")
def get_zabbix_hosts():
    # Auth
    auth_payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"user": ZABBIX_USER, "password": ZABBIX_PASS},
        "id": 1
    }
    r = requests.post(ZABBIX_URL, json=auth_payload)
    if not r.ok or "result" not in r.json():
        raise HTTPException(status_code=502, detail="Zabbix auth failed")
    token = r.json()["result"]
    # Get hosts
    host_payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {"output": ["hostid", "host", "name", "status"]},
        "auth": token,
        "id": 2
    }
    r2 = requests.post(ZABBIX_URL, json=host_payload)
    if not r2.ok or "result" not in r2.json():
        raise HTTPException(status_code=502, detail="Zabbix host fetch failed")
    return r2.json()["result"]
