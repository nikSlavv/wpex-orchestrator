#!/usr/bin/env python3
import streamlit as st
import docker
import psycopg2
import os
import time
import requests

# --- CONFIGURAZIONE ---
IMAGE_NAME = "nikoceps/wpex-monitoring:latest"

# Tenta di ottenere l'IP pubblico per i link
def get_public_ip():
    try:
        # Timeout breve per non bloccare l'app se offline
        return os.getenv("HOST_IP", requests.get('https://api.ipify.org', timeout=1).text)
    except:
        return "localhost"

CURRENT_HOST_IP = get_public_ip()

# --- CSS CUSTOM ---
st.markdown("""
<style>
    .secret-hover {
        background-color: #333;
        color: #333; 
        border-radius: 4px;
        padding: 5px 10px;
        font-family: monospace;
        transition: all 0.2s ease-in-out;
        cursor: text;
        user-select: all; 
        border: 1px solid #444;
    }
    .secret-hover:hover {
        background-color: #222;
        color: #0f0; 
        border-color: #0f0;
    }
    /* Riduciamo spaziatura expander */
    .streamlit-expanderHeader {
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE SECRETS ---
def get_secret(secret_name, default=None):
    try:
        with open(f"/run/secrets/{secret_name}", "r") as f:
            return f.read().strip()
    except IOError:
        return default

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "wpex_keys_db")
DB_USER = os.getenv("DB_USER", "wpex_admin")
DB_PASS = get_secret("db_password", "admin")
DATA_KEY = get_secret("db_encryption_key", "mysecretkey")

st.set_page_config(page_title="WPEX Orchestrator", page_icon="🏢", layout="wide")

# --- DATABASE LAYER ---
def get_db_connection():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    except Exception as e:
        st.toast(f"❌ Errore DB: {e}", icon="🔥")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
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
        conn.commit()
        conn.close()

def migrate_db():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("ALTER TABLE servers ADD COLUMN IF NOT EXISTS web_port INT DEFAULT 8080;")
            conn.commit()
        except: pass
        finally: conn.close()

# --- MODEL FUNCTIONS ---

# CHIAVI
def add_global_key(alias, plain_key):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO access_keys (alias, key_value) VALUES (%s, pgp_sym_encrypt(%s, %s));", 
                        (alias, plain_key, DATA_KEY))
            conn.commit()
            conn.close()
            return True
        except: return False
    return False

def get_all_keys_info():
    conn = get_db_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute(f"SELECT id, alias, pgp_sym_decrypt(key_value, %s) FROM access_keys ORDER BY created_at DESC", (DATA_KEY,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "alias": r[1], "key": r[2]} for r in rows]

def delete_global_key(key_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM access_keys WHERE id = %s", (key_id,))
        conn.commit()
        conn.close()

# SERVER
def add_server_db(name, udp_port, web_port, key_ids):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO servers (name, port, web_port) VALUES (%s, %s, %s) RETURNING id;", 
                        (name, udp_port, web_port))
            server_id = cur.fetchone()[0]
            for kid in key_ids:
                cur.execute("INSERT INTO server_keys_link (server_id, key_id) VALUES (%s, %s)", (server_id, kid))
            conn.commit()
            conn.close()
            return True, server_id
        except Exception as e:
            return False, str(e)
    return False, "DB Error"

def update_server_keys_link(server_id, new_key_ids):
    """Aggiorna le chiavi associate a un server"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            # 1. Rimuovi vecchi link
            cur.execute("DELETE FROM server_keys_link WHERE server_id = %s", (server_id,))
            # 2. Aggiungi nuovi link
            for kid in new_key_ids:
                cur.execute("INSERT INTO server_keys_link (server_id, key_id) VALUES (%s, %s)", (server_id, kid))
            conn.commit()
            conn.close()
            return True
        except: return False
    return False

def delete_server_db(server_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM servers WHERE id = %s", (server_id,))
        conn.commit()
        conn.close()

def get_servers_list():
    conn = get_db_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT id, name, port, web_port FROM servers ORDER BY port ASC")
    servers = []
    for row in cur.fetchall():
        sid, name, udp_port, web_port = row
        # Ora prendiamo anche ID e Alias delle chiavi per la GUI di modifica
        cur.execute("""
            SELECT k.id, k.alias, pgp_sym_decrypt(k.key_value, %s) 
            FROM access_keys k 
            JOIN server_keys_link l ON k.id = l.key_id 
            WHERE l.server_id = %s
        """, (DATA_KEY, sid))
        # Salviamo la lista di dizionari invece che solo stringhe
        keys_data = [{"id": k[0], "alias": k[1], "key": k[2]} for k in cur.fetchall()]
        servers.append({"id": sid, "name": name, "udp_port": udp_port, "web_port": web_port, "keys": keys_data})
    conn.close()
    return servers

# --- DOCKER ACTIONS ---
def get_docker_status(container_name):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        return container.status, container
    except docker.errors.NotFound:
        return "not_created", None
    except:
        return "error", None

def deploy_server_docker(name, udp_port, web_port, keys_list):
    client = docker.from_env()
    container_name = f"wpex-{name}"
    
    cmd_args = ["--stats", ":8080"]
    for k in keys_list:
        cmd_args.extend(["--allow", k])
    if not keys_list: cmd_args.extend(["--allow", "placeholder"])

    port_bindings = {
        f'{udp_port}/udp': udp_port,
        '8080/tcp': web_port
    }

    try:
        status, container = get_docker_status(container_name)
        if status != "not_created":
            container.remove(force=True)

        client.containers.run(
            image=IMAGE_NAME,
            name=container_name,
            command=cmd_args,
            ports=port_bindings,
            restart_policy={"Name": "always"},
            detach=True
        )
        return True, "Container Avviato!"
    except Exception as e:
        return False, str(e)

def stop_server_docker(name):
    try:
        docker.from_env().containers.get(f"wpex-{name}").stop()
    except: pass

def start_server_docker(name):
    try:
        docker.from_env().containers.get(f"wpex-{name}").start()
    except: pass

def remove_server_docker(name):
    try:
        docker.from_env().containers.get(f"wpex-{name}").remove(force=True)
    except: pass

def get_logs(name):
    try:
        return docker.from_env().containers.get(f"wpex-{name}").logs(tail=20, timestamps=True).decode('utf-8', errors='ignore')
    except:
        return "Nessun log."

# --- INIT ---
if 'db_init' not in st.session_state:
    init_db()
    migrate_db()
    st.session_state['db_init'] = True

# --- UI LAYOUT ---
st.title("🏢 WPEX Multi-Server Orchestrator")
st.markdown(f"<small>Host IP: `{CURRENT_HOST_IP}`</small>", unsafe_allow_html=True)

tab_servers, tab_keys = st.tabs(["📦 Server & Istanze", "🔐 Database Chiavi"])

# ==========================
# TAB 1: GESTIONE SERVER
# ==========================
with tab_servers:
    # --- FORM CREAZIONE ---
    with st.expander("➕ Aggiungi Nuovo Server", expanded=False):
        with st.form("new_server_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            srv_name = c1.text_input("Nome Server", placeholder="es. alpha")
            srv_udp = c2.number_input("Porta UDP", value=40000, step=1)
            srv_web = c3.number_input("Porta Web", value=8080, step=1)
            
            # Carichiamo tutte le chiavi disponibili
            all_keys_info = get_all_keys_info()
            key_map = {k['id']: k['alias'] for k in all_keys_info} # ID -> Alias
            
            selected_ids = st.multiselect("Seleziona Chiavi", options=key_map.keys(), format_func=lambda x: key_map[x])

            if st.form_submit_button("Crea Server"):
                srv_name = srv_name.lower().replace(" ", "-")
                if srv_name and selected_ids:
                    ok, msg = add_server_db(srv_name, srv_udp, srv_web, selected_ids)
                    if ok:
                        # Estraiamo le chiavi raw per docker
                        raw_keys = [k['key'] for k in all_keys_info if k['id'] in selected_ids]
                        res, d_msg = deploy_server_docker(srv_name, srv_udp, srv_web, raw_keys)
                        if res: st.rerun()
                        else: st.error(d_msg)
                    else: st.error(msg)
                else: st.warning("Dati mancanti.")

    st.divider()

    # --- LISTA SERVER ---
    servers = get_servers_list()
    # Serve ricaricare le info globali delle chiavi per i menu di modifica
    all_keys_global = get_all_keys_info()
    global_key_map = {k['id']: k['alias'] for k in all_keys_global}

    if not servers: st.info("Nessun server attivo.")
    
    for srv in servers:
        with st.container():
            status, _ = get_docker_status(f"wpex-{srv['name']}")
            status_icon = "🟢" if status == "running" else "🔴" if status in ["exited", "stopped"] else "⚪"
            
            c_info, c_actions = st.columns([3, 2])
            
            # Colonna INFO
            with c_info:
                st.markdown(f"### {status_icon} wpex-{srv['name']}")
                st.caption(f"UDP: **{srv['udp_port']}** | Web: **{srv['web_port']}**")
                
                # --- NUOVA SEZIONE: GESTIONE CHIAVI ---
                with st.expander(f"⚙️ Gestisci Chiavi ({len(srv['keys'])})"):
                    # 1. Troviamo gli ID delle chiavi attualmente assegnate a questo server
                    current_server_key_ids = [k['id'] for k in srv['keys']]
                    
                    # 2. Multiselect pre-compilato
                    new_selection = st.multiselect(
                        "Modifica lista chiavi:",
                        options=global_key_map.keys(),
                        default=current_server_key_ids,
                        format_func=lambda x: global_key_map[x],
                        key=f"ms_{srv['id']}"
                    )
                    
                    # 3. Pulsante Aggiornamento
                    if st.button("💾 Salva e Riavvia", key=f"save_{srv['id']}"):
                        # Aggiorna DB
                        if update_server_keys_link(srv['id'], new_selection):
                            # Prepara lista chiavi raw per docker
                            new_keys_raw = [k['key'] for k in all_keys_global if k['id'] in new_selection]
                            # Riavvia Docker
                            deploy_server_docker(srv['name'], srv['udp_port'], srv['web_port'], new_keys_raw)
                            st.toast("Chiavi aggiornate!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Errore DB durante aggiornamento.")

            # Colonna AZIONI
            with c_actions:
                st.write("**Controlli:**")
                b1, b2, b3 = st.columns(3)
                if b1.button("▶️", key=f"start_{srv['id']}", disabled=(status=="running")):
                    start_server_docker(srv['name'])
                    st.rerun()
                if b2.button("⏸️", key=f"stop_{srv['id']}", disabled=(status!="running")):
                    stop_server_docker(srv['name'])
                    st.rerun()
                if b3.button("🗑️", key=f"del_{srv['id']}"):
                    remove_server_docker(srv['name'])
                    delete_server_db(srv['id'])
                    st.rerun()
                
                st.link_button(f"📊 Apri Stats ({srv['web_port']})", f"http://{CURRENT_HOST_IP}:{srv['web_port']}", type="primary")
            
            if st.checkbox("Logs", key=f"lg_{srv['id']}"):
                st.code(get_logs(srv['name']))
            
            st.write("---")

# ==========================
# TAB 2: GLOBAL KEYS
# ==========================
with tab_keys:
    st.subheader("Chiavi Globali")
    with st.form("add_key"):
        c1, c2 = st.columns([1, 2])
        alias = c1.text_input("Nome/Alias")
        k_val = c2.text_input("Chiave", type="password")
        if st.form_submit_button("Aggiungi"):
            add_global_key(alias, k_val)
            st.rerun()
    
    st.write("---")
    keys = get_all_keys_info()
    for k in keys:
        c1, c2, c3 = st.columns([2, 4, 1])
        c1.write(f"**{k['alias']}**")
        c2.markdown(f'<span class="secret-hover">{k["key"]}</span>', unsafe_allow_html=True)
        if c3.button("🗑️", key=f"kd_{k['id']}"):
            delete_global_key(k['id'])
            st.rerun()
