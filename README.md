# WPEX Orchestrator

![WPEX Orchestrator Logo](https://img.shields.io/badge/WPEX-Orchestrator-7c6aef?style=for-the-badge)

**WPEX Orchestrator** è una piattaforma SaaS per l'orchestrazione e il monitoraggio centralizzato di nodi **WPEX** (WireGuard Packet Relay). Tramite una dashboard web moderna e intuitiva, permette di effettuare il provisioning dinamico di server VPN basati su Docker Swarm, gestire l'accesso degli utenti (RBAC Multitenant) e monitorare lo stato di salute e le performance della rete in tempo reale.

## 🌟 Caratteristiche Principali

- **Provisioning Dinamico (Docker Swarm)**: Crea, avvia, ferma ed elimina istanze server WPEX con un click.
- **Sicurezza Integrata**: Gestione centralizzata delle chiavi pubbliche WireGuard per prevenire attacchi di amplificazione (Anti-DDoS via whitelist).
- **Monitoring Real-Time**: Integrazione nativa con le API di diagnostica di WPEX per visualizzare handshake, sessioni attive e consumo di banda.
- **RBAC Multitenant**: Struttura a ruoli (Admin, Executive, Engineer, Viewer) per delegare l'accesso e isolare le risorse per organizzazione.
- **Topologia Visuale**: Mappa interattiva dello stato di rete e delle connessioni tra i relay.
- **Interfaccia Premium**: Frontend in React (Vite) con design responsivo, dark mode nativa e componenti glassmorphism.

## 🚀 Architettura

Il progetto segue un approccio a microservizi:
1. **Frontend**: Applicazione a singola pagina (SPA) React + Vite per un'esperienza utente fluida.
2. **Backend**: API scritte in Python (FastAPI) per orchestrare i container Docker comunicando col socket locale.
3. **Database**: PostgreSQL per la persistenza sicura di utenti, tenant e chiavi (cifrate con PGP).
4. **Gateway**: Nginx come reverse proxy per instradare le richieste API e servire l'app, con automazione Let's Encrypt (Certbot) per SSL.
5. **Worker Nodes**: Immagini Docker `wpex` che girano come servizi instradando il traffico WireGuard UDP.

## 📖 Documentazione

Per guide dettagliate sull'architettura, le regole di routing interne a WPEX, il setup e le istruzioni per l'uso dell'interfaccia, fai riferimento al manuale ufficiale:

👉 **[Consulta il Manuale Utente (USER_MANUAL.md)](USER_MANUAL.md)**

## 🛠️ Deploy Veloce

L'applicativo è progettato per girare su un cluster **Docker Swarm**. 
Un esempio rapido per avviare l'intero stack (DB, Backend, Frontend, Nginx):

```bash
# 1. Inizializza Swarm (se non già attivo)
docker swarm init

# 2. Crea i secret di sicurezza
printf "password_sicura_db" | docker secret create db_password -
printf "chiave_crittografia_pgp" | docker secret create db_encryption_key -
printf "segreto_jwt_super_lungo" | docker secret create jwt_secret -

# 3. Fai partire lo stack
docker stack deploy -c wpex-stack.yml wpex
```
> **Nota**: Il servizio backend richiede l'accesso al socket docker sul nodo manager per operare le creazioni dei container figlio.

---

*Realizzato per orchestrare dinamicamente le reti WireGuard mantenendo inalterata la crittografia E2E.*
