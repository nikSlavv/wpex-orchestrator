"""
WPEX Orchestrator — Dashboard KPI API
Aggregated metrics for executive overview.
"""
import requests
from fastapi import APIRouter, Depends
from typing import Optional

from database import get_db, DATA_KEY
from auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

def _init_k8s():
    try:
        from kubernetes import config
        config.load_incluster_config()
    except:
        try:
            from kubernetes import config
            config.load_kube_config()
        except:
            pass

def _get_k8s_pod_status(name: str):
    from kubernetes import client
    _init_k8s()
    try:
        core_api = client.CoreV1Api()
        pods = core_api.list_namespaced_pod(namespace="wpex", label_selector=f"app=wpex-{name}")
        if not pods.items:
            try:
                apps_api = client.AppsV1Api()
                apps_api.read_namespaced_deployment(name=f"wpex-{name}", namespace="wpex")
                return "stopped", 0
            except:
                return "not_created", 0
                
        pod = pods.items[0]
        status = pod.status.phase.lower()
        if status == "running":
            is_ready = any(cond.type == "Ready" and cond.status == "True" for cond in pod.status.conditions) if pod.status.conditions else False
            if not is_ready:
                status = "starting"
        restart_count = sum([c.restart_count for c in pod.status.container_statuses]) if pod.status.container_statuses else 0
        return status, restart_count
    except:
        return "error", 0


def _fetch_relay_stats(container_name: str) -> Optional[dict]:
    """Fetch stats from a WPEX relay container via internal Docker network."""
    try:
        resp = requests.get(f"http://{container_name}.wpex.svc.cluster.local:8080/stats", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def _compute_health_score(status: str, stats, restart_count: int = 0) -> float:
    """Compute composite health score (0-100) using the same weighted-average as relay_proxy."""
    if status != "running":
        return 0.0

    components = {}

    # Container status
    components["container"] = 100.0

    # Restart penalty
    rc_score = max(0, 100 - restart_count * 10)
    components["restarts"] = float(rc_score)

    if stats:
        # Handshake rate
        total_hs = stats.get("total_handshakes", 0)
        success_hs = stats.get("successful_handshakes", 0)
        if total_hs > 0:
            components["handshake_rate"] = round(success_hs / total_hs * 100, 1)
        else:
            components["handshake_rate"] = 100.0

        # Peer connectivity
        peers = stats.get("peers", {})
        if isinstance(peers, dict) and len(peers) > 0:
            connected = sum(1 for p in peers.values() if isinstance(p, dict) and p.get("status") == 1)
            components["connectivity"] = round(connected / len(peers) * 100, 1)
        else:
            components["connectivity"] = 100.0

    # Weighted average — same weights as relay_proxy.py
    weights = {"container": 0.2, "restarts": 0.15, "handshake_rate": 0.35, "connectivity": 0.3}
    weighted_sum = 0.0
    total_weight = 0.0
    for k, w in weights.items():
        if k in components:
            weighted_sum += components[k] * w
            total_weight += w

    return round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0


@router.get("/kpi")
def get_dashboard_kpi(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()

    is_tenant_scoped = user.get("role") in ("engineer", "viewer")
    tenant_id = user.get("tenant_id")

    # Relay counts
    if is_tenant_scoped:
        cur.execute("SELECT COUNT(*) FROM servers WHERE tenant_id = %s", (tenant_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM servers")
    relays_total = cur.fetchone()[0]

    # Tenant counts
    if is_tenant_scoped:
        cur.execute("SELECT COUNT(*) FROM tenants WHERE is_active = TRUE AND id = %s", (tenant_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM tenants WHERE is_active = TRUE")
    tenants_active = cur.fetchone()[0]

    # Keys Assigned
    if is_tenant_scoped:
        cur.execute("SELECT COUNT(*) FROM access_keys WHERE tenant_id = %s", (tenant_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM access_keys")
    keys_assigned = cur.fetchone()[0]

    # (Tunnels count removed)

    # Get relay details for health computation
    if is_tenant_scoped:
        cur.execute("""
            SELECT s.id, s.name, s.port, s.web_port, s.tenant_id, t.name as tenant_name 
            FROM servers s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            WHERE s.tenant_id = %s ORDER BY s.name
        """, (tenant_id,))
    else:
        cur.execute("""
            SELECT s.id, s.name, s.port, s.web_port, s.tenant_id, t.name as tenant_name 
            FROM servers s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            ORDER BY s.name
        """)
    relays = cur.fetchall()
    conn.close()

    relays_active = 0
    total_health = 0
    total_bytes = 0
    total_peers = 0
    relay_details = []

    for relay in relays:
        rid, name, udp_port, web_port, t_id, t_name = relay
        container_name = f"wpex-{name}"

        status, restart_count = _get_k8s_pod_status(name)

        if status == "running":
            relays_active += 1

        # Fetch WPEX stats
        stats = _fetch_relay_stats(container_name)
        health = _compute_health_score(status, stats, restart_count)
        total_health += health

        if stats:
            total_bytes += stats.get("total_bytes_transferred", 0)
            peers = stats.get("peers", {})
            if isinstance(peers, dict):
                total_peers += len(peers)

        relay_details.append({
            "id": rid, "name": name, "status": status,
            "tenant_id": t_id, "tenant_name": t_name or "Globale",
            "health": float(f"{health:.1f}"),
            "bytes_transferred": stats.get("total_bytes_transferred", 0) if stats else 0,
            "peers_count": len(stats.get("peers", {})) if stats and isinstance(stats.get("peers"), dict) else 0,
        })

    global_health = float(f"{(total_health / max(relays_total, 1)):.1f}")
    bandwidth_mbps = float(f"{(total_bytes / (1024 * 1024)):.2f}")

    return {
        "relays_active": relays_active,
        "relays_total": relays_total,
        "tenants_active": tenants_active,
        "keys_assigned": keys_assigned,
        "bandwidth_aggregated_mb": bandwidth_mbps,
        "total_peers": total_peers,
        "global_health_score": global_health,
        "relays": relay_details,
    }


@router.get("/alerts")
def get_dashboard_alerts(user=Depends(get_current_user)):
    """Get critical alerts based on current system state."""
    conn = get_db()
    cur = conn.cursor()
    
    is_tenant_scoped = user.get("role") in ("engineer", "viewer")
    tenant_id = user.get("tenant_id")
    
    if is_tenant_scoped:
        cur.execute("SELECT id, name FROM servers WHERE tenant_id = %s ORDER BY name", (tenant_id,))
    else:
        cur.execute("SELECT id, name FROM servers ORDER BY name")
    relays = cur.fetchall()
    conn.close()

    alerts = []

    for relay in relays:
        rid, name = relay
        container_name = f"wpex-{name}"

        status, restart_count = _get_k8s_pod_status(name)

        if status != "running":
            alerts.append({
                "severity": "critical",
                "relay": name,
                "message": f"Relay {name} non è in esecuzione (stato: {status})",
                "type": "relay_down",
            })
            
        if restart_count > 3:
            alerts.append({
                "severity": "warning",
                "relay": name,
                "message": f"Relay {name} ha {restart_count} restart",
                "type": "high_restarts",
            })

        # Check stats
        stats = _fetch_relay_stats(container_name)
        if stats:
            total_hs = stats.get("total_handshakes", 0)
            success_hs = stats.get("successful_handshakes", 0)
            if total_hs > 10 and (success_hs / total_hs) < 0.7:
                alerts.append({
                    "severity": "warning",
                    "relay": name,
                    "message": f"Basso tasso di handshake completati ({round(success_hs/total_hs*100,1)}%)",
                    "type": "low_handshake_rate",
                })

    # (Tenant quota for tunnels omitted)

    return {"alerts": alerts, "total": len(alerts),
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "warning": len([a for a in alerts if a["severity"] == "warning"])}


@router.get("/topology")
def get_topology_data(user=Depends(get_current_user)):
    """Return topology data for D3.js visualization."""
    conn = get_db()
    cur = conn.cursor()

    is_tenant_scoped = user.get("role") in ("engineer", "viewer")
    tenant_id = user.get("tenant_id")

    # Nodes — relays
    if is_tenant_scoped:
        cur.execute("""
            SELECT s.id, s.name, s.port, s.web_port, s.tenant_id, t.name as tenant_name 
            FROM servers s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            WHERE s.tenant_id = %s ORDER BY s.name
        """, (tenant_id,))
    else:
        cur.execute("""
            SELECT s.id, s.name, s.port, s.web_port, s.tenant_id, t.name as tenant_name 
            FROM servers s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            ORDER BY s.name
        """)
    relay_nodes = []
    for r in cur.fetchall():
        relay_nodes.append({
            "id": f"relay-{r[0]}", "type": "relay",
            "label": r[1],
            "data": {
                "port": r[2], "web_port": r[3],
                "tenant_id": r[4], "tenant": r[5] or "Globale"
            },
        })

    # Nodes — keys (acting as sites)
    if is_tenant_scoped:
        cur.execute("""
            SELECT k.id, k.alias, t.name as tenant_name, t.id as tenant_id
            FROM access_keys k
            LEFT JOIN tenants t ON k.tenant_id = t.id
            WHERE k.tenant_id = %s
            ORDER BY k.alias
        """, (tenant_id,))
    else:
        cur.execute("""
            SELECT k.id, k.alias, t.name as tenant_name, t.id as tenant_id
            FROM access_keys k
            LEFT JOIN tenants t ON k.tenant_id = t.id
            ORDER BY k.alias
        """)
    key_nodes = []
    for k in cur.fetchall():
        key_nodes.append({
            "id": f"key-{k[0]}", "type": "site",
            "label": k[1], "data": {"tenant": k[2], "tenant_id": k[3]},
        })

    # Edges — key-to-relay links
    if is_tenant_scoped:
        cur.execute("""
            SELECT skl.key_id, skl.server_id, ten.name as tenant_name, s.name as server_name, pgp_sym_decrypt(k.key_value, %s) as public_key
            FROM server_keys_link skl
            JOIN access_keys k ON skl.key_id = k.id
            JOIN servers s ON skl.server_id = s.id
            LEFT JOIN tenants ten ON k.tenant_id = ten.id
            WHERE k.tenant_id = %s
        """, (DATA_KEY, tenant_id))
    else:
        cur.execute("""
            SELECT skl.key_id, skl.server_id, ten.name as tenant_name, s.name as server_name, pgp_sym_decrypt(k.key_value, %s) as public_key
            FROM server_keys_link skl
            JOIN access_keys k ON skl.key_id = k.id
            JOIN servers s ON skl.server_id = s.id
            LEFT JOIN tenants ten ON k.tenant_id = ten.id
        """, (DATA_KEY,))
        
    links = cur.fetchall()

    server_names = {link[3] for link in links}
    server_stats = {}
    for s_name in server_names:
        stats = _fetch_relay_stats(f"wpex-{s_name}")
        raw_peers = stats.get("peers", {}) if stats else {}
        
        peers_list = list(raw_peers.values()) if isinstance(raw_peers, dict) else (raw_peers if isinstance(raw_peers, list) else [])
        
        active_count = 0
        for p in peers_list:
            if isinstance(p, dict) and (p.get("status") == 1 or p.get("endpoint")):
                active_count += 1
                
        server_stats[s_name] = {"active_count": active_count}

    edges = []
    from collections import defaultdict
    s_links = defaultdict(list)
    for link in links:
        s_links[link[3]].append(link)
        
    for s_name, sub_links in s_links.items():
        active_available = int(server_stats.get(s_name, {}).get("active_count", 0))
        
        for link in sub_links:
            key_id, server_id, tenant_name, server_name, public_key = link
            
            if active_available > 0:
                status = "active"
                active_available -= 1
            else:
                status = "down"

            edges.append({
                "id": f"edge-k{key_id}-s{server_id}",
                "source": f"key-{key_id}",
                "target": f"relay-{server_id}",
                "tenant": tenant_name,
                "status": status
            })

    conn.close()
    return {
        "nodes": relay_nodes + key_nodes,
        "edges": edges,
    }
