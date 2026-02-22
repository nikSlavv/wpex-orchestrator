"""
WPEX Orchestrator — Dashboard KPI API
Aggregated metrics for executive overview.
"""
import requests
from fastapi import APIRouter, Depends
from typing import Optional

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _fetch_relay_stats(container_name: str) -> Optional[dict]:
    """Fetch stats from a WPEX relay container via internal Docker network."""
    try:
        resp = requests.get(f"http://{container_name}:8080/stats", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def _compute_health_score(docker_status: str, stats: Optional[dict], restart_count: int = 0) -> float:
    """Compute composite health score (0-100) for a relay."""
    score = 100.0

    # Container status penalty
    if docker_status != "running":
        return 0.0

    # Restart count penalty (15% weight)
    if restart_count > 5:
        score -= 15
    elif restart_count > 2:
        score -= 8
    elif restart_count > 0:
        score -= 3

    if stats:
        # Handshake success rate (25% weight)
        total_hs = stats.get("total_handshakes", 0)
        success_hs = stats.get("successful_handshakes", 0)
        if total_hs > 0:
            success_rate = success_hs / total_hs
            if success_rate < 0.5:
                score -= 25
            elif success_rate < 0.8:
                score -= 15
            elif success_rate < 0.95:
                score -= 5

        # Active sessions health (check if peers are connected)
        peers = stats.get("peers", {})
        if isinstance(peers, dict):
            total_peers = len(peers)
            connected = sum(1 for p in peers.values() if isinstance(p, dict) and p.get("status") == 1)
            if total_peers > 0:
                connected_ratio = connected / total_peers
                if connected_ratio < 0.5:
                    score -= 20
                elif connected_ratio < 0.8:
                    score -= 10

    return max(0.0, min(100.0, score))


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

    # Tunnel counts
    if is_tenant_scoped:
        cur.execute("SELECT COUNT(*) FROM tunnels WHERE tenant_id = %s", (tenant_id,))
        tunnels_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tunnels WHERE status = 'active' AND tenant_id = %s", (tenant_id,))
        tunnels_active = cur.fetchone()[0]
    else:
        cur.execute("SELECT COUNT(*) FROM tunnels")
        tunnels_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tunnels WHERE status = 'active'")
        tunnels_active = cur.fetchone()[0]

    # Get relay details for health computation
    if is_tenant_scoped:
        cur.execute("SELECT id, name, port, web_port FROM servers WHERE tenant_id = %s ORDER BY name", (tenant_id,))
    else:
        cur.execute("SELECT id, name, port, web_port FROM servers ORDER BY name")
    relays = cur.fetchall()
    conn.close()

    relays_active = 0
    total_health = 0
    total_bytes = 0
    total_peers = 0
    tunnels_degraded = 0
    relay_details = []

    import docker
    try:
        docker_client = docker.from_env()
    except:
        docker_client = None

    for relay in relays:
        rid, name, udp_port, web_port = relay
        container_name = f"wpex-{name}"

        # Docker status
        status = "unknown"
        restart_count = 0
        if docker_client:
            try:
                c = docker_client.containers.get(container_name)
                status = c.status
                restart_count = c.attrs.get("RestartCount", 0)
            except:
                status = "not_created"

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

        if health < 70:
            tunnels_degraded += 1

        relay_details.append({
            "id": rid, "name": name, "status": status,
            "health": float(f"{health:.1f}"),
            "bytes_transferred": stats.get("total_bytes_transferred", 0) if stats else 0,
            "peers_count": len(stats.get("peers", {})) if stats and isinstance(stats.get("peers"), dict) else 0,
        })

    global_health = float(f"{(total_health / max(relays_total, 1)):.1f}")
    bandwidth_mbps = float(f"{(total_bytes / (1024 * 1024)):.2f}")

    return {
        "relays_active": relays_active,
        "relays_total": relays_total,
        "tunnels_active": tunnels_active,
        "tunnels_total": tunnels_total,
        "tunnels_degraded": tunnels_degraded,
        "tenants_active": tenants_active,
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

    import docker
    try:
        docker_client = docker.from_env()
    except:
        docker_client = None

    for relay in relays:
        rid, name = relay
        container_name = f"wpex-{name}"

        if docker_client:
            try:
                c = docker_client.containers.get(container_name)
                if c.status != "running":
                    alerts.append({
                        "severity": "critical",
                        "relay": name,
                        "message": f"Relay {name} non è in esecuzione (stato: {c.status})",
                        "type": "relay_down",
                    })
                restart_count = c.attrs.get("RestartCount", 0)
                if restart_count > 3:
                    alerts.append({
                        "severity": "warning",
                        "relay": name,
                        "message": f"Relay {name} ha {restart_count} restart",
                        "type": "high_restarts",
                    })
            except:
                alerts.append({
                    "severity": "critical",
                    "relay": name,
                    "message": f"Container {container_name} non trovato",
                    "type": "container_missing",
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

    # Tenant quota warnings
    cur2 = get_db().cursor()
    if is_tenant_scoped:
        cur2.execute("""
            SELECT t.name, t.max_tunnels,
                   (SELECT COUNT(*) FROM tunnels WHERE tenant_id = t.id) as count
            FROM tenants t WHERE t.is_active = TRUE AND t.id = %s
        """, (tenant_id,))
    else:
        cur2.execute("""
            SELECT t.name, t.max_tunnels,
                   (SELECT COUNT(*) FROM tunnels WHERE tenant_id = t.id) as count
            FROM tenants t WHERE t.is_active = TRUE
        """)
    for row in cur2.fetchall():
        if row[2] >= row[1] * 0.8:
            alerts.append({
                "severity": "warning",
                "tenant": row[0],
                "message": f"Tenant {row[0]} al {round(row[2]/row[1]*100)}% della quota tunnel",
                "type": "quota_warning",
            })

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
        cur.execute("SELECT id, name, port, web_port FROM servers WHERE tenant_id = %s ORDER BY name", (tenant_id,))
    else:
        cur.execute("SELECT id, name, port, web_port FROM servers ORDER BY name")
    relay_nodes = []
    for r in cur.fetchall():
        relay_nodes.append({
            "id": f"relay-{r[0]}", "type": "relay",
            "label": r[1], "data": {"port": r[2], "web_port": r[3]},
        })

    # Nodes — sites
    if is_tenant_scoped:
        cur.execute("""
            SELECT s.id, s.name, s.region, s.public_ip, t.name as tenant_name, t.id as tenant_id
            FROM sites s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            WHERE s.tenant_id = %s
            ORDER BY s.name
        """, (tenant_id,))
    else:
        cur.execute("""
            SELECT s.id, s.name, s.region, s.public_ip, t.name as tenant_name, t.id as tenant_id
            FROM sites s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            ORDER BY s.name
        """)
    site_nodes = []
    for s in cur.fetchall():
        site_nodes.append({
            "id": f"site-{s[0]}", "type": "site",
            "label": s[1], "data": {"region": s[2], "public_ip": s[3],
                                     "tenant": s[4], "tenant_id": s[5]},
        })

    # Edges — tunnels
    if is_tenant_scoped:
        cur.execute("""
            SELECT t.id, t.site_a_id, t.site_b_id, t.relay_id, t.status,
                   ten.name as tenant_name
            FROM tunnels t
            LEFT JOIN tenants ten ON t.tenant_id = ten.id
            WHERE t.tenant_id = %s
        """, (tenant_id,))
    else:
        cur.execute("""
            SELECT t.id, t.site_a_id, t.site_b_id, t.relay_id, t.status,
                   ten.name as tenant_name
            FROM tunnels t
            LEFT JOIN tenants ten ON t.tenant_id = ten.id
        """)
    edges = []
    for t in cur.fetchall():
        # Site A ↔ Relay
        edges.append({
            "id": f"edge-{t[0]}-a", "source": f"site-{t[1]}", "target": f"relay-{t[3]}",
            "tunnel_id": t[0], "status": t[4], "tenant": t[5],
        })
        # Relay ↔ Site B
        edges.append({
            "id": f"edge-{t[0]}-b", "source": f"relay-{t[3]}", "target": f"site-{t[2]}",
            "tunnel_id": t[0], "status": t[4], "tenant": t[5],
        })

    conn.close()
    return {
        "nodes": relay_nodes + site_nodes,
        "edges": edges,
    }
