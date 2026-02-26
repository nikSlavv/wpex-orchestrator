"""
WPEX Orchestrator — Database Layer
Connection management, schema init, and migrations.
Supports multi-tenant SaaS architecture.
"""
import os
import psycopg2
import secrets

# --- CONFIG ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "wpex_keys_db")
DB_USER = os.getenv("DB_USER", "wpex_admin")

def _read_secret(name, default=None):
    if os.getenv(name):
        return os.getenv(name)
    try:
        with open(f"/run/secrets/{name}", "r") as f:
            return f.read().strip()
    except IOError:
        return default

DB_PASS = _read_secret("db_password", "admin")
DATA_KEY = _read_secret("db_encryption_key", "mysecretkey")


def get_db():
    """Return a new psycopg2 connection."""
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)


def generate_api_key():
    """Generate a secure random API key."""
    return secrets.token_urlsafe(48)


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ── Original tables ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS access_keys (
            id SERIAL PRIMARY KEY,
            alias VARCHAR(50),
            key_value BYTEA NOT NULL,
            tenant_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            port INT UNIQUE NOT NULL,
            web_port INT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS server_keys_link (
            server_id INT REFERENCES servers(id) ON DELETE CASCADE,
            key_id INT REFERENCES access_keys(id) ON DELETE CASCADE,
            PRIMARY KEY (server_id, key_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti VARCHAR(36) PRIMARY KEY,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            slug VARCHAR(50) UNIQUE NOT NULL,
            max_tunnels INT DEFAULT 10,
            max_bandwidth_mbps INT DEFAULT 100,
            sla_target DECIMAL(5,2) DEFAULT 99.9,
            allowed_regions TEXT[] DEFAULT '{}',
            preferred_relay_ids INT[],
            api_key VARCHAR(100) UNIQUE,
            billing_integration_id VARCHAR(100),
            status VARCHAR(20) DEFAULT 'active',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id SERIAL PRIMARY KEY,
            tenant_id INT REFERENCES tenants(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            region VARCHAR(50),
            public_ip VARCHAR(45),
            subnet VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            user_id INT,
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_id INT,
            details JSONB,
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


def migrate_db():
    """Run any pending schema migrations."""
    conn = get_db()
    try:
        cur = conn.cursor()
        # Original migration
        cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS web_port INT DEFAULT 8080;")
        # SaaS migrations — RBAC fields on users
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'engineer';")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id INT;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR(100);")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ip_whitelist TEXT[];")
        # Onboarding: status field (pending/active/disabled)
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';")
        # Relay tenant association
        cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS tenant_id INT;")
        cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS region VARCHAR(50);")
        cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';")
        # Access Keys tenant isolation
        cur.execute("ALTER TABLE access_keys ADD COLUMN IF NOT EXISTS tenant_id INT;")

        # Tenant registration status
        cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';")
        
        # Obsolete Tunnels removal
        cur.execute("DROP TABLE IF EXISTS relay_config_versions CASCADE;")
        cur.execute("DROP TABLE IF EXISTS tunnels CASCADE;")
        
        conn.commit()
    except:
        pass
    finally:
        conn.close()
