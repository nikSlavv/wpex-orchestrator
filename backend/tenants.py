"""
WPEX Orchestrator — Tenant Management API
Multi-tenant CRUD with quota enforcement.
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from database import get_db, generate_api_key
from auth import get_current_user

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


# --- Pydantic Models ---
class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    max_tunnels: int = 10
    max_bandwidth_mbps: int = 100
    sla_target: float = 99.9
    allowed_regions: List[str] = []
    preferred_relay_ids: List[int] = []

class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    max_tunnels: Optional[int] = None
    max_bandwidth_mbps: Optional[int] = None
    sla_target: Optional[float] = None
    allowed_regions: Optional[List[str]] = None
    preferred_relay_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None

class CreateSiteRequest(BaseModel):
    name: str
    region: str = ""
    public_ip: str = ""
    subnet: str = ""


# --- Tenant Endpoints ---
@router.get("")
def list_tenants(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    
    is_tenant_scoped = user.get("role") in ("engineer", "viewer")
    tenant_id = user.get("tenant_id")
    
    query = """
        SELECT t.id, t.name, t.slug, t.max_tunnels, t.max_bandwidth_mbps,
               t.sla_target, t.allowed_regions, t.preferred_relay_ids,
               t.api_key, t.is_active, t.created_at,
               (SELECT COUNT(*) FROM tunnels WHERE tenant_id = t.id) as tunnel_count,
               (SELECT COUNT(*) FROM sites WHERE tenant_id = t.id) as site_count
        FROM tenants t
    """
    params = []
    if is_tenant_scoped:
        query += " WHERE t.id = %s"
        params.append(tenant_id)
        
    query += " ORDER BY t.name ASC"
    
    cur.execute(query, params)
    tenants = []
    for row in cur.fetchall():
        tenants.append({
            "id": row[0], "name": row[1], "slug": row[2],
            "max_tunnels": row[3], "max_bandwidth_mbps": row[4],
            "sla_target": float(row[5]), "allowed_regions": row[6] or [],
            "preferred_relay_ids": row[7] or [],
            "api_key": row[8], "is_active": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "tunnel_count": row[11], "site_count": row[12],
            "tunnel_usage_pct": round((row[11] / row[3] * 100) if row[3] > 0 else 0, 1),
        })
    conn.close()
    return {"tenants": tenants}


@router.post("")
def create_tenant(body: CreateTenantRequest, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo gli admin possono creare tenant")
        
    conn = get_db()
    try:
        cur = conn.cursor()
        api_key = generate_api_key()
        cur.execute("""
            INSERT INTO tenants (name, slug, max_tunnels, max_bandwidth_mbps,
                                 sla_target, allowed_regions, preferred_relay_ids, api_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (body.name, body.slug.lower().replace(" ", "-"),
              body.max_tunnels, body.max_bandwidth_mbps,
              body.sla_target, body.allowed_regions,
              body.preferred_relay_ids, api_key))
        tenant_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return {"id": tenant_id, "api_key": api_key, "message": "Tenant creato"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tenant_id}")
def get_tenant(tenant_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("engineer", "viewer") and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Accesso negato")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, slug, max_tunnels, max_bandwidth_mbps,
               sla_target, allowed_regions, preferred_relay_ids,
               api_key, billing_integration_id, is_active, created_at, updated_at
        FROM tenants WHERE id = %s
    """, (tenant_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Tenant non trovato")

    # Get sites
    cur.execute("SELECT id, name, region, public_ip, subnet, is_active FROM sites WHERE tenant_id = %s ORDER BY name", (tenant_id,))
    sites = [{"id": s[0], "name": s[1], "region": s[2], "public_ip": s[3], "subnet": s[4], "is_active": s[5]} for s in cur.fetchall()]

    # Get tunnels
    cur.execute("""
        SELECT t.id, t.status, t.config_version,
               sa.name as site_a, sb.name as site_b,
               s.name as relay_name
        FROM tunnels t
        LEFT JOIN sites sa ON t.site_a_id = sa.id
        LEFT JOIN sites sb ON t.site_b_id = sb.id
        LEFT JOIN servers s ON t.relay_id = s.id
        WHERE t.tenant_id = %s
    """, (tenant_id,))
    tunnels = [{"id": t[0], "status": t[1], "config_version": t[2],
                "site_a": t[3], "site_b": t[4], "relay": t[5]} for t in cur.fetchall()]

    conn.close()
    return {
        "id": row[0], "name": row[1], "slug": row[2],
        "max_tunnels": row[3], "max_bandwidth_mbps": row[4],
        "sla_target": float(row[5]), "allowed_regions": row[6] or [],
        "preferred_relay_ids": row[7] or [],
        "api_key": row[8], "billing_integration_id": row[9],
        "is_active": row[10],
        "created_at": row[11].isoformat() if row[11] else None,
        "updated_at": row[12].isoformat() if row[12] else None,
        "sites": sites, "tunnels": tunnels,
        "usage": {
            "tunnels_used": len(tunnels),
            "tunnels_limit": row[3],
            "tunnels_pct": round(len(tunnels) / row[3] * 100, 1) if row[3] > 0 else 0,
            "sites_count": len(sites),
        }
    }


@router.put("/{tenant_id}")
def update_tenant(tenant_id: int, body: UpdateTenantRequest, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo gli admin possono modificare i tenant")

    conn = get_db()
    cur = conn.cursor()
    updates = []
    values = []
    if body.name is not None:
        updates.append("name = %s")
        values.append(body.name)
    if body.max_tunnels is not None:
        updates.append("max_tunnels = %s")
        values.append(body.max_tunnels)
    if body.max_bandwidth_mbps is not None:
        updates.append("max_bandwidth_mbps = %s")
        values.append(body.max_bandwidth_mbps)
    if body.sla_target is not None:
        updates.append("sla_target = %s")
        values.append(body.sla_target)
    if body.allowed_regions is not None:
        updates.append("allowed_regions = %s")
        values.append(body.allowed_regions)
    if body.preferred_relay_ids is not None:
        updates.append("preferred_relay_ids = %s")
        values.append(body.preferred_relay_ids)
    if body.is_active is not None:
        updates.append("is_active = %s")
        values.append(body.is_active)

    if not updates:
        conn.close()
        return {"message": "Nessun aggiornamento"}

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(tenant_id)
    cur.execute(f"UPDATE tenants SET {', '.join(updates)} WHERE id = %s", values)
    conn.commit()
    conn.close()
    return {"message": "Tenant aggiornato"}


@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: int, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo gli admin possono eliminare i tenant")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
    conn.commit()
    conn.close()
    return {"message": "Tenant eliminato"}


# --- Site Endpoints ---
@router.get("/{tenant_id}/sites")
def list_sites(tenant_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("engineer", "viewer") and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Accesso negato")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, region, public_ip, subnet, is_active, created_at
        FROM sites WHERE tenant_id = %s ORDER BY name
    """, (tenant_id,))
    sites = [{
        "id": r[0], "name": r[1], "region": r[2],
        "public_ip": r[3], "subnet": r[4], "is_active": r[5],
        "created_at": r[6].isoformat() if r[6] else None,
    } for r in cur.fetchall()]
    conn.close()
    return {"sites": sites}


@router.post("/{tenant_id}/sites")
def create_site(tenant_id: int, body: CreateSiteRequest, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti per creare site")
    if user.get("role") == "engineer" and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Accesso negato")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sites (tenant_id, name, region, public_ip, subnet)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """, (tenant_id, body.name, body.region, body.public_ip, body.subnet))
        site_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return {"id": site_id, "message": "Site creato"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tenant_id}/sites/{site_id}")
def delete_site(tenant_id: int, site_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti per eliminare site")
    if user.get("role") == "engineer" and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Accesso negato")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sites WHERE id = %s AND tenant_id = %s", (site_id, tenant_id))
    conn.commit()
    conn.close()
    return {"message": "Site eliminato"}


@router.get("/{tenant_id}/usage")
def get_tenant_usage(tenant_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("engineer", "viewer") and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Accesso negato")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT max_tunnels, max_bandwidth_mbps FROM tenants WHERE id = %s", (tenant_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Tenant non trovato")

    max_tunnels, max_bw = row
    cur.execute("SELECT COUNT(*) FROM tunnels WHERE tenant_id = %s", (tenant_id,))
    tunnel_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tunnels WHERE tenant_id = %s AND status = 'active'", (tenant_id,))
    active_tunnels = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sites WHERE tenant_id = %s", (tenant_id,))
    site_count = cur.fetchone()[0]

    conn.close()
    return {
        "tunnels_used": tunnel_count,
        "tunnels_active": active_tunnels,
        "tunnels_limit": max_tunnels,
        "tunnels_pct": round(tunnel_count / max_tunnels * 100, 1) if max_tunnels > 0 else 0,
        "bandwidth_limit_mbps": max_bw,
        "sites_count": site_count,
        "soft_quota_warning": tunnel_count >= (max_tunnels * 0.8),
    }
