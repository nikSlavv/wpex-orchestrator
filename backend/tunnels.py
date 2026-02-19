"""
WPEX Orchestrator — Tunnel Management API
Tunnel lifecycle, config versioning, and metrics.
"""
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/tunnels", tags=["tunnels"])


# --- Pydantic Models ---
class CreateTunnelRequest(BaseModel):
    tenant_id: int
    site_a_id: int
    site_b_id: int
    relay_id: int
    config_json: dict = {}

class UpdateTunnelConfigRequest(BaseModel):
    config_json: dict


# --- Endpoints ---
@router.get("")
def list_tunnels(
    tenant_id: Optional[int] = Query(None),
    relay_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    user=Depends(get_current_user)
):
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT t.id, t.tenant_id, t.status, t.config_version, t.created_at, t.updated_at,
               sa.name as site_a_name, sa.region as site_a_region, sa.public_ip as site_a_ip,
               sb.name as site_b_name, sb.region as site_b_region, sb.public_ip as site_b_ip,
               s.name as relay_name,
               ten.name as tenant_name
        FROM tunnels t
        LEFT JOIN sites sa ON t.site_a_id = sa.id
        LEFT JOIN sites sb ON t.site_b_id = sb.id
        LEFT JOIN servers s ON t.relay_id = s.id
        LEFT JOIN tenants ten ON t.tenant_id = ten.id
        WHERE 1=1
    """
    params = []
    if tenant_id:
        query += " AND t.tenant_id = %s"
        params.append(tenant_id)
    if relay_id:
        query += " AND t.relay_id = %s"
        params.append(relay_id)
    if status:
        query += " AND t.status = %s"
        params.append(status)
    query += " ORDER BY t.created_at DESC"

    cur.execute(query, params)
    tunnels = []
    for row in cur.fetchall():
        tunnels.append({
            "id": row[0], "tenant_id": row[1], "status": row[2],
            "config_version": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
            "site_a": {"name": row[6], "region": row[7], "public_ip": row[8]},
            "site_b": {"name": row[9], "region": row[10], "public_ip": row[11]},
            "relay": row[12],
            "tenant": row[13],
        })
    conn.close()
    return {"tunnels": tunnels, "total": len(tunnels)}


@router.post("")
def create_tunnel(body: CreateTunnelRequest, user=Depends(get_current_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        # Check tenant quota
        cur.execute("SELECT max_tunnels FROM tenants WHERE id = %s", (body.tenant_id,))
        tenant = cur.fetchone()
        if not tenant:
            conn.close()
            raise HTTPException(status_code=404, detail="Tenant non trovato")

        cur.execute("SELECT COUNT(*) FROM tunnels WHERE tenant_id = %s", (body.tenant_id,))
        current_count = cur.fetchone()[0]
        if current_count >= tenant[0]:
            conn.close()
            raise HTTPException(status_code=429, detail=f"Quota tunnel raggiunta ({tenant[0]})")

        cur.execute("""
            INSERT INTO tunnels (tenant_id, site_a_id, site_b_id, relay_id, config_json, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            RETURNING id;
        """, (body.tenant_id, body.site_a_id, body.site_b_id, body.relay_id,
              json.dumps(body.config_json)))
        tunnel_id = cur.fetchone()[0]

        # Save config version 1
        cur.execute("""
            INSERT INTO relay_config_versions (relay_id, version, config_json, created_by)
            VALUES (%s, 1, %s, %s)
            ON CONFLICT (relay_id, version) DO NOTHING;
        """, (body.relay_id, json.dumps(body.config_json), user["id"]))

        conn.commit()
        conn.close()
        return {"id": tunnel_id, "message": "Tunnel creato e attivo"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tunnel_id}")
def get_tunnel(tunnel_id: int, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.tenant_id, t.site_a_id, t.site_b_id, t.relay_id,
               t.status, t.config_json, t.config_version, t.created_at, t.updated_at,
               sa.name, sa.region, sa.public_ip,
               sb.name, sb.region, sb.public_ip,
               s.name as relay_name,
               ten.name as tenant_name
        FROM tunnels t
        LEFT JOIN sites sa ON t.site_a_id = sa.id
        LEFT JOIN sites sb ON t.site_b_id = sb.id
        LEFT JOIN servers s ON t.relay_id = s.id
        LEFT JOIN tenants ten ON t.tenant_id = ten.id
        WHERE t.id = %s
    """, (tunnel_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Tunnel non trovato")

    conn.close()
    return {
        "id": row[0], "tenant_id": row[1],
        "site_a": {"id": row[2], "name": row[10], "region": row[11], "public_ip": row[12]},
        "site_b": {"id": row[3], "name": row[13], "region": row[14], "public_ip": row[15]},
        "relay": {"id": row[4], "name": row[16]},
        "tenant": row[17],
        "status": row[5], "config": row[6], "config_version": row[7],
        "created_at": row[8].isoformat() if row[8] else None,
        "updated_at": row[9].isoformat() if row[9] else None,
    }


@router.delete("/{tunnel_id}")
def delete_tunnel(tunnel_id: int, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tunnels WHERE id = %s", (tunnel_id,))
    conn.commit()
    conn.close()
    return {"message": "Tunnel eliminato"}


@router.put("/{tunnel_id}/config")
def update_tunnel_config(tunnel_id: int, body: UpdateTunnelConfigRequest, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    # Get current version
    cur.execute("SELECT config_version, relay_id, config_json FROM tunnels WHERE id = %s", (tunnel_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404)

    new_version = row[0] + 1
    relay_id = row[1]
    old_config = row[2]

    # Compute simple diff
    diff = {"previous": old_config, "new": body.config_json}

    # Update tunnel
    cur.execute("""
        UPDATE tunnels SET config_json = %s, config_version = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (json.dumps(body.config_json), new_version, tunnel_id))

    # Save version
    cur.execute("""
        INSERT INTO relay_config_versions (relay_id, version, config_json, diff_from_previous, created_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (relay_id, new_version, json.dumps(body.config_json), json.dumps(diff), user["id"]))

    conn.commit()
    conn.close()
    return {"message": "Configurazione aggiornata", "version": new_version}


@router.get("/{tunnel_id}/config/history")
def get_config_history(tunnel_id: int, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT relay_id FROM tunnels WHERE id = %s", (tunnel_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404)

    cur.execute("""
        SELECT v.id, v.version, v.config_json, v.diff_from_previous, v.created_at,
               u.username
        FROM relay_config_versions v
        LEFT JOIN users u ON v.created_by = u.id
        WHERE v.relay_id = %s
        ORDER BY v.version DESC
    """, (row[0],))

    versions = [{
        "id": r[0], "version": r[1], "config": r[2], "diff": r[3],
        "created_at": r[4].isoformat() if r[4] else None,
        "created_by": r[5],
    } for r in cur.fetchall()]
    conn.close()
    return {"versions": versions}


@router.post("/{tunnel_id}/config/rollback/{version}")
def rollback_config(tunnel_id: int, version: int, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT relay_id FROM tunnels WHERE id = %s", (tunnel_id,))
    trow = cur.fetchone()
    if not trow:
        conn.close()
        raise HTTPException(status_code=404)

    cur.execute("""
        SELECT config_json FROM relay_config_versions
        WHERE relay_id = %s AND version = %s
    """, (trow[0], version))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Versione {version} non trovata")

    # Get current version
    cur.execute("SELECT config_version FROM tunnels WHERE id = %s", (tunnel_id,))
    current = cur.fetchone()[0]
    new_version = current + 1

    # Create new version from old config (rollback is a new version)
    cur.execute("""
        UPDATE tunnels SET config_json = %s, config_version = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (json.dumps(row[0]), new_version, tunnel_id))

    cur.execute("""
        INSERT INTO relay_config_versions (relay_id, version, config_json, diff_from_previous, created_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (trow[0], new_version, json.dumps(row[0]),
          json.dumps({"action": "rollback", "from_version": current, "to_version": version}),
          user["id"]))

    conn.commit()
    conn.close()
    return {"message": f"Rollback alla versione {version} completato", "new_version": new_version}
