# WPEX Orchestrator

![WPEX Orchestrator](https://img.shields.io/badge/WPEX-Orchestrator-7c6aef?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-3.0-009688?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-Vite-61dafb?style=flat-square&logo=react)
![Kubernetes](https://img.shields.io/badge/Kubernetes-namespace:wpex-326ce5?style=flat-square&logo=kubernetes)

**WPEX Orchestrator** è una piattaforma SaaS multi-tenant per l'orchestrazione e il monitoraggio centralizzato di nodi **WPEX** (WireGuard Packet Relay). Tramite una dashboard web moderna permette di fare provisioning dinamico di relay VPN su **Kubernetes**, gestire gli accessi (RBAC multi-tenant) e monitorare in tempo reale lo stato di salute e le performance della rete.

---

## 🌟 Caratteristiche Principali

- **Provisioning su Kubernetes**: Crea, avvia, ferma, riavvia e aggiorna relay WPEX come Deployment K8s con un click — completo di Service NodePort per UDP e HTTP.
- **Gestione Chiavi WireGuard**: Wallet centralizzato di public key cifrate con `pgcrypto`. Le chiavi vengono iniettate al relay via flag `--allow` al momento del deploy.
- **Monitoring Real-Time**: Dashboard KPI aggregata + per-relay: handshake rate, sessioni attive, peer connessi, dati trasferiti, health score pesato.
- **Diagnostica Remota**: Esegui `ping` e `traceroute` direttamente dal container del relay tramite K8s exec.
- **RBAC Multi-Tenant**: 4 ruoli (Admin, Executive, Engineer, Viewer) con isolamento completo delle risorse per organizzazione.
- **Audit Log**: Tracciabilità strutturata di tutte le operazioni critiche (crea/elimina relay, modifica chiavi, login, ecc.).
- **Topologia Visuale**: Mappa interattiva dello stato dei relay e delle connessioni.
- **Design Responsivo**: Frontend React + Vite con dark mode, glassmorphism e supporto mobile.
- **TLS automatico**: Nginx con Let's Encrypt / Certbot per HTTPS in produzione.

---

## 🚀 Architettura

```
Browser (HTTPS)
    │
    ▼
Nginx (TLS 1.3, Let's Encrypt)
    ├── /           → React Frontend (Vite, :3000)
    └── /api/*      → FastAPI Backend (Uvicorn, :8000)
                            │
                    ┌───────┴────────┐
               PostgreSQL        K8s API
            (wpex_keys_db)   (deploy/stop/restart relay pods)
                                    │
                        ┌───────────▼───────────┐
                        │  Pod: wpex-{name}      │
                        │  ├─ wpex Go binary     │
                        │  │   UDP :40xxx        │
                        │  └─ stats HTTP :8080   │
                        └───────────────────────┘
                                    ▲
                        WireGuard UDP (Site Routers)
```

Stack completo:
| Layer | Tecnologia |
|---|---|
| Frontend | React 18 + Vite |
| Backend API | Python 3.11 + FastAPI + Uvicorn |
| Database | PostgreSQL 15 + pgcrypto |
| Orchestrazione relay | Kubernetes (Python client) |
| Gateway / TLS | Nginx + Certbot / Let's Encrypt |
| Relay engine | Go binary (`wpex`) |

---

## 📖 Documentazione

Per l'architettura dettagliata, la guida all'uso dell'interfaccia e le istruzioni di deployment:

👉 **[Manuale Utente (USER_MANUAL.md)](USER_MANUAL.md)**

---

## 🛠️ Deploy Rapido (Docker Swarm)

L'orchestratore stesso (backend, frontend, DB, Nginx) gira su **Docker Swarm**. I relay WPEX figli vengono creati come pod **Kubernetes**.

```bash
# 1. Inizializza Swarm (se non già fatto)
docker swarm init

# 2. Crea i secret
printf "password_sicura_db"       | docker secret create db_password -
printf "chiave_crittografia_pgp"  | docker secret create db_encryption_key -
printf "segreto_jwt_super_lungo"  | docker secret create jwt_secret -

# 3. Deploy dello stack
docker stack deploy -c wpex-stack.yml wpex
```

> **Nota**: Il backend richiede accesso al kubeconfig per poter creare/gestire i pod relay nel namespace `wpex`.

---

## 🔐 Primo Accesso

1. Naviga all'indirizzo del server (HTTPS).
2. Registra il primo account — verrà creato in stato `pending`.
3. Attiva manualmente il primo admin da database:
   ```sql
   UPDATE users SET status='active', role='admin' WHERE username='tuo_utente';
   ```
4. Da quel momento, approva i nuovi utenti direttamente dalla UI → Impostazioni → Utenti in Attesa.

---

*Realizzato per orchestrare reti WireGuard mantenendo inalterata la crittografia E2E.*
