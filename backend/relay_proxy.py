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

def _get_k8s_pod_info(name):
    from kubernetes import client
    _init_k8s()
    try:
        core_api = client.CoreV1Api()
        pods = core_api.list_namespaced_pod(namespace="wpex", label_selector=f"app=wpex-{name}")
        if not pods.items:
            return {"status": "not_found", "restart_count": 0, "image": None, "started_at": None, "pod_name": None}
        
        pod = pods.items[0]
        status = pod.status.phase.lower()
        restart_count = sum([c.restart_count for c in pod.status.container_statuses]) if pod.status.container_statuses else 0
        image = pod.spec.containers[0].image
        started_at = pod.status.start_time.isoformat() if pod.status.start_time else None
        return {
            "status": "running" if status == "running" else status,
            "restart_count": restart_count,
            "image": image,
            "started_at": started_at,
            "pod_name": pod.metadata.name,
            "node_name": pod.spec.node_name
        }
    except:
        return {"status": "error", "restart_count": 0, "image": None, "started_at": None, "pod_name": None}


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
        resp = http_requests.get(f"http://{container_name}.wpex.svc.cluster.local:8080/stats", timeout=3)
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

    # K8s status
    docker_info = _get_k8s_pod_info(name)
    docker_info["uptime"] = None

    # WPEX stats
    stats = None
    try:
        resp = http_requests.get(f"http://{container_name}.wpex.svc.cluster.local:8080/stats", timeout=2)
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
    docker_info = _get_k8s_pod_info(name)
    if not docker_info.get("pod_name"):
        return {"error": "Pod non disponibile", "name": container_name}

    try:
        # Get resource stats from Metrics Server if available
        resource_stats = {}
        try:
            from kubernetes import client
            api = client.CustomObjectsApi()
            k8s_metrics = api.get_namespaced_custom_object(
                "metrics.k8s.io", "v1beta1", "wpex", "pods", docker_info["pod_name"]
            )
            containers = k8s_metrics.get("containers", [])
            if containers:
                usage = containers[0].get("usage", {})
                resource_stats["cpu_pct"] = usage.get("cpu", "N/A")
                resource_stats["memory_usage_mb"] = usage.get("memory", "N/A")
        except:
            pass

        return {
            "name": docker_info["pod_name"],
            "status": docker_info["status"],
            "started_at": docker_info["started_at"],
            "restart_count": docker_info["restart_count"],
            "image": docker_info["image"],
            "node_name": docker_info.get("node_name"),
            "resources": resource_stats,
            "healthcheck": "none",
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

    docker_info = _get_k8s_pod_info(name)
    if not docker_info.get("pod_name"):
        return {"error": "Pod non disponibile"}

    try:
        from kubernetes import client
        from kubernetes.stream import stream
        core_api = client.CoreV1Api()
        
        exec_command = ["/bin/sh", "-c", f"ping -c 4 -W 2 {body.target}"]
        resp = stream(
            core_api.connect_get_namespaced_pod_exec,
            docker_info["pod_name"],
            "wpex",
            command=exec_command,
            stderr=True, stdin=False,
            stdout=True, tty=False
        )
        return {"exit_code": 0, "output": resp, "error": "", "target": body.target}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{relay_id}/diagnostics/traceroute")
def traceroute_from_relay(relay_id: int, body: DiagnosticRequest, user=Depends(get_current_user)):
    """Execute traceroute from relay container."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404)

    docker_info = _get_k8s_pod_info(name)
    if not docker_info.get("pod_name"):
        return {"error": "Pod non disponibile"}

    try:
        from kubernetes import client
        from kubernetes.stream import stream
        core_api = client.CoreV1Api()
        
        exec_command = ["/bin/sh", "-c", f"traceroute -m 15 -w 2 {body.target}"]
        resp = stream(
            core_api.connect_get_namespaced_pod_exec,
            docker_info["pod_name"],
            "wpex",
            command=exec_command,
            stderr=True, stdin=False,
            stdout=True, tty=False
        )
        return {"exit_code": 0, "output": resp, "error": "", "target": body.target}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{relay_id}/restart")
def restart_relay(relay_id: int, user=Depends(get_current_user)):
    """Restart a relay container."""
    name = _get_relay_name(relay_id)
    if not name:
        raise HTTPException(status_code=404)

    try:
        from kubernetes import client
        _init_k8s()
        apps_api = client.AppsV1Api()
        import datetime
        patch = {'spec': {'template': {'metadata': {'annotations': {'wpex.io/restartedAt': str(datetime.datetime.now())}}}}}
        apps_api.patch_namespaced_deployment(name=f"wpex-{name}", namespace="wpex", body=patch)
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
    image = body.image if body.image else "nikoceps/wpex-monitoring:latest"

    try:
        from kubernetes import client
        _init_k8s()
        apps_api = client.AppsV1Api()
        patch = {'spec': {'template': {'spec': {'containers': [{'name': 'relay', 'image': image}]}}}}
        apps_api.patch_namespaced_deployment(name=f"wpex-{name}", namespace="wpex", body=patch)
        return {"message": f"Upgrade di {name} avviato con immagine {image}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
