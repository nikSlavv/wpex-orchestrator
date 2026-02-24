# WPEX Orchestrator - Manuale Utente

## 1. Introduzione
**WPEX Orchestrator** è una piattaforma di gestione e orchestrazione centralizzata per nodi di rete (relays basati su WireGuard). Attraverso una dashboard unificata SaaS, permette di creare, configurare, monitorare e aggiornare istanze server dinamicamente tramite container Docker. 

Al suo cuore, il sistema utilizza **WPEX (WireGuard Packet Relay)**, un relay trasparente progettato per facilitare il NAT traversal senza mai compromettere o decifrare la crittografia end-to-end di WireGuard.

## 2. Architettura & Stack Tecnologico
L'applicazione segue un'architettura a microservizi pensata per essere distribuita in cluster **Docker Swarm**.

- **Motore VPN (WPEX)**: Scritto in Go, è un relay a zero-overhead (nessun problema di MTU) che instrada i pacchetti cifrati WireGuard direzionandoli unicamente in base all'indice del peer, senza alcuna conoscenza delle chiavi private. 
- **Frontend**: React.js (Vite), interamente responsive, UI moderna (Dark Mode/Glassmorphism).
- **Backend API**: Python 3.11 (FastAPI), gestisce la logica di business globale e comunica col daemon Docker per il provisioning dei nodi WPEX.
- **Database**: PostgreSQL persistito tramite volumi, per RBAC e storage chiavi.
- **Reverse Proxy**: Nginx funge da gateway principale, gestendo il traffico HTTP/HTTPS e il caricamento dei certificati SSL (Let's Encrypt tramite Certbot).

## 3. Il Motore WPEX: Come Funziona
A differenza di soluzioni hub-and-spoke in cui i pacchetti vengono decifrati sul server cloud, WPEX non possiede alcuna chiave privata. 
Durante la fase di elaborazione:
1. WPEX apprende l'indirizzo endpoint originario associato all'indice randomico (a 32 bit) che i peer WireGuard esibiscono nella sessione.
2. Inoltra i messaggi basandosi sull'indice ricevente.

### 3.1 Sicurezza e Protezione da Amplification Attacks
Per l'handshake inziale (essendo sprovvisto di indice ricevente noto), WPEX esegue un "broadcast" indirizzato agli endpoint noti. Per evitare che questa meccanica venga sfruttata da malintenzionati per attacchi DDoS/Amplification, WPEX Orchestrator inietta staticamente una lista di **Chiavi Pubbliche Autorizzate** (Whitelist) all'avvio del container.
In questo modo, WPEX scarta istantaneamente qualsiasi tentativo di handshake proveniente da peer le cui public key non siano registrate nel database, pur non potendo decifrarne il traffico.

### 3.2 Monitoring in Tempo Reale
Ogni nodo WPEX espone interfacce HTTP sulla porta `8080`. Seppur protette e proxate verso l'esterno dall'Orchestrator, forniscono costantemente metriche via JSON su:
- *Handshake Status* (Connessi vs Handshaking vs Disconnessi)
- *Sessioni VPN attive*
- *Conteggio Byte* per peer (Trasferimento Dati)
- *Tempi e log* (inclusi i roaming dei peer in caso di cambio rete dati).

## 4. Gestione Utenti e Ruoli (RBAC)
WPEX Orchestrator gestisce il controllo accessi tramite 4 livelli gerarchici per ambienti Multitenant:

- **Admin**: Controllo assoluto (Globale). Gestisce policy di sicurezza, tenant ed elimina risorse.
- **Executive**: Solo lettura (Globale). Visibilità su metriche di tutte le organizzazioni, senza permessi di scrittura.
- **Engineer**: Amministratore di Tenant (Locale). Modifica utenti, chiavi e relays della propria organizzazione.
- **Viewer**: Sola lettura (Locale). Visibilità limitata alle sole dashboard della propria organizzazione.

## 5. Guida ai Moduli Principali (Web UI)

### 5.1 Dashboard
Pannello riassuntivo con le KPI in tempo reale: totale Relay attivi, Health Score globale (calcolato incrociando lo stato dei container e delle API WPEX interne), allarmi critici e statistiche aggregate di banda.

### 5.2 Relays (Istanze Server)
Pannello operativo per l'orchestrazione. 
- **Creazione Rapida**: Assegna un nome, la porta UDP (es. 40000) e seleziona le chiavi pubbliche abilitate. L'Orchestrator avvierà istantaneamente il container WPEX esposto in rete.
- **Monitor View**: Ogni relay ha un suo pannello dedicato. Cliccandolo, si vedono i grafici di CPU/RAM del container aggregati alle statistiche interne di WireGuard (Handshakes, Active Sessions, Data Transferred).
- **Gestione del Ciclo di Vita**: Pulsanti diretti per Start, Stop, Delete, Restart; oltre ad utility per accedere ai log crudi in tempo reale.
- **Diagnostica Remota**: Include un mini-terminale HTTP per eseguire `Ping` e `Traceroute` eseguiti contestualmente dal container remoto del relay.

### 5.3 Chiavi Globali
Un portafoglio virtuale per le chiavi Pubbliche Wireguard (Peer Allowed). 
- Inserisci la stringa base64 (es. `AAAAAAAAAAAAAAAA...=`) nel wallet globale, che sarà criptata via PGP sul database. 
- Successivamente, all'interno della pagina "Relay Health", potrai scorrere quali chiavi "assegnare" al nodo. Alla pressione di *Salva e Riavvia*, l'Orchestrator inietterà a linea di comando i flag `--allow` necessari al processo Go di wpex per autorizzare i peer.

### 5.4 Topologia
Mappa dinamica interattiva in cui le "nuvole" rappresentano i Relay Cloud e i link tracciano lo stato delle interconnessioni, segnalando latenze critiche o interruzioni (colore ambra/rosso) in caso di cadute di rete o nodi in crash.

### 5.5 Impostazioni e Audit
Per gli amministratori, approvazione nuovi ingressi (utenti in stato `pending`), assegnazione ai Tenant e consultazione delle policy di sistema e tracciabilità operativa tramite Log strutturati delle azioni compiute.

## 6. Installazione & Deployment (Produzione)
Assicurarsi che il nodo principale esegua `Docker` in modalità Swarm (`docker swarm init`).
1. Creare i *secret* globali per il DB e JWT:
   ```bash
   printf "mypostgrespassword123" | docker secret create db_password -
   printf "myencryptionkey12345" | docker secret create db_encryption_key -
   printf "myjwtsecret12345678" | docker secret create jwt_secret -
   ```
2. Fare il deploy dello stack orchestratore:
   ```bash
   docker stack deploy -c wpex-stack.yml wpex
   ```
   Questa operazione avvierà i servizi backend, frontend, database, nginx proxy e automazione SSL Let's Encrypt.
   **Avviso Sicurezza**: Il Backend richiede l'accesso al socket Docker (`/var/run/docker.sock`) per lanciare nativamente i container child di `wpex`.

## 7. Flusso di Primo Accesso
1. A deploy terminato, naviga sull'indirizzo IP/Dominio associato.
2. Vai alla schermata di "Registrato" e crea il primo account. Poiché è il primo per il sistema, sarà salvato ma settato come `pending` (in attesa di accettazione secondo le policy SaaS).
3. L'operatore di sistema backend dovrà eseguire manualmente uno sblocco a database modificando lo status in `active` e scalando il `role` a `admin`. Da lì, l'amministratore potrà confermare o rifiutare le successive registrazioni comodamente via interfaccia web.
