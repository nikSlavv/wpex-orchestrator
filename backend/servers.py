"""
WPEX Orchestrator — Server Management API
CRUD operations + Docker container actions.
"""
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import requests

from database import get_db, DATA_KEY
from auth import get_current_user
from audit import log_audit_event

router = APIRouter(prefix="/api/servers", tags=["servers"])

IMAGE_NAME = "nikoceps/wpex-monitoring:latest"
WPEX_NETWORK = os.getenv("WPEX_NETWORK", "wpex_wpex-network")


def _get_public_ip():
    try:
        return os.getenv("HOST_IP", requests.get("https://api.ipify.org", timeout=1).text)
    except:
        return "localhost"


# --- Pydantic Models ---
class CreateServerRequest(BaseModel):
    name: str
    udp_port: int
    key_ids: List[int]
    tenant_id: Optional[int] = None
    region: str = ""
    description: str = ""

class UpdateKeysRequest(BaseModel):
    key_ids: List[int]


# --- Docker Helpers ---
# --- Kubernetes Helpers ---
def _init_k8s():
    try:
        config.load_incluster_config()
    except:
        try:
            config.load_kube_config()
        except:
            pass

def _k8s_status(name: str):
    _init_k8s()
    try:
        core_api = client.CoreV1Api()
        pods = core_api.list_namespaced_pod(namespace="wpex", label_selector=f"app=wpex-{name}")
        if not pods.items:
            apps_api = client.AppsV1Api()
            try:
                apps_api.read_namespaced_deployment(name=f"wpex-{name}", namespace="wpex")
                return "stopped"
            except:
                return "not_created"
        
        pod = pods.items[0]
        return pod.status.phase.lower()
    except Exception:
        return "error"

def _deploy_relay(name, udp_port, web_port, keys_list):
    _init_k8s()
    app_name = f"wpex-{name}"
    
    cmd_args = ["--stats", ":8080"]
    for k in keys_list:
        cmd_args.extend(["--allow", k])
    if not keys_list:
        cmd_args.extend(["--allow", "placeholder"])

    apps_api = client.AppsV1Api()
    core_api = client.CoreV1Api()

    container = client.V1Container(
        name="relay",
        image=IMAGE_NAME,
        args=cmd_args,
        ports=[
            client.V1ContainerPort(container_port=udp_port, host_port=udp_port, protocol="UDP"),
            client.V1ContainerPort(container_port=8080, protocol="TCP")
        ],
        security_context=client.V1SecurityContext(capabilities=client.V1Capabilities(add=["NET_ADMIN"]))
    )
    
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": app_name}),
        spec=client.V1PodSpec(containers=[container])
    )
    
    spec = client.V1DeploymentSpec(
        replicas=1,
        selector=client.V1LabelSelector(match_labels={"app": app_name}),
        template=template
    )
    
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=app_name),
        spec=spec
    )

    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=app_name),
        spec=client.V1ServiceSpec(
            selector={"app": app_name},
            ports=[
                client.V1ServicePort(name="udp", port=udp_port, target_port=udp_port, protocol="UDP"),
                client.V1ServicePort(name="http", port=8080, target_port=8080, protocol="TCP")
            ],
            type="NodePort"
        )
    )

    try:
        try:
            apps_api.read_namespaced_deployment(name=app_name, namespace="wpex")
            apps_api.patch_namespaced_deployment(name=app_name, namespace="wpex", body=deployment)
        except ApiException as e:
            if e.status == 404:
                apps_api.create_namespaced_deployment(namespace="wpex", body=deployment)
            else:
                return False, str(e)
                
        try:
            core_api.read_namespaced_service(name=app_name, namespace="wpex")
            core_api.patch_namespaced_service(name=app_name, namespace="wpex", body=service)
        except ApiException as e:
            if e.status == 404:
                core_api.create_namespaced_service(namespace="wpex", body=service)
            else:
                return False, str(e)

        return True, "Relay avviato su Kubernetes"
    except Exception as e:
        return False, str(e)


@router.get("")
def list_servers(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    
    query = "SELECT id, name, port, web_port, tenant_id, region, description FROM servers "
    params = []
    
    if user.get("role") in ("engineer", "viewer"):
        query += "WHERE tenant_id = %s "
        params.append(user.get("tenant_id"))
        
    query += "ORDER BY port ASC"
    
    cur.execute(query, params)
    servers = []
    for row in cur.fetchall():
        sid, name, udp_port, web_port, tenant_id, region, description = row
        cur.execute(
            """SELECT k.id, k.alias, pgp_sym_decrypt(k.key_value, %s)
               FROM access_keys k
               JOIN server_keys_link l ON k.id = l.key_id
               WHERE l.server_id = %s""",
            (DATA_KEY, sid),
        )
        keys_data = [{"id": k[0], "alias": k[1], "key": k[2]} for k in cur.fetchall()]
        status = _k8s_status(name)
        servers.append({
            "id": sid, "name": name, "udp_port": udp_port, "web_port": web_port,
            "tenant_id": tenant_id, "region": region, "description": description,
            "keys": keys_data, "status": status,
        })
    conn.close()
    return {"servers": servers, "host_ip": _get_public_ip()}


@router.post("")
def create_server(body: CreateServerRequest, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti per creare server")

    tenant_id = body.tenant_id
    if user.get("role") == "engineer":
        tenant_id = user.get("tenant_id")
        
    conn = get_db()
    cur = conn.cursor()

    # Get next web port
    cur.execute("SELECT MAX(web_port) FROM servers")
    max_port = cur.fetchone()[0]
    web_port = (max_port + 1) if max_port else 8080

    name = body.name.lower().replace(" ", "-")
    
    try:
        cur.execute(
            """INSERT INTO servers (name, port, web_port, tenant_id, region, description) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, body.udp_port, web_port, tenant_id, body.region, body.description),
        )
        server_id = cur.fetchone()[0]
        for kid in body.key_ids:
            cur.execute("INSERT INTO server_keys_link (server_id, key_id) VALUES (%s, %s)", (server_id, kid))
        conn.commit()

        # Get actual key values for Docker
        cur.execute(
            "SELECT pgp_sym_decrypt(key_value, %s) FROM access_keys WHERE id = ANY(%s)",
            (DATA_KEY, body.key_ids),
        )
        raw_keys = [r[0] for r in cur.fetchall()]
        conn.close()

        ok, msg = _deploy_relay(name, body.udp_port, web_port, raw_keys)
        
        log_audit_event(
            user_id=user["id"],
            action="create",
            entity_type="relay",
            entity_id=server_id,
            details={"name": name, "udp_port": body.udp_port}
        )
        
        if not ok:
            return {"id": server_id, "warning": msg}
        return {"id": server_id, "message": "Server creato e avviato"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{server_id}")
def delete_server(server_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, tenant_id FROM servers WHERE id = %s", (server_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Server non trovato")
        
    name, tenant_id = row
    if user.get("role") == "engineer" and tenant_id != user.get("tenant_id"):
        conn.close()
        raise HTTPException(status_code=403, detail="Server non appartiene alla tua organizzazione")
    _init_k8s()
    try:
        apps_api = client.AppsV1Api()
        core_api = client.CoreV1Api()
        apps_api.delete_namespaced_deployment(name=f"wpex-{name}", namespace="wpex")
        core_api.delete_namespaced_service(name=f"wpex-{name}", namespace="wpex")
    except:
        pass
    
    cur.execute("DELETE FROM servers WHERE id = %s", (server_id,))
    conn.commit()
    conn.close()
    
    log_audit_event(
        user_id=user["id"],
        action="delete",
        entity_type="relay",
        entity_id=server_id,
        details={"name": name}
    )
    
    return {"message": f"Server {name} eliminato"}


@router.post("/{server_id}/start")
def start_server(server_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
        
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, tenant_id FROM servers WHERE id = %s", (server_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404)
        
    name, tenant_id = row
    if user.get("role") == "engineer" and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Server non appartiene alla tua organizzazione")

    _init_k8s()
    try:
        apps_api = client.AppsV1Api()
        deployment = apps_api.read_namespaced_deployment(name=f"wpex-{name}", namespace="wpex")
        deployment.spec.replicas = 1
        apps_api.patch_namespaced_deployment(name=f"wpex-{name}", namespace="wpex", body=deployment)
    except:
        pass
            
    log_audit_event(
        user_id=user["id"],
        action="start",
        entity_type="relay",
        entity_id=server_id,
        details={"name": name}
    )
    
    return {"message": "Avviato"}


@router.post("/{server_id}/stop")
def stop_server(server_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
        
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, tenant_id FROM servers WHERE id = %s", (server_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404)
        
    name, tenant_id = row
    if user.get("role") == "engineer" and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Server non appartiene alla tua organizzazione")

    _init_k8s()
    try:
        apps_api = client.AppsV1Api()
        deployment = apps_api.read_namespaced_deployment(name=f"wpex-{name}", namespace="wpex")
        deployment.spec.replicas = 0
        apps_api.patch_namespaced_deployment(name=f"wpex-{name}", namespace="wpex", body=deployment)
    except:
        pass
            
    log_audit_event(
        user_id=user["id"],
        action="stop",
        entity_type="relay",
        entity_id=server_id,
        details={"name": name}
    )
    
    return {"message": "Fermato"}


@router.put("/{server_id}/keys")
def update_keys(server_id: int, body: UpdateKeysRequest, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
        
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, port, web_port, tenant_id FROM servers WHERE id = %s", (server_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404)
    
    name, udp_port, web_port, tenant_id = row
    
    if user.get("role") == "engineer" and tenant_id != user.get("tenant_id"):
        conn.close()
        raise HTTPException(status_code=403, detail="Server non appartiene alla tua organizzazione")

    cur.execute("DELETE FROM server_keys_link WHERE server_id = %s", (server_id,))
    for kid in body.key_ids:
        cur.execute("INSERT INTO server_keys_link (server_id, key_id) VALUES (%s, %s)", (server_id, kid))
    conn.commit()

    # Redeploy with new keys
    cur.execute(
        "SELECT pgp_sym_decrypt(key_value, %s) FROM access_keys WHERE id = ANY(%s)",
        (DATA_KEY, body.key_ids),
    )
    raw_keys = [r[0] for r in cur.fetchall()]
    conn.close()

    _deploy_relay(name, udp_port, web_port, raw_keys)
    
    log_audit_event(
        user_id=user["id"],
        action="update_keys",
        entity_type="relay",
        entity_id=server_id,
        details={"name": name, "key_count": len(body.key_ids)}
    )
    
    return {"message": "Chiavi aggiornate e server riavviato"}


@router.get("/{server_id}/logs")
def get_logs(server_id: int, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, tenant_id FROM servers WHERE id = %s", (server_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404)
        
    name, tenant_id = row
    if user.get("role") in ("engineer", "viewer") and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Server non appartiene alla tua organizzazione")

    _init_k8s()
    try:
        core_api = client.CoreV1Api()
        pods = core_api.list_namespaced_pod(namespace="wpex", label_selector=f"app=wpex-{name}")
        if not pods.items:
            return {"logs": "Nessun pod attivo trovato."}
        
        pod_name = pods.items[0].metadata.name
        logs = core_api.read_namespaced_pod_log(name=pod_name, namespace="wpex", tail_lines=30)
        return {"logs": logs}
    except Exception as e:
        return {"logs": f"Errore nel recupero log: {str(e)}"}
