#!/usr/bin/env python3
import streamlit as st
import streamlit.components.v1 as components
import docker
import psycopg2
import os
import time
import requests
import datetime
import uuid
import extra_streamlit_components as stx
import jwt

from style import GLOBAL_CSS, LANDING_HTML, icon, status_dot

# --- CONFIGURAZIONE ---
IMAGE_NAME = "nikoceps/wpex-monitoring:latest"

# --- GESTIONE SECRETS ---
def get_secret(secret_name, default=None):
    try:
        with open(f"/run/secrets/{secret_name}", "r") as f:
            return f.read().strip()
    except IOError:
        return default

# --- JWT CONFIG ---
JWT_SECRET = get_secret("jwt_secret")
if not JWT_SECRET:
    JWT_SECRET = os.getenv("JWT_SECRET", "changeme_super_long_fallback_secret_key_32bytes_minimum")

JWT_ALGORITHM = "HS256"
JWT_EXP_DAYS = 7

# Tenta di ottenere l'IP pubblico per i link
def get_public_ip():
    try:
        return os.getenv("HOST_IP", requests.get('https://api.ipify.org', timeout=1).text)
    except:
        return "localhost"

CURRENT_HOST_IP = get_public_ip()

# --- CONFIG DB ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "wpex_keys_db")
DB_USER = os.getenv("DB_USER", "wpex_admin")
DB_PASS = get_secret("db_password", "admin")
DATA_KEY = get_secret("db_encryption_key", "mysecretkey")
WPEX_NETWORK = os.getenv("WPEX_NETWORK", "wpex_wpex-network")

# --- PAGE CONFIG ---
st.set_page_config(page_title="WPEX Orchestrator", page_icon="⚡", layout="wide")

# --- INJECT GLOBAL CSS ---
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# --- DATABASE LAYER ---
def get_db_connection():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    except Exception as e:
        st.toast(f"Errore DB: {e}")
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
            cur.execute("DELETE FROM server_keys_link WHERE server_id = %s", (server_id,))
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

def get_next_web_port():
    conn = get_db_connection()
    if not conn: return 8080
    cur = conn.cursor()
    cur.execute("SELECT MAX(web_port) FROM servers")
    max_port = cur.fetchone()[0]
    conn.close()
    if max_port:
        return max_port + 1
    return 8080

def get_servers_list():
    conn = get_db_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT id, name, port, web_port FROM servers ORDER BY port ASC")
    servers = []
    for row in cur.fetchall():
        sid, name, udp_port, web_port = row
        cur.execute("""
            SELECT k.id, k.alias, pgp_sym_decrypt(k.key_value, %s) 
            FROM access_keys k 
            JOIN server_keys_link l ON k.id = l.key_id 
            WHERE l.server_id = %s
        """, (DATA_KEY, sid))
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
        f'{udp_port}/udp': udp_port
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
            network=WPEX_NETWORK,
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

# --- AUTH FUNCTIONS ---

def create_jwt_token(user_id, username):
    try:
        expiration = datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXP_DAYS)
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "name": username,
            "exp": expiration,
            "jti": jti
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token, expiration
    except Exception as e:
        print(f"Error creating token: {e}")
        return None, None

def is_token_blacklisted(jti):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM token_blacklist WHERE jti = %s", (jti,))
            exists = cur.fetchone()
            conn.close()
            return exists is not None
        except: pass
    return False

def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if is_token_blacklisted(payload['jti']):
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def blacklist_token(jti, exp_timestamp):
    conn = get_db_connection()
    if conn:
        try:
            expires_at = datetime.datetime.fromtimestamp(exp_timestamp)
            cur = conn.cursor()
            cur.execute("INSERT INTO token_blacklist (jti, expires_at) VALUES (%s, %s)", (jti, expires_at))
            conn.commit()
            conn.close()
        except: pass

def get_user_from_session(token):
    payload = verify_jwt_token(token)
    if payload:
        return {"id": int(payload['sub']), "username": payload['name']}
    return None

def delete_session(token):
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        blacklist_token(payload['jti'], payload['exp'])
    except: pass

def create_user(username, password):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, crypt(%s, gen_salt('bf')));", 
                        (username, password))
            conn.commit()
            conn.close()
            return True, "Utente creato con successo!"
        except psycopg2.errors.UniqueViolation:
            return False, "Username già esistente."
        except Exception as e:
            return False, f"Errore creazione utente: {e}"
    return False, "Errore connessione DB"

def check_login(username, password):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username FROM users WHERE username = %s AND password_hash = crypt(%s, password_hash);", 
                        (username, password))
            user = cur.fetchone()
            conn.close()
            if user:
                return True, user
            return False, None
        except Exception as e:
            return False, None
    return False, None


# --- INIT ---
if 'db_init' not in st.session_state:
    init_db()
    migrate_db()
    st.session_state['db_init'] = True

# --- COOKIE MANAGER ---
cookie_manager = stx.CookieManager(key="wpex_cookie_mgr")

# --- SESSION CHECK ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user'] = None
    st.session_state['session_token'] = None
    st.session_state['auth_checked'] = False

if not st.session_state['logged_in']:
    cookies = cookie_manager.get_all()
    
    if not st.session_state['auth_checked']:
        if cookies is None:
            st.stop()
        
        session_token = cookies.get("wpex_session")
        
        if session_token:
            user_data = get_user_from_session(session_token)
            if user_data:
                st.session_state['logged_in'] = True
                st.session_state['user'] = user_data
                st.session_state['username'] = user_data['username']
                st.session_state['session_token'] = session_token
                st.session_state['auth_checked'] = True
                
                if st.query_params.get("page") == "login":
                     st.query_params["page"] = "dashboard"
                st.rerun()
        
        retry_count = st.session_state.get('auth_retries', 0)
        if retry_count < 5:
             st.session_state['auth_retries'] = retry_count + 1
             time.sleep(0.5)
             st.rerun()
             
        st.session_state['auth_checked'] = True

# --- ROUTING & REDIRECTS ---
page = st.query_params.get("page", "dashboard")

if not st.session_state['logged_in']:
    if not st.session_state.get('auth_checked', False):
        with st.spinner("Checking authentication..."):
            time.sleep(1)
            st.rerun()

    # ── LANDING PAGE (default for non-logged users) ──
    if st.session_state.get('auth_checked', False) and page not in ("login", "landing"):
        st.query_params["page"] = "landing"
        st.rerun()

    if page == "landing" or page == "dashboard":
        # Show landing page via components.html (renders full HTML properly)
        components.html(LANDING_HTML, height=750, scrolling=False)
        
        st.stop()

    # ── LOGIN PAGE ──
    if page == "login":
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(f'<div class="login-title">{icon("lock")} WPEX Login</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Accedi alla dashboard di gestione</div>', unsafe_allow_html=True)
            
            tab_login, tab_register = st.tabs([f"Accedi", f"Registrati"])
            
            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Entra")
                    
                    if submit:
                        if username and password:
                            success, user_data = check_login(username, password)
                            if success:
                                token, expires = create_jwt_token(user_data[0], user_data[1])
                                if token:
                                    cookie_manager.set("wpex_session", token, expires_at=expires)
                                    
                                    st.session_state['logged_in'] = True
                                    st.session_state['username'] = user_data[1]
                                    st.session_state['user'] = {"id": user_data[0], "username": user_data[1]}
                                    st.session_state['session_token'] = token
                                    st.toast(f"Benvenuto {user_data[1]}!")
                                    time.sleep(0.5)
                                    st.query_params.clear()
                                    st.rerun()
                                else:
                                    st.error("Errore creazione token.")
                            else:
                                st.error("Credenziali non valide.")
                        else:
                            st.warning("Inserisci username e password.")

            with tab_register:
                with st.form("register_form"):
                    new_user = st.text_input("Nuovo Username")
                    new_pass = st.text_input("Nuova Password", type="password")
                    confirm_pass = st.text_input("Conferma Password", type="password")
                    reg_submit = st.form_submit_button("Crea Account")
                    
                    if reg_submit:
                        if new_user and new_pass:
                            if new_pass != confirm_pass:
                                st.error("Le password non coincidono.")
                            else:
                                ok, msg = create_user(new_user, new_pass)
                                if ok:
                                    st.success(msg)
                                    time.sleep(1)
                                else:
                                    st.error(msg)
                        else:
                            st.warning("Compila tutti i campi.")
    
    if not st.session_state['logged_in']:
        st.stop()

# SE SIAMO LOGGATI MA SIAMO SU ?page=login o landing, redirect a root
if page in ("login", "landing"):
    st.query_params.clear()
    st.rerun()

# ── SIDEBAR ──
with st.sidebar:
    st.markdown(f'{icon("user")} **{st.session_state.get("username", "Admin")}**', unsafe_allow_html=True)
    if st.button(f"Logout", type="secondary"):
        token = st.session_state.get('session_token')
        if token:
            delete_session(token)
        
        try:
            cookie_manager.delete("wpex_session")
        except: pass
        
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.session_state['session_token'] = None
        if 'username' in st.session_state: del st.session_state['username']
            
        st.query_params.clear()
        st.rerun()

# ── MAIN TITLE ──
st.markdown(f'<h1 style="display:flex;align-items:center;gap:10px">{icon("layout-dashboard")} WPEX Orchestrator</h1>', unsafe_allow_html=True)
st.markdown(f'<span class="info-badge">Host: <code>{CURRENT_HOST_IP}</code></span>', unsafe_allow_html=True)

# --- ROUTING NAVIGATOR ---
server_name_param = st.query_params.get("name", None)

if page == "server" and server_name_param:
    # ── VISTA SINGOLA SERVER ──
    current_view_server = server_name_param
    
    all_servers = get_servers_list()
    srv_data = next((s for s in all_servers if s['name'] == current_view_server), None)
    
    if not srv_data:
        st.error(f"Server {current_view_server} non trovato.")
        if st.button(f"{icon('arrow-left')} Torna alla Dashboard"):
            st.query_params.clear()
            st.rerun()
    else:
        st.markdown(f'### {icon("monitor")} Monitor: {current_view_server}', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 4])
        if c1.button("Dashboard", key="back_dash"):
            st.query_params.clear()
            st.rerun()
        
        # Iframe della GUI
        raw_gui_url = f"/wpex-{current_view_server}/"
        components.iframe(raw_gui_url, height=600, scrolling=True)
        
        # Controlli sotto
        st.divider()
        st.markdown(f'### {icon("settings")} Controlli Integrati', unsafe_allow_html=True)
        
        col_info, col_actions = st.columns([2, 1])
        with col_info:
            status, _ = get_docker_status(f"wpex-{current_view_server}")
            st.markdown(f'{status_dot(status)} **Status:** {status.upper()}', unsafe_allow_html=True)
            st.markdown(
                f'<span class="info-badge">UDP: {srv_data["udp_port"]}</span>'
                f'<span class="info-badge">Web: {srv_data["web_port"]}</span>',
                unsafe_allow_html=True
            )
            
            # Gestione Chiavi rapida
            all_keys_global = get_all_keys_info()
            global_key_map = {k['id']: k['alias'] for k in all_keys_global}
            current_server_key_ids = [k['id'] for k in srv_data['keys']]
            
            new_selection = st.multiselect(
                "Chiavi assegnate:",
                options=global_key_map.keys(),
                default=current_server_key_ids,
                format_func=lambda x: global_key_map[x],
                key=f"ms_view_{srv_data['id']}"
            )
            if st.button("Aggiorna e Riavvia", key=f"up_view_{srv_data['id']}"):
                new_keys_raw = [k['key'] for k in all_keys_global if k['id'] in new_selection]
                if update_server_keys_link(srv_data['id'], new_selection):
                    deploy_server_docker(srv_data['name'], srv_data['udp_port'], srv_data['web_port'], new_keys_raw)
                    st.success("Configurazione aggiornata!")
                    time.sleep(1)
                    st.rerun()

        with col_actions:
            st.write("**Azioni Rapide:**")
            ca1, ca2 = st.columns(2)
            if ca1.button("Start", key=f"st_v_{srv_data['id']}"): start_server_docker(srv_data['name']); st.rerun()
            if ca2.button("Stop", key=f"sp_v_{srv_data['id']}"): stop_server_docker(srv_data['name']); st.rerun()
            
        if st.checkbox("Mostra Logs", key=f"log_v_{srv_data['id']}"):
            st.code(get_logs(srv_data['name']))

else:
    # ── DASHBOARD (VIEW PRINCIPALE) ──
    tab_servers, tab_keys = st.tabs([
        f"Server & Istanze",
        f"Database Chiavi"
    ])
    
    # ==========================
    # TAB 1: GESTIONE SERVER
    # ==========================
    with tab_servers:
        with st.expander(f"Aggiungi Nuovo Server", expanded=False):
            with st.form("new_server_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                srv_name = c1.text_input("Nome Server", placeholder="es. alpha")
                srv_udp = c2.number_input("Porta UDP", value=40000, step=1)
                
                all_keys_info = get_all_keys_info()
                key_map = {k['id']: k['alias'] for k in all_keys_info}
                
                selected_ids = st.multiselect("Seleziona Chiavi", options=key_map.keys(), format_func=lambda x: key_map[x])

                if st.form_submit_button("Crea Server"):
                    srv_name = srv_name.lower().replace(" ", "-")
                    if srv_name and selected_ids:
                        srv_web = get_next_web_port()
                        ok, msg = add_server_db(srv_name, srv_udp, srv_web, selected_ids)
                        if ok:
                            raw_keys = [k['key'] for k in all_keys_info if k['id'] in selected_ids]
                            res, d_msg = deploy_server_docker(srv_name, srv_udp, srv_web, raw_keys)
                            if res: st.rerun()
                            else: st.error(d_msg)
                        else: st.error(msg)
                    else: st.warning("Dati mancanti.")

        st.divider()

        # --- LISTA SERVER ---
        servers = get_servers_list()
        all_keys_global = get_all_keys_info()
        global_key_map = {k['id']: k['alias'] for k in all_keys_global}

        if not servers: st.info("Nessun server attivo.")
        
        for srv in servers:
            with st.container(border=True):
                status, _ = get_docker_status(f"wpex-{srv['name']}")
                
                c_info, c_actions = st.columns([3, 2])
                
                # Colonna INFO
                with c_info:
                    st.markdown(
                        f'<div class="server-title">{status_dot(status)} wpex-{srv["name"]}</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<span class="info-badge">UDP: {srv["udp_port"]}</span>'
                        f'<span class="info-badge">Web: {srv["web_port"]}</span>',
                        unsafe_allow_html=True
                    )
                    
                    with st.expander(f"Gestisci Chiavi ({len(srv['keys'])})"):
                        current_server_key_ids = [k['id'] for k in srv['keys']]
                        
                        new_selection = st.multiselect(
                            "Modifica lista chiavi:",
                            options=global_key_map.keys(),
                            default=current_server_key_ids,
                            format_func=lambda x: global_key_map[x],
                            key=f"ms_{srv['id']}"
                        )
                        
                        if st.button("Salva e Riavvia", key=f"save_{srv['id']}"):
                            if update_server_keys_link(srv['id'], new_selection):
                                new_keys_raw = [k['key'] for k in all_keys_global if k['id'] in new_selection]
                                deploy_server_docker(srv['name'], srv['udp_port'], srv['web_port'], new_keys_raw)
                                st.toast("Chiavi aggiornate!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Errore DB durante aggiornamento.")

                # Colonna AZIONI
                with c_actions:
                    st.write("**Controlli:**")
                    b1, b2, b3 = st.columns(3)
                    if b1.button("Start", key=f"start_{srv['id']}", disabled=(status=="running")):
                        start_server_docker(srv['name'])
                        st.rerun()
                    if b2.button("Stop", key=f"stop_{srv['id']}", disabled=(status!="running")):
                        stop_server_docker(srv['name'])
                        st.rerun()
                    if b3.button("Delete", key=f"del_{srv['id']}"):
                        remove_server_docker(srv['name'])
                        delete_server_db(srv['id'])
                        st.rerun()
                    
                    if st.button(f"Console", key=f"view_{srv['id']}"):
                         st.query_params["page"] = "server"
                         st.query_params["name"] = srv['name']
                         st.rerun()
                
                if st.checkbox("Logs", key=f"lg_{srv['id']}"):
                    st.code(get_logs(srv['name']))

    # ==========================
    # TAB 2: GLOBAL KEYS
    # ==========================
    with tab_keys:
        st.markdown(f'### {icon("database")} Chiavi Globali', unsafe_allow_html=True)
        with st.form("add_key"):
            c1, c2 = st.columns([1, 2])
            alias = c1.text_input("Nome/Alias")
            k_val = c2.text_input("Chiave", type="password")
            if st.form_submit_button("Aggiungi"):
                add_global_key(alias, k_val)
                st.rerun()
        
        st.divider()
        keys = get_all_keys_info()
        for k in keys:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 4, 1])
                c1.markdown(f'{icon("key")} **{k["alias"]}**', unsafe_allow_html=True)
                c2.markdown(f'<span class="secret-hover">{k["key"]}</span>', unsafe_allow_html=True)
                if c3.button("Delete", key=f"kd_{k['id']}"):
                    delete_global_key(k['id'])
                    st.rerun()
