from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os
from datetime import datetime

ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/zabbix/api_jsonrpc.php")
ZABBIX_USER = os.environ.get("ZABBIX_USER", "apiuser")
ZABBIX_PASS = os.environ.get("ZABBIX_PASS", "apipass")

router = APIRouter(prefix="/api/zabbix", tags=["zabbix"])


def _zbx_login() -> str:
    r = requests.post(ZABBIX_URL, json={
        "jsonrpc": "2.0", "method": "user.login",
        "params": {"user": ZABBIX_USER, "password": ZABBIX_PASS}, "id": 1
    }, verify=False, timeout=10)
    if not r.ok or "result" not in r.json():
        raise HTTPException(status_code=502, detail="Zabbix auth failed")
    return r.json()["result"]


def _zbx_call(token: str, method: str, params: dict, req_id: int = 2) -> list:
    r = requests.post(ZABBIX_URL, json={
        "jsonrpc": "2.0", "method": method,
        "params": params, "auth": token, "id": req_id
    }, verify=False, timeout=10)
    if not r.ok or "result" not in r.json():
        raise HTTPException(status_code=502, detail=f"Zabbix {method} failed")
    return r.json()["result"]

class ZabbixAuthRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str = "user.login"
    params: dict = {"user": ZABBIX_USER, "password": ZABBIX_PASS}
    id: int = 1


@router.get("/hosts")
def get_zabbix_hosts():
    token = _zbx_login()
    return _zbx_call(token, "host.get", {
        "output": ["hostid", "host", "name", "status"]
    })


@router.get("/docker/{hostid}")
def get_docker_stats(hostid: str):
    """Return all docker.* items with lastvalue for a host."""
    token = _zbx_login()
    items = _zbx_call(token, "item.get", {
        "hostids": hostid,
        "search": {"key_": "docker."},
        "output": ["itemid", "name", "key_", "lastvalue", "lastclock", "units", "value_type"],
        "sortfield": "key_",
    })
    return items


@router.get("/history/{itemid}")
def get_item_history(itemid: str, hours: int = 1, value_type: int = 0):
    """Return history data for a single item (last N hours). value_type: 0=float, 3=int."""
    token = _zbx_login()
    now = int(datetime.now().timestamp())
    from_ts = now - hours * 3600
    data = _zbx_call(token, "history.get", {
        "itemids": itemid,
        "history": value_type,
        "time_from": from_ts,
        "time_till": now,
        "output": "extend",
        "sortfield": "clock",
        "sortorder": "ASC",
        "limit": 200,
    })
    return [{"clock": int(h["clock"]), "value": h["value"]} for h in data]
