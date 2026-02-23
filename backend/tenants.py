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
from audit import log_audit_event

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


# --- Pydantic Models ---
class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    max_bandwidth_mbps: int = 100
    sla_target: float = 99.9
    allowed_regions: List[str] = []
    preferred_relay_ids: List[int] = []

class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
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
        SELECT t.id, t.name, t.slug, t.max_bandwidth_mbps,
               t.sla_target, t.allowed_regions, t.preferred_relay_ids,
               t.api_key, t.is_active, t.created_at,
               (SELECT COUNT(*) FROM access_keys WHERE tenant_id = t.id) as site_count
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
            "max_bandwidth_mbps": row[3],
            "sla_target": float(row[4]), "allowed_regions": row[5] or [],
            "preferred_relay_ids": row[6] or [],
            "api_key": row[7], "is_active": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "site_count": row[10],
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
            INSERT INTO tenants (name, slug, max_bandwidth_mbps,
                                 sla_target, allowed_regions, preferred_relay_ids, api_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (body.name, body.slug.lower().replace(" ", "-"),
              body.max_bandwidth_mbps,
              body.sla_target, body.allowed_regions,
              body.preferred_relay_ids, api_key))
        tenant_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        log_audit_event(
            user_id=user["id"],
            action="create",
            entity_type="tenant",
            entity_id=tenant_id,
            details={"name": body.name, "slug": body.slug}
        )
        
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
        SELECT id, name, slug, max_bandwidth_mbps,
               sla_target, allowed_regions, preferred_relay_ids,
               api_key, billing_integration_id, is_active, created_at, updated_at
        FROM tenants WHERE id = %s
    """, (tenant_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Tenant non trovato")

    # Get sites (keys mapping)
    cur.execute("SELECT id, alias FROM access_keys WHERE tenant_id = %s ORDER BY alias", (tenant_id,))
    sites = [{"id": s[0], "alias": s[1]} for s in cur.fetchall()]

    conn.close()
    return {
        "id": row[0], "name": row[1], "slug": row[2],
        "max_bandwidth_mbps": row[3],
        "sla_target": float(row[4]), "allowed_regions": row[5] or [],
        "preferred_relay_ids": row[6] or [],
        "api_key": row[7], "billing_integration_id": row[8],
        "is_active": row[9],
        "created_at": row[10].isoformat() if row[10] else None,
        "updated_at": row[11].isoformat() if row[11] else None,
        "sites": sites,
        "usage": {
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
    values = [] # type: list
    if body.name is not None:
        updates.append("name = %s")
        values.append(body.name)
    if body.slug is not None:
        updates.append("slug = %s")
        val = str(body.slug).lower().replace(" ", "-")
        values.append(val)
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
    
    log_audit_event(
        user_id=user["id"],
        action="update",
        entity_type="tenant",
        entity_id=tenant_id,
        details={"fields_updated": [u.split(' =')[0] for u in updates if u != "updated_at = CURRENT_TIMESTAMP"]}
    )
    
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
    
    log_audit_event(
        user_id=user["id"],
        action="delete",
        entity_type="tenant",
        entity_id=tenant_id
    )
    
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
        
        log_audit_event(
            user_id=user["id"],
            action="create",
            entity_type="site",
            entity_id=site_id,
            details={"name": body.name, "tenant_id": tenant_id}
        )
        
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
    
    log_audit_event(
        user_id=user["id"],
        action="delete",
        entity_type="site",
        entity_id=site_id,
        details={"tenant_id": tenant_id}
    )
    
    return {"message": "Site eliminato"}


@router.get("/{tenant_id}/usage")
def get_tenant_usage(tenant_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("engineer", "viewer") and tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Accesso negato")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT max_bandwidth_mbps FROM tenants WHERE id = %s", (tenant_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Tenant non trovato")

    max_bw = row[0]
    cur.execute("SELECT COUNT(*) FROM sites WHERE tenant_id = %s", (tenant_id,))
    site_count = cur.fetchone()[0]

    conn.close()
    return {
        "bandwidth_limit_mbps": max_bw,
        "sites_count": site_count,
    }
