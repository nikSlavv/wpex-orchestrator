"""
WPEX Orchestrator — FastAPI Entry Point
SaaS multi-tenant VPN dashboard API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, migrate_db
from auth import router as auth_router
from servers import router as servers_router
from keys import router as keys_router
from tenants import router as tenants_router
from dashboard_kpi import router as dashboard_router
from relay_proxy import router as relay_proxy_router
from audit import router as audit_router

app = FastAPI(title="WPEX Orchestrator SaaS API", version="3.0")

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(servers_router)
app.include_router(keys_router)
app.include_router(tenants_router)
app.include_router(dashboard_router)
app.include_router(relay_proxy_router)
app.include_router(audit_router)


@app.on_event("startup")
def startup():
    init_db()
    migrate_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "3.0"}
