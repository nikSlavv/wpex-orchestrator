"""
WPEX Orchestrator — Database Layer
Connection management, schema init, and migrations.
"""
import os
import psycopg2

# --- CONFIG ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "wpex_keys_db")
DB_USER = os.getenv("DB_USER", "wpex_admin")

def _read_secret(name, default=None):
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


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS access_keys (
            id SERIAL PRIMARY KEY,
            alias VARCHAR(50),
            key_value BYTEA NOT NULL,
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

    conn.commit()
    conn.close()


def migrate_db():
    """Run any pending schema migrations."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS web_port INT DEFAULT 8080;")
        conn.commit()
    except:
        pass
    finally:
        conn.close()
