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
    """Fallback per Kubernetes: finge di essere Zabbix e restituisce i Pod del cluster come 'Containers'."""
    from kubernetes import client, config
    try:
        config.load_incluster_config()
    except:
        try:
            config.load_kube_config()
        except:
            return []

    core_api = client.CoreV1Api()
    try:
        pods = core_api.list_namespaced_pod(namespace='wpex').items
    except Exception:
        return []

    running = len([p for p in pods if p.status.phase == "Running"])
    total = len(pods)

    # Summary items expected by the frontend
    items = [
        {"itemid": "k8s_sum_r", "name": "K8s Pods Running", "key_": "docker.containers.running", "lastvalue": str(running), "value_type": "3"},
        {"itemid": "k8s_sum_s", "name": "K8s Pods Stopped", "key_": "docker.containers.stopped", "lastvalue": str(total - running), "value_type": "3"},
        {"itemid": "k8s_sum_t", "name": "K8s Pods Total",   "key_": "docker.containers.total",   "lastvalue": str(total), "value_type": "3"},
        {"itemid": "k8s_sum_i", "name": "K8s Container Images", "key_": "docker.images.total", "lastvalue": "0", "value_type": "3"},
    ]

    # Map each pod to expected zabbix-like keys
    for pod in pods:
        name = pod.metadata.name
        status = "running" if pod.status.phase == "Running" else "stopped"
        
        items.extend([
            {"itemid": f"s_{name}", "name": f"Pod {name} Status", "key_": f"docker.containers[{name},State.Status]", "lastvalue": status, "value_type": "1"},
            {"itemid": f"n_{name}", "name": f"Pod {name} Name",   "key_": f"docker.containers[{name},Name]",         "lastvalue": name, "value_type": "1"},
        ])
        
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


@router.get("/devices")
def get_devices():
    """Return all non-Docker hosts with availability and key metrics."""
    token = _zbx_login()

    # Get all hosts with availability info
    hosts = _zbx_call(token, "host.get", {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": ["ip", "dns", "type"],
        "filter": {"status": "0"},  # enabled only
    })

    result = []
    for h in hosts:
        hostid = h["hostid"]

        # Get latest values for key items
        items = _zbx_call(token, "item.get", {
            "hostids": hostid,
            "output": ["itemid", "key_", "lastvalue", "lastclock", "value_type", "units", "name"],
            "search": {"key_": ""},
            "searchByAny": True,
            "filter": {"status": "0"},
            "sortfield": "key_",
            "limit": 200,
        })

        # Extract useful metrics
        metrics = {}
        net_items = []
        for item in items:
            k = item["key_"]
            v = item["lastvalue"]
            if k in ("icmpping", "agent.ping"):
                metrics["ping"] = v
                metrics["ping_itemid"] = item["itemid"]
                metrics["ping_vt"] = item["value_type"]
            elif k == "icmppingsec":
                metrics["ping_ms"] = round(float(v) * 1000, 2) if v else None
            elif k in ("system.uptime", "agent.uptime"):
                metrics["uptime"] = int(v) if v else None
                metrics["uptime_itemid"] = item["itemid"]
                metrics["uptime_vt"] = item["value_type"]
            elif k in ("system.cpu.util", "system.cpu.util[,idle]"):
                metrics["cpu"] = round(float(v), 1) if v else None
                metrics["cpu_itemid"] = item["itemid"]
                metrics["cpu_vt"] = item["value_type"]
            elif k.startswith("vm.memory") or k == "system.memory.used":
                metrics["mem"] = v
                metrics["mem_itemid"] = item["itemid"]
                metrics["mem_vt"] = item["value_type"]
            elif "net.if.in" in k:
                net_items.append({**item, "direction": "in"})
            elif "net.if.out" in k:
                net_items.append({**item, "direction": "out"})

        # Availability: online if ping=1 or agent alive
        ping_val = metrics.get("ping")
        available = ping_val == "1" or ping_val == 1

        result.append({
            "hostid": hostid,
            "host": h["host"],
            "name": h["name"],
            "interfaces": h.get("interfaces", []),
            "available": available,
            "metrics": metrics,
            "net_items": net_items[:6],  # max 3 ifaces in/out
            "is_docker": h["host"] == "Docker-Host" or h["name"] == "Docker-Host",
        })

    return result


@router.get("/devices/{hostid}/items")
def get_host_items(hostid: str):
    """Return all items with lastvalue for any host."""
    token = _zbx_login()
    return _zbx_call(token, "item.get", {
        "hostids": hostid,
        "output": ["itemid", "name", "key_", "lastvalue", "lastclock", "units", "value_type"],
        "filter": {"status": "0"},
        "sortfield": "name",
        "limit": 300,
    })
