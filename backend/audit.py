"""
WPEX Orchestrator — Audit Log API
Audit logging middleware and read endpoints.
"""
import json
from fastapi import APIRouter, Depends, Request, Query
from typing import Optional, Callable
from functools import wraps

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


def log_audit_event(user_id: int, action: str, entity_type: str = None,
                    entity_id: int = None, details: dict = None, ip_address: str = None):
    """Write an audit log entry."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, action, entity_type, entity_id,
              json.dumps(details) if details else None, ip_address))
        conn.commit()
        conn.close()
    except:
        pass


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user=Depends(get_current_user)
):
    """List audit log entries with pagination and filters."""
    conn = get_db()
    cur = conn.cursor()
    offset = (page - 1) * per_page

    query = """
        SELECT a.id, a.user_id, u.username, a.action, a.entity_type,
               a.entity_id, a.details, a.ip_address, a.created_at
        FROM audit_log a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) FROM audit_log a WHERE 1=1"
    params = []
    count_params = []

    if user_id:
        query += " AND a.user_id = %s"
        count_query += " AND a.user_id = %s"
        params.append(user_id)
        count_params.append(user_id)
    if action:
        query += " AND a.action ILIKE %s"
        count_query += " AND a.action ILIKE %s"
        params.append(f"%{action}%")
        count_params.append(f"%{action}%")
    if entity_type:
        query += " AND a.entity_type = %s"
        count_query += " AND a.entity_type = %s"
        params.append(entity_type)
        count_params.append(entity_type)

    # Count
    cur.execute(count_query, count_params)
    total = cur.fetchone()[0]

    # Data
    query += " ORDER BY a.created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    cur.execute(query, params)

    logs = [{
        "id": r[0], "user_id": r[1], "username": r[2], "action": r[3],
        "entity_type": r[4], "entity_id": r[5], "details": r[6],
        "ip_address": r[7],
        "created_at": r[8].isoformat() if r[8] else None,
    } for r in cur.fetchall()]
    conn.close()

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }
