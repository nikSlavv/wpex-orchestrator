# WPEX Orchestrator — Manuale Utente

## 1. Introduzione

**WPEX Orchestrator** è una piattaforma SaaS multi-tenant per la gestione centralizzata di nodi di rete VPN basati su WireGuard. Attraverso una dashboard unificata permette di creare, configurare, monitorare e aggiornare istanze relay dinamicamente su **Kubernetes**.

Al suo cuore, il sistema orchestra il binario **WPEX** (WireGuard Packet Relay) — un relay trasparente che facilita il NAT traversal senza mai compromettere né decifrare la crittografia end-to-end di WireGuard.

---

## 2. Architettura & Stack Tecnologico

L'applicazione segue un'architettura a microservizi distribuita su **Docker Swarm** (per l'orchestratore) e **Kubernetes** (per i relay figli).

| Componente | Tecnologia | Ruolo |
|---|---|---|
| **Relay Engine** | Go (wpex binary) | Instrada pacchetti WireGuard UDP tra peer NAT |
| **Backend API** | Python 3.11 + FastAPI | Logica di business, RBAC, provisioning K8s |
| **Frontend** | React 18 + Vite | Dashboard SPA, dark mode, responsive |
| **Database** | PostgreSQL 15 + pgcrypto | Persistenza chiavi (cifrate), utenti, tenant, audit |
| **Gateway** | Nginx + Let's Encrypt | Reverse proxy HTTPS, TLS 1.3, rinnovo cert auto |
| **Orchestrazione** | Kubernetes Python client | Deploy/stop/restart/upgrade pod relay |

---

## 3. Il Motore WPEX: Come Funziona

WPEX non è un endpoint WireGuard — è un **relay trasparente UDP**. Non possiede né vede alcuna chiave privata.

### 3.1 Routing dei Pacchetti

1. Ogni peer WireGuard sceglie un **peer index** casuale a 32 bit per identificarsi nella sessione.
2. WPEX apprende l'associazione `peer_index → indirizzo UDP` al momento del primo handshake.
3. I pacchetti successivi vengono inoltrati direttamente al peer corretto in base al `receiver_index`.

Per l'**handshake iniziale** (che non ha ancora un receiver index), WPEX fa un broadcast verso tutti gli endpoint noti. Solo il peer corretto risponderà.

### 3.2 Sicurezza Anti-Amplification (Allowlist pubkey)

Il broadcast dell'handshake iniziale sarebbe sfruttabile per attacchi DDoS/amplification. Per mitigarlo, l'Orchestrator inietta una **whitelist di chiavi pubbliche WireGuard** autorizzate al momento del deploy del relay (`--allow <pubkey>`).

Il relay verifica il campo `mac1` di ogni handshake initiation: se la public key non è nella lista, il pacchetto viene scartato immediatamente (log: `invalid mac1 in handshake initiation`).

> **Nota**: Solo le chiavi **pubbliche** sono note al relay — la crittografia E2E rimane intatta.

### 3.3 Monitoring in Tempo Reale

Ogni relay espone un HTTP server interno sulla porta `8080` (accessibile solo dall'Orchestrator tramite K8s internal DNS `wpex-{name}.wpex.svc.cluster.local`):

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/stats` | GET | Statistiche raw JSON (handshake, sessioni, bytes) |
| `/api/v1/stats` | GET | Stats enhanced con success rate e peer list ordinata |
| `/api/v1/health` | GET | Health score pesato con breakdown per componente |
| `/api/v1/config` | GET | Configurazione runtime (CLI args usati all'avvio) |
| `/api/v1/diagnostics/ping` | POST | Ping dal container verso un target |
| `/api/v1/diagnostics/traceroute` | POST | Traceroute dal container verso un target |

---

## 4. Gestione Utenti e Ruoli (RBAC)

WPEX Orchestrator implementa un controllo accessi a **4 livelli gerarchici** in ambiente multi-tenant:

| Ruolo | Scope | Permessi |
|---|---|---|
| **Admin** | Globale | Accesso completo. Gestisce tutti i tenant, relay, chiavi, utenti e policy. |
| **Executive** | Globale | Solo lettura. Visibilità su metriche e KPI di tutte le organizzazioni. |
| **Engineer** | Locale (proprio tenant) | CRUD su relay e chiavi del proprio tenant. Non può accedere ad altri tenant. |
| **Viewer** | Locale (proprio tenant) | Solo lettura delle dashboard del proprio tenant. |

Gli utenti si registrano in stato `pending` e devono essere approvati da un Admin prima di poter accedere.

---

## 5. Guida ai Moduli (Web UI)

### 5.1 Dashboard

Pannello riassuntivo con KPI in tempo reale:
- Numero totale relay attivi / totali
- Health score globale medio (calcolato su handshake rate, peer connectivity, uptime)
- Sessioni VPN attive e totale handshake
- Allarmi critici e relay degradati
- Statistiche aggregate di banda

### 5.2 Relays

Pannello operativo principale per l'orchestrazione dei relay:

- **Creazione**: Assegna nome, porta UDP e seleziona le chiavi pubbliche autorizzate. L'Orchestrator crea un Deployment K8s (`wpex-{name}`) con il binario che parte con `--port {udp} --allow {pubkey1} --allow {pubkey2} ... --stats :8080`.
- **Stato**: Ogni relay mostra status live (running/stopped/error), health score, numero di peer connessi.
- **Relay Detail** (click sul relay): Grafici di handshake, sessioni attive, bytes trasferiti; log raw del pod; diagnostica ping/traceroute.
- **Ciclo di vita**: Start, Stop, Restart, Delete, Upgrade immagine direttamente dalla UI.
- **Aggiornamento chiavi**: Modifica la lista di public key autorizzate → l'Orchestrator aggiorna il Deployment K8s con le nuove chiavi.

### 5.3 Chiavi (Keys)

Wallet centralizzato delle public key WireGuard:

1. Inserisci la stringa base64 della public key (44 caratteri, es. `AAAA...=`) e un alias leggibile.
2. La chiave viene cifrata con `pgcrypto` e salvata nel database — non è mai visibile in chiaro dopo l'inserimento.
3. Associa le chiavi ai relay dal pannello Relays o dal dettaglio del relay.
4. Ogni tenant vede e gestisce solo le proprie chiavi.

### 5.4 Topologia

Mappa interattiva della rete:
- I nodi rappresentano i relay cloud
- I link mostrano lo stato delle interconnessioni
- Colori: verde (healthy), ambra (degradato), rosso (offline/critico)

### 5.5 Tenant

_(Solo Admin)_ Gestione delle organizzazioni clienti:
- Crea e configura tenant con limiti di tunnel, banda, SLA target e regioni consentite
- Assegna utenti ai tenant
- Visualizza risorse per tenant

### 5.6 Impostazioni

- **Utenti in attesa**: Approva o rifiuta nuovi account in stato `pending`
- **Profilo**: Cambia password, configura MFA (TOTP), gestisci whitelist IP
- **Log di Audit**: Tracciabilità completa delle operazioni (chi, quando, cosa) con filtri per tipo di evento

---

## 6. Installazione & Deployment

### Prerequisiti

- Un nodo con **Docker + Swarm** attivo (per l'orchestratore)
- Un cluster **Kubernetes** raggiungibile con namespace `wpex` creato (per i relay)
- Un dominio con record DNS puntato al server (per Let's Encrypt)

### Deploy Orchestratore (Docker Swarm)

```bash
# 1. Crea il namespace K8s per i relay (se non esiste)
kubectl create namespace wpex

# 2. Crea i secret Docker Swarm
printf "password_db_sicura"      | docker secret create db_password -
printf "chiave_crittografia_32+" | docker secret create db_encryption_key -
printf "jwt_secret_lungo_random" | docker secret create jwt_secret -

# 3. Deploy stack
docker stack deploy -c wpex-stack.yml wpex

# 4. Verifica
docker stack services wpex
```

### Configurazione SSL (Let's Encrypt)

Lo stack include Certbot in modalità auto-renew. Per ottenere il primo certificato:

```bash
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh
```

Modifica il dominio nel script e in `nginx/nginx.conf` prima di eseguirlo.

---

## 7. Primo Accesso

1. Naviga su `https://tuo-dominio.com`
2. Clicca **Registrati** e crea il primo account
3. L'account sarà in stato `pending` — attiva il primo admin manualmente:

```sql
-- Esegui su PostgreSQL
UPDATE users SET status = 'active', role = 'admin' WHERE username = 'tuo_utente';
```

4. Accedi con le tue credenziali
5. Da **Impostazioni → Utenti in Attesa** approva i futuri account via UI

---

## 8. Configurazione WireGuard sui Client

Per connettere un client WireGuard (es. Mikrotik, Linux, router) al relay:

```ini
[Interface]
PrivateKey = <chiave_privata_del_peer>
# Nessun Address di peer overlay — wpex è trasparente

[Peer]
PublicKey = <pubkey_dell_altro_peer>
Endpoint = <ip_o_dominio_relay>:<porta_udp>
PersistentKeepalive = 25
AllowedIPs = <subnet_remota>
```

**Requisiti**:
- La public key di **questo peer** deve essere nella allowlist del relay (aggiunta tramite Orchestrator → Keys)
- Tutti i peer che devono comunicare tra loro devono essere collegati allo **stesso relay**
- `PersistentKeepalive` è fondamentale se il peer è dietro NAT

> **Caso NAT condiviso**: Se più peer escono dallo stesso IP pubblico, assicurarsi che il NAT mantenga porte sorgente stabili. Ogni peer deve usare una porta sorgente WireGuard diversa.

---

## 9. Troubleshooting

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| `invalid mac1 in handshake initiation` nei log | Public key del peer non nella allowlist | Aggiungi la chiave in Orchestrator → Keys e associala al relay |
| Loop di `Handshake initiated` + `Removed duplicate peer` | Il peer B non è raggiungibile (chiave non autorizzata o non connesso) | Verifica che entrambi i peer abbiano le proprie chiavi aggiunte al relay |
| Relay mostra porta diversa da quella configurata | Bug porta (fix applicato in `servers.py`) | Redeploya il relay dalla UI per ricreare il pod con `--port` corretto |
| Health score 0% | Pod K8s non running | Controlla i log del pod in Relays → Detail → Logs |
| Utente bloccato su `pending` | Nessun admin ha approvato l'account | Approva da Impostazioni → Utenti in Attesa, o da SQL |
