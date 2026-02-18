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
# Usa prima Docker Secret, poi Env Var, poi Fallback
JWT_SECRET = get_secret("jwt_secret")
if not JWT_SECRET:
    JWT_SECRET = os.getenv("JWT_SECRET", "fallback_secret_key_change_me")

JWT_ALGORITHM = "HS256"
JWT_EXP_DAYS = 7

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
WPEX_NETWORK = os.getenv("WPEX_NETWORK", "wpex_wpex-network")


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

        # Tabella Utenti per Login
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tabella Blacklist Token (Logout) - SOSTITUISCE SESSIONS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS token_blacklist (
                jti VARCHAR(36) PRIMARY KEY,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        conn.close()

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

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "wpex_keys_db")
DB_USER = os.getenv("DB_USER", "wpex_admin")
DB_PASS = get_secret("db_password", "admin")
DATA_KEY = get_secret("db_encryption_key", "mysecretkey")
WPEX_NETWORK = os.getenv("WPEX_NETWORK", "wpex_wpex-network")

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

        # Tabella Utenti per Login
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tabella Sessioni
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
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

# (create_session RIMOSSA)

def get_user_from_session(token):
    # In JWT mode, "session" is the token itself
    payload = verify_jwt_token(token)
    if payload:
        return {"id": payload['sub'], "username": payload['name']}
    return None

def delete_session(token):
    # In JWT mode, we blacklist the token
    # We need to decode it first to get jti/exp
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        blacklist_token(payload['jti'], payload['exp'])
    except: pass

def create_user(username, password):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Usa pgcrypto per l'hashing sicuro direttamente nel DB
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
            # Verifica password con crypt
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
# Importante: deve essere inizializzato prima di qualsiasi check
cookie_manager = stx.CookieManager()

# --- SESSION CHECK ---
# --- SESSION CHECK ---
# Init session vars
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user'] = None
    st.session_state['session_token'] = None
    st.session_state['auth_checked'] = False

# 1. Controlla se c'è un cookie valido se non siamo ancora loggati
if not st.session_state['logged_in']:
    cookies = cookie_manager.get_all()
    
    # Se non abbiamo ancora controllato e i cookies sembrano vuoti (o nulli),
    # potenzialmente stanno ancora caricando.
    if not st.session_state['auth_checked']:
        # Se i cookies sono None, stx non è pronto.
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
                
                # Se siamo sulla pagina di login, facciamo un redirect pulito alla dashboard
                if st.query_params.get("page") == "login":
                     st.query_params["page"] = "dashboard"
                st.rerun()
        
        # Se non abbiamo trovato nulla, dobbiamo essere SICURI che non sia un ritardo di caricamento.
        # Proviamo a fare 2-3 tentativi di rerun prima di arrenderci.
        retry_count = st.session_state.get('auth_retries', 0)
        if retry_count < 2:
             st.session_state['auth_retries'] = retry_count + 1
             time.sleep(0.3)
             st.rerun()
             
        # Se siamo arrivati qui dopo i retry, allora NON siamo loggati davvero.
        st.session_state['auth_checked'] = True
# --- ROUTING & REDIRECTS ---
# Se non siamo loggati, l'UNICA pagina accessibile è login
page = st.query_params.get("page", "dashboard")

if not st.session_state['logged_in']:
    # Se NON abbiamo ancora finito i check di auth, NON mostriamo nulla (o spinner)
    if not st.session_state.get('auth_checked', False):
        st.stop()

    # Se la pagina corrente NON è login, forza redirect
    if page != "login":
        st.query_params["page"] = "login"
        st.rerun()
        
    # --- LOGIN PAGE WRAPPER ---
    # Stile Moderno / Glassmorphism per la login
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: auto;
            padding: 2rem;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        div.stButton > button {
            width: 100%;
            background-color: #ff4b4b;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #ff3333;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 75, 75, 0.4);
        }
        h1 { text-align: center; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🔐 WPEX Login")
        
        tab_login, tab_register = st.tabs(["Accedi", "Registrati"])
        
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Entra")
                
                if submit:
                    if username and password:
                        success, user_data = check_login(username, password)
                        if success:
                            # 1. Crea JWT Token
                            token, expires = create_jwt_token(user_data[0], user_data[1])
                            if token:
                                # 2. Setta Cookie
                                cookie_manager.set("wpex_session", token, expires_at=expires)
                                
                                st.session_state['logged_in'] = True
                                st.session_state['username'] = user_data[1]
                                st.session_state['user'] = {"id": user_data[0], "username": user_data[1]}
                                st.session_state['session_token'] = token
                                st.toast(f"Benvenuto {user_data[1]}!", icon="👋")
                                time.sleep(0.5)
                                # REDIRECT A ROOT DOPO LOGIN
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
    
    # Se non siamo loggati e stiamo renderizzando il form, fermiamo qui l'esecuzione
    # SE siamo appena loggati (rerun), questo blocco non viene raggiunto o st.stop viene saltato
    if not st.session_state['logged_in']:
        st.stop()

# SE SIAMO LOGGATI MA SIAMO SU ?page=login, redirect a root
if page == "login":
    st.query_params.clear()
    st.rerun()

# SIDEBAR LOGOUT
with st.sidebar:
    st.write(f"Utente: **{st.session_state.get('username', 'Admin')}**")
    if st.button("Logout", type="secondary"):
        # 1. Rimuovi sessione dal DB usando il token memorizzato
        token = st.session_state.get('session_token')
        if token:
            delete_session(token)
        
        # 2. Rimuovi Cookie (tentativo best effort)
        try:
            cookie_manager.delete("wpex_session")
        except: pass
        
        # 3. Pulisci stato
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.session_state['session_token'] = None
        if 'username' in st.session_state: del st.session_state['username']
            
        # Redirect a Login implicitamente al prossimo rerun
        st.query_params.clear()
        st.rerun()

st.title("🏢 WPEX Multi-Server Orchestrator")
st.markdown(f"<small>Host IP: `{CURRENT_HOST_IP}`</small>", unsafe_allow_html=True)

# --- ROUTING NAVIGATOR ---
# Gestiamo la navigazione tramite query params
# Page è già stato letto sopra

server_name_param = st.query_params.get("name", None)

if page == "server" and server_name_param:
    # --- VISTA SINGOLA SERVER ---
    current_view_server = server_name_param
    
    # Troviamo i dati del server
    all_servers = get_servers_list()
    srv_data = next((s for s in all_servers if s['name'] == current_view_server), None)
    
    if not srv_data:
        st.error(f"Server {current_view_server} non trovato.")
        if st.button("Torna alla Dashboard"):
            st.query_params.clear()
            st.rerun()
    else:
        st.subheader(f"🖥️ Monitor: {current_view_server}")
        c1, c2 = st.columns([1, 4])
        if c1.button("⬅️ Dashboard"):
            st.query_params.clear()
            st.rerun()
        
        # 1. Iframe della GUI (Solo la parte visuale)
        # Nota: Qui usiamo il path rewritato da Nginx per l'accesso raw
        # L'accesso raw è protetto? No, al momento no, ma nginx lo nasconde parzialmente.
        # Useremo il path interno /wpex-<name>/
        raw_gui_url = f"/wpex-{current_view_server}/"
        components.iframe(raw_gui_url, height=600, scrolling=True)
        
        # 2. Controlli sotto (Integrated)
        st.divider()
        st.markdown("### 🛠️ Controlli Integrati")
        
        col_info, col_actions = st.columns([2, 1])
        with col_info:
            status, _ = get_docker_status(f"wpex-{current_view_server}") # Fix: aggiungi wpex-
            st.write(f"**Status:** {status.upper()}")
            st.caption(f"UDP: {srv_data['udp_port']} | Web (Internal): {srv_data['web_port']}")
            
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
            if ca1.button("▶️ Start", key=f"st_v_{srv_data['id']}"): start_server_docker(srv_data['name']); st.rerun()
            if ca2.button("⏸️ Stop", key=f"sp_v_{srv_data['id']}"): stop_server_docker(srv_data['name']); st.rerun()
            
        if st.checkbox("Mostra Logs", key=f"log_v_{srv_data['id']}"):
            st.code(get_logs(srv_data['name']))

else:
    # --- DASHBOARD (VIEW PRINCIPALE) ---
    tab_servers, tab_keys = st.tabs(["📦 Server & Istanze", "🔐 Database Chiavi"])
    
    # ==========================
    # TAB 1: GESTIONE SERVER
    # ==========================
    with tab_servers:
        # --- LISTA SERVER ---
        with st.expander("➕ Aggiungi Nuovo Server", expanded=False):
            with st.form("new_server_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                srv_name = c1.text_input("Nome Server", placeholder="es. alpha")
                srv_udp = c2.number_input("Porta UDP", value=40000, step=1)
                
                # Carichiamo tutte le chiavi disponibili
                all_keys_info = get_all_keys_info()
                key_map = {k['id']: k['alias'] for k in all_keys_info} # ID -> Alias
                
                selected_ids = st.multiselect("Seleziona Chiavi", options=key_map.keys(), format_func=lambda x: key_map[x])

                if st.form_submit_button("Crea Server"):
                    srv_name = srv_name.lower().replace(" ", "-")
                    if srv_name and selected_ids:
                        srv_web = get_next_web_port()
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
                    
                    # Visualizza nel dashboard (Link con Query Param)
                    if st.button(f"👁️ Console", key=f"view_{srv['id']}"):
                         st.query_params["page"] = "server"
                         st.query_params["name"] = srv['name']
                         st.rerun()
                
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
