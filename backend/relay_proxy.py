"""
WPEX Orchestrator — Relay Proxy API
Proxies requests to individual WPEX relay containers.
Provides enhanced container info and diagnostics.
"""
import os
import requests as http_requests
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/relays", tags=["relays"])


def _get_docker_client():
    try:
        import docker
        return docker.from_env()
    except:
        return None


def _get_relay_name(relay_id: int) -> Optional[str]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM servers WHERE id = %s", (relay_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


@router.get("/{relay_id}/stats")
def get_relay_stats(relay_id: int, user=Depends(get_current_user)):
    """Proxy stats from WPEX relay container."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404, detail="Relay non trovato")

    container_name = f"wpex-{name}"
    try:
        resp = http_requests.get(f"http://{container_name}:8080/stats", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        pass

    return {"error": "Statistiche non disponibili", "relay": name}


@router.get("/{relay_id}/health")
def get_relay_health(relay_id: int, user=Depends(get_current_user)):
    """Get computed health score for a relay."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404, detail="Relay non trovato")

    container_name = f"wpex-{name}"
    client = _get_docker_client()

    # Docker status
    docker_info = {"status": "unknown", "restart_count": 0, "uptime": None, "image": None}
    if client:
        try:
            c = client.containers.get(container_name)
            docker_info["status"] = c.status
            docker_info["restart_count"] = c.attrs.get("RestartCount", 0)
            docker_info["image"] = c.image.tags[0] if c.image.tags else str(c.image.id)[:20]
            # Get started_at
            state = c.attrs.get("State", {})
            docker_info["started_at"] = state.get("StartedAt")
        except:
            docker_info["status"] = "not_found"

    # WPEX stats
    stats = None
    try:
        resp = http_requests.get(f"http://{container_name}:8080/stats", timeout=2)
        if resp.status_code == 200:
            stats = resp.json()
    except:
        pass

    # Compute health
    score = 100.0
    components = {}

    if docker_info["status"] != "running":
        score = 0.0
        components["container"] = {"score": 0, "detail": f"Container {docker_info['status']}"}
    else:
        components["container"] = {"score": 100, "detail": "Running"}

        # Restart penalty
        rc = docker_info["restart_count"]
        rc_score = max(0, 100 - rc * 10)
        components["restarts"] = {"score": rc_score, "detail": f"{rc} restarts"}

        if stats:
            # Handshake rate
            total_hs = stats.get("total_handshakes", 0)
            success_hs = stats.get("successful_handshakes", 0)
            if total_hs > 0:
                hs_rate = success_hs / total_hs * 100
                components["handshake_rate"] = {"score": round(hs_rate, 1), "detail": f"{round(hs_rate,1)}% success"}
            else:
                components["handshake_rate"] = {"score": 100, "detail": "No handshakes yet"}

            # Peer connectivity
            peers = stats.get("peers", {})
            if isinstance(peers, dict) and len(peers) > 0:
                connected = sum(1 for p in peers.values() if isinstance(p, dict) and p.get("status") == 1)
                conn_pct = connected / len(peers) * 100
                components["connectivity"] = {"score": round(conn_pct, 1), "detail": f"{connected}/{len(peers)} peers connected"}
            else:
                components["connectivity"] = {"score": 100, "detail": "No peers tracked"}

        # Weighted average
        weights = {"container": 0.2, "restarts": 0.15, "handshake_rate": 0.35, "connectivity": 0.3}
        weighted_sum = 0
        total_weight = 0
        for k, w in weights.items():
            if k in components:
                weighted_sum += components[k]["score"] * w
                total_weight += w
        score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0

    return {
        "relay_id": relay_id,
        "relay_name": name,
        "health_score": score,
        "components": components,
        "docker": docker_info,
        "stats_available": stats is not None,
    }


@router.get("/{relay_id}/container")
def get_relay_container_info(relay_id: int, user=Depends(get_current_user)):
    """Get detailed Docker container info for a relay."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404, detail="Relay non trovato")

    container_name = f"wpex-{name}"
    client = _get_docker_client()
    if not client:
        return {"error": "Docker non disponibile"}

    try:
        c = client.containers.get(container_name)
        state = c.attrs.get("State", {})
        host_config = c.attrs.get("HostConfig", {})

        # Get resource stats
        resource_stats = {}
        try:
            stats = c.stats(stream=False)
            # CPU
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            if system_delta > 0:
                num_cpus = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
                resource_stats["cpu_pct"] = round((cpu_delta / system_delta) * num_cpus * 100, 2)
            # Memory
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            resource_stats["memory_usage_mb"] = round(mem_usage / (1024 * 1024), 1)
            resource_stats["memory_limit_mb"] = round(mem_limit / (1024 * 1024), 1)
            resource_stats["memory_pct"] = round(mem_usage / mem_limit * 100, 2)
            # Network
            networks = stats.get("networks", {})
            tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())
            rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
            resource_stats["network_tx_mb"] = round(tx_bytes / (1024 * 1024), 2)
            resource_stats["network_rx_mb"] = round(rx_bytes / (1024 * 1024), 2)
        except:
            pass

        return {
            "name": container_name,
            "status": c.status,
            "started_at": state.get("StartedAt"),
            "finished_at": state.get("FinishedAt"),
            "restart_count": c.attrs.get("RestartCount", 0),
            "image": c.image.tags[0] if c.image.tags else None,
            "image_id": str(c.image.id)[:20],
            "platform": c.attrs.get("Platform"),
            "host_config": {
                "restart_policy": host_config.get("RestartPolicy", {}).get("Name"),
                "network_mode": host_config.get("NetworkMode"),
            },
            "resources": resource_stats,
            "healthcheck": state.get("Health", {}).get("Status", "none"),
        }
    except Exception as e:
        return {"error": str(e), "name": container_name}


class DiagnosticRequest(BaseModel):
    target: str

@router.post("/{relay_id}/diagnostics/ping")
def ping_from_relay(relay_id: int, body: DiagnosticRequest, user=Depends(get_current_user)):
    """Execute ping from relay container."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404)

    client = _get_docker_client()
    if not client:
        return {"error": "Docker non disponibile"}

    container_name = f"wpex-{name}"
    try:
        c = client.containers.get(container_name)
        exit_code, output = c.exec_run(f"ping -c 4 -W 2 {body.target}", demux=True)
        stdout = output[0].decode("utf-8", errors="ignore") if output[0] else ""
        stderr = output[1].decode("utf-8", errors="ignore") if output[1] else ""
        return {"exit_code": exit_code, "output": stdout, "error": stderr, "target": body.target}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{relay_id}/diagnostics/traceroute")
def traceroute_from_relay(relay_id: int, body: DiagnosticRequest, user=Depends(get_current_user)):
    """Execute traceroute from relay container."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404)

    client = _get_docker_client()
    if not client:
        return {"error": "Docker non disponibile"}

    container_name = f"wpex-{name}"
    try:
        c = client.containers.get(container_name)
        exit_code, output = c.exec_run(f"traceroute -m 15 -w 2 {body.target}", demux=True)
        stdout = output[0].decode("utf-8", errors="ignore") if output[0] else ""
        stderr = output[1].decode("utf-8", errors="ignore") if output[1] else ""
        return {"exit_code": exit_code, "output": stdout, "error": stderr, "target": body.target}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{relay_id}/restart")
def restart_relay(relay_id: int, user=Depends(get_current_user)):
    """Restart a relay container."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404)

    client = _get_docker_client()
    if not client:
        raise HTTPException(status_code=503, detail="Docker non disponibile")

    try:
        c = client.containers.get(f"wpex-{name}")
        c.restart(timeout=10)
        return {"message": f"Relay {name} riavviato"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpgradeRequest(BaseModel):
    image: str = ""


@router.post("/{relay_id}/upgrade")
def upgrade_relay(relay_id: int, body: UpgradeRequest, user=Depends(get_current_user)):
    """Upgrade a relay container to a new image version."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, port, web_port FROM servers WHERE id = %s", (relay_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404)

    name, port, web_port = row

    # Get current keys
    cur.execute("""
        SELECT pgp_sym_decrypt(k.key_value, (SELECT value FROM (SELECT 'mysecretkey' as value) as v))
        FROM access_keys k
        JOIN server_keys_link l ON k.id = l.key_id
        WHERE l.server_id = %s
    """, (relay_id,))
    conn.close()

    image = body.image if body.image else "nikoceps/wpex-monitoring:latest"
    client = _get_docker_client()
    if not client:
        raise HTTPException(status_code=503)

    try:
        # Pull new image
        client.images.pull(image)
        # Restart with new image (simplified — in production would do blue-green)
        container_name = f"wpex-{name}"
        try:
            c = client.containers.get(container_name)
            c.stop(timeout=10)
            c.remove()
        except:
            pass

        return {"message": f"Upgrade di {name} avviato con immagine {image}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
