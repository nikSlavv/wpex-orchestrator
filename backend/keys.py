"""
WPEX Orchestrator — Key Management API
PGP-encrypted access keys CRUD.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from database import get_db, DATA_KEY
from auth import get_current_user
from audit import log_audit_event

router = APIRouter(prefix="/api/keys", tags=["keys"])


class CreateKeyRequest(BaseModel):
    alias: str
    key: str
    tenant_id: Optional[int] = None


@router.get("")
def list_keys(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    
    query = "SELECT id, alias, pgp_sym_decrypt(key_value, %s), tenant_id FROM access_keys "
    params = [DATA_KEY]
    
    if user.get("role") in ("engineer", "viewer"):
        query += "WHERE tenant_id = %s "
        params.append(user.get("tenant_id"))
        
    query += "ORDER BY created_at DESC"
    
    cur.execute(query, params)
    keys = [{"id": r[0], "alias": r[1], "key": r[2], "tenant_id": r[3]} for r in cur.fetchall()]
    conn.close()
    return {"keys": keys}


@router.post("")
def create_key(body: CreateKeyRequest, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti per creare chiavi")
        
    tenant_id = body.tenant_id
    if user.get("role") == "engineer":
        tenant_id = user.get("tenant_id") # Force assignment to engineer's tenant
        
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO access_keys (alias, key_value, tenant_id) VALUES (%s, pgp_sym_encrypt(%s, %s), %s) RETURNING id;",
            (body.alias, body.key, DATA_KEY, tenant_id),
        )
        key_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        log_audit_event(
            user_id=user["id"],
            action="create",
            entity_type="key",
            entity_id=key_id,
            details={"alias": body.alias}
        )
        
        return {"id": key_id, "message": "Chiave creata", "tenant_id": tenant_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{key_id}")
def delete_key(key_id: int, user=Depends(get_current_user)):
    if user.get("role") in ("viewer", "executive"):
        raise HTTPException(status_code=403, detail="Permessi insufficienti per eliminare chiavi")
        
    conn = get_db()
    cur = conn.cursor()
    
    if user.get("role") == "engineer":
        cur.execute("SELECT tenant_id FROM access_keys WHERE id = %s", (key_id,))
        row = cur.fetchone()
        if not row or row[0] != user.get("tenant_id"):
            conn.close()
            raise HTTPException(status_code=404, detail="Chiave non trovata nel tuo tenant")

    cur.execute("DELETE FROM access_keys WHERE id = %s", (key_id,))
    conn.commit()
    conn.close()
    
    log_audit_event(
        user_id=user["id"],
        action="delete",
        entity_type="key",
        entity_id=key_id
    )
    
    return {"message": "Chiave eliminata"}
