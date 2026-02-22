"""
WPEX Orchestrator — Authentication API
JWT-based auth with token blacklisting.
"""
import os, datetime, uuid
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel
import jwt
import psycopg2

from database import get_db, _read_secret

# --- JWT Config ---
JWT_SECRET = _read_secret("jwt_secret") or os.getenv(
    "JWT_SECRET", "changeme_super_long_fallback_secret_key_32bytes_minimum"
)
JWT_ALGORITHM = "HS256"
JWT_EXP_DAYS = 7

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Pydantic Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    tenant_id: int


# --- JWT Helpers ---
def create_jwt_token(user_id: int, username: str):
    exp = datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXP_DAYS)
    jti = str(uuid.uuid4())
    payload = {"sub": str(user_id), "name": username, "exp": exp, "jti": jti}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, exp


def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Check blacklist
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM token_blacklist WHERE jti = %s", (payload["jti"],))
        if cur.fetchone():
            conn.close()
            return None
        conn.close()
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user_any_status(request: Request):
    """Dependency that extracts user and role/tenant but DOES NOT block pending users."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("wpex_session")
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")

    user_id = int(payload["sub"])
    role = "engineer"
    tenant_id = None
    status = "active"
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT role, tenant_id, status FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            role = row[0] or "engineer"
            tenant_id = row[1]
            status = row[2] or "active"
        conn.close()
    except:
        pass

    return {"id": user_id, "username": payload["name"], "token": token,
            "role": role, "tenant_id": tenant_id, "status": status}


def get_current_user(user=Depends(get_current_user_any_status)):
    """FastAPI dependency: same as above but BLOCKS users that are not 'active'."""
    if user["status"] != "active":
        raise HTTPException(
            status_code=403, 
            detail="Account non attivo o in attesa di approvazione",
            headers={"X-User-Status": user["status"]}
        )
    return user


# --- Endpoints ---
@router.post("/login")
def login(body: LoginRequest, response: Response):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, status FROM users WHERE username = %s AND password_hash = crypt(%s, password_hash);",
        (body.username, body.password),
    )
    user = cur.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    token, exp = create_jwt_token(user[0], user[1])
    response.set_cookie(
        "wpex_session", token,
        httponly=True, samesite="lax",
        expires=exp.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    return {"token": token, "username": user[1], "expires": exp.isoformat(), "status": user[2] or "active"}


@router.post("/register")
def register(body: RegisterRequest):
    conn = get_db()
    try:
        cur = conn.cursor()
        # Verify tenant exists
        cur.execute("SELECT id FROM tenants WHERE id = %s AND is_active = TRUE", (body.tenant_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail="Organizzazione non valida o inattiva")
        
        # Insert user as pending with viewer role
        cur.execute(
            "INSERT INTO users (username, password_hash, status, role, tenant_id) VALUES (%s, crypt(%s, gen_salt('bf')), 'pending', 'viewer', %s);",
            (body.username, body.password, body.tenant_id),
        )
        conn.commit()
        conn.close()
        return {"message": "Registrazione completata. Il tuo account è in attesa di approvazione da parte della tua organizzazione."}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Username già esistente")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
def logout(response: Response, user=Depends(get_current_user)):
    # Blacklist the current token
    try:
        payload = jwt.decode(user["token"], options={"verify_signature": False})
        conn = get_db()
        cur = conn.cursor()
        expires_at = datetime.datetime.fromtimestamp(payload["exp"])
        cur.execute(
            "INSERT INTO token_blacklist (jti, expires_at) VALUES (%s, %s)",
            (payload["jti"], expires_at),
        )
        conn.commit()
        conn.close()
    except:
        pass

    response.delete_cookie("wpex_session")
    return {"message": "Logout effettuato"}


@router.get("/me")
def me(user=Depends(get_current_user_any_status)):
    return {"id": user["id"], "username": user["username"],
            "role": user.get("role", "engineer"), "tenant_id": user.get("tenant_id"),
            "status": user.get("status", "active")}


@router.get("/users")
def list_users(user=Depends(get_current_user)):
    # Admin sees all. Engineer sees only their tenant's users.
    conn = get_db()
    cur = conn.cursor()
    if user.get("role") == "admin":
        cur.execute("SELECT id, username, role, tenant_id, created_at, status FROM users ORDER BY id")
    elif user.get("role") == "engineer":
        cur.execute("SELECT id, username, role, tenant_id, created_at, status FROM users WHERE tenant_id = %s ORDER BY id", (user["tenant_id"],))
    else:
        conn.close()
        raise HTTPException(status_code=403, detail="Solo gli admin e gli engineer possono visualizzare gli utenti")
    
    rows = cur.fetchall()
    conn.close()
    return {"users": [{"id": r[0], "username": r[1], "role": r[2] or "engineer",
                        "tenant_id": r[3], "created_at": str(r[4]) if r[4] else None,
                        "status": r[5] or "active"} for r in rows]}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, body: dict, user=Depends(get_current_user)):
    role = body.get("role")
    if role not in ("admin", "executive", "engineer", "viewer"):
        raise HTTPException(status_code=400, detail="Ruolo non valido")
        
    conn = get_db()
    cur = conn.cursor()
    
    # RBAC rules
    if user.get("role") == "admin":
        pass # Admin can do anything
    elif user.get("role") == "engineer":
        if role in ("admin", "executive"):
            conn.close()
            raise HTTPException(status_code=403, detail="Non puoi assegnare un ruolo con visibilità globale")
            
        # Ensure user belongs to the same tenant
        cur.execute("SELECT tenant_id FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row or row[0] != user.get("tenant_id"):
            conn.close()
            raise HTTPException(status_code=403, detail="Puoi gestire solo utenti del tuo tenant")
    else:
        conn.close()
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    cur.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
    conn.commit()
    conn.close()
    return {"message": "Ruolo aggiornato", "user_id": user_id, "role": role}


@router.put("/users/{user_id}/tenant")
def update_user_tenant(user_id: int, body: dict, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo gli admin possono assegnare tenant")
    tenant_id = body.get("tenant_id")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET tenant_id = %s WHERE id = %s", (tenant_id, user_id))
    conn.commit()
    conn.close()
    return {"message": "Tenant aggiornato", "user_id": user_id, "tenant_id": tenant_id}


@router.put("/users/{user_id}/status")
def update_user_status(user_id: int, body: dict, user=Depends(get_current_user)):
    # RBAC Check: admin can do anything. Engineer can manage users in their tenant.
    if user.get("role") == "admin":
        pass
    elif user.get("role") == "engineer":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT tenant_id FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row or row[0] != user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Puoi gestire solo utenti del tuo tenant")
    else:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    status = body.get("status")
    if status not in ("pending", "active", "disabled"):
        raise HTTPException(status_code=400, detail="Status non valido")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
    conn.commit()
    conn.close()
    return {"message": "Status aggiornato", "user_id": user_id, "status": status}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo gli admin possono eliminare utenti")
    
    # Prevent self-deletion
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Non puoi eliminare te stesso")

    conn = get_db()
    cur = conn.cursor()
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato")
        
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return {"message": "Utente eliminato con successo", "user_id": user_id}


@router.get("/public/tenants")
def list_public_tenants():
    """Publicly accessible list of tenants for registration."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM tenants WHERE is_active = TRUE ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return {"tenants": [{"id": r[0], "name": r[1]} for r in rows]}

