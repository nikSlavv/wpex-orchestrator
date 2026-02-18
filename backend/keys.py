"""
WPEX Orchestrator — Key Management API
PGP-encrypted access keys CRUD.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from database import get_db, DATA_KEY
from auth import get_current_user

router = APIRouter(prefix="/api/keys", tags=["keys"])


class CreateKeyRequest(BaseModel):
    alias: str
    key: str


@router.get("")
def list_keys(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, alias, pgp_sym_decrypt(key_value, %s) FROM access_keys ORDER BY created_at DESC",
        (DATA_KEY,),
    )
    keys = [{"id": r[0], "alias": r[1], "key": r[2]} for r in cur.fetchall()]
    conn.close()
    return {"keys": keys}


@router.post("")
def create_key(body: CreateKeyRequest, user=Depends(get_current_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO access_keys (alias, key_value) VALUES (%s, pgp_sym_encrypt(%s, %s)) RETURNING id;",
            (body.alias, body.key, DATA_KEY),
        )
        key_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return {"id": key_id, "message": "Chiave creata"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{key_id}")
def delete_key(key_id: int, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM access_keys WHERE id = %s", (key_id,))
    conn.commit()
    conn.close()
    return {"message": "Chiave eliminata"}
