"""
WPEX Orchestrator — Server Management API
CRUD operations + Docker container actions.
"""
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import docker
import requests

from database import get_db, DATA_KEY
from auth import get_current_user

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
def _get_docker_client():
    """Get Docker client, return None if Docker is unavailable."""
    try:
        return docker.from_env()
    except Exception:
        return None


def _docker_status(container_name: str):
    client = _get_docker_client()
    if not client:
        return "error"
    try:
        c = client.containers.get(container_name)
        return c.status
    except docker.errors.NotFound:
        return "not_created"
    except:
        return "error"



def _deploy_container(name, udp_port, web_port, keys_list):
    client = _get_docker_client()
    if not client:
        return False, "Docker non disponibile"
    container_name = f"wpex-{name}"
    
    cmd_args = ["--stats", ":8080"]
    for k in keys_list:
        cmd_args.extend(["--allow", k])
    if not keys_list:
        cmd_args.extend(["--allow", "placeholder"])

    port_bindings = {f"{udp_port}/udp": udp_port}

    try:
        status = _docker_status(container_name)
        if status != "not_created" and client:
            client.containers.get(container_name).remove(force=True)

        client.containers.run(
            image=IMAGE_NAME,
            name=container_name,
            command=cmd_args,
            ports=port_bindings,
            network=WPEX_NETWORK,
            restart_policy={"Name": "always"},
            detach=True,
        )
        return True, "Container avviato"
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
        status = _docker_status(f"wpex-{name}")
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

        ok, msg = _deploy_container(name, body.udp_port, web_port, raw_keys)
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
    client = _get_docker_client()
    if client:
        try:
            client.containers.get(f"wpex-{name}").remove(force=True)
        except:
            pass
    
    cur.execute("DELETE FROM servers WHERE id = %s", (server_id,))
    conn.commit()
    conn.close()
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

    client = _get_docker_client()
    if client:
        try:
            client.containers.get(f"wpex-{name}").start()
        except:
            pass
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

    client = _get_docker_client()
    if client:
        try:
            client.containers.get(f"wpex-{row[0]}").stop()
        except:
            pass
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

    _deploy_container(name, udp_port, web_port, raw_keys)
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

    client = _get_docker_client()
    if not client:
        return {"logs": "Docker non disponibile."}
    try:
        logs = client.containers.get(f"wpex-{row[0]}").logs(
            tail=30, timestamps=True
        ).decode("utf-8", errors="ignore")
        return {"logs": logs}
    except:
        return {"logs": "Nessun log disponibile."}
