from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os
from datetime import datetime, timedelta

ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/zabbix/api_jsonrpc.php")
ZABBIX_USER = os.environ.get("ZABBIX_USER", "apiuser")
ZABBIX_PASS = os.environ.get("ZABBIX_PASS", "apipass")

router = APIRouter(prefix="/api/zabbix", tags=["zabbix"])

# --- Helper for Zabbix API auth ---
def zabbix_login():
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"user": ZABBIX_USER, "password": ZABBIX_PASS},
        "id": 1
    }
    r = requests.post(ZABBIX_URL, json=payload)
    if not r.ok or "result" not in r.json():
        raise HTTPException(status_code=502, detail="Zabbix auth failed")
    return r.json()["result"]

# --- API: Get traffic data for a host (example: net.if.in/if.out) ---
@router.get("/traffic/{hostid}")
def get_host_traffic(hostid: str):
    token = zabbix_login()
    # Get items for network interfaces (in/out)
    item_payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "hostids": hostid,
            "search": {"key_": "net.if."},
            "output": ["itemid", "name", "key_", "lastvalue"]
        },
        "auth": token,
        "id": 2
    }
    r = requests.post(ZABBIX_URL, json=item_payload)
    if not r.ok or "result" not in r.json():
        raise HTTPException(status_code=502, detail="Zabbix item fetch failed")
    items = r.json()["result"]
    # For each item, get history (last hour)
    now = int(datetime.now().timestamp())
    hour_ago = now - 3600
    traffic_data = {}
    for item in items:
        hist_payload = {
            "jsonrpc": "2.0",
            "method": "history.get",
            "params": {
                "itemids": item["itemid"],
                "time_from": hour_ago,
                "time_till": now,
                "output": "extend",
                "sortfield": "clock",
                "sortorder": "ASC",
                "limit": 60
            },
            "auth": token,
            "id": 3
        }
        r2 = requests.post(ZABBIX_URL, json=hist_payload)
        if not r2.ok or "result" not in r2.json():
            continue
        traffic_data[item["name"]] = [
            {"clock": int(h["clock"]), "value": float(h["value"])} for h in r2.json()["result"]
        ]
    return traffic_data
