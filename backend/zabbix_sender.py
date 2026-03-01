"""
WPEX Orchestrator — Zabbix Sender
Periodically polls every wpex relay container for stats and pushes
metrics into Zabbix via Zabbix API (host/item management) and
ZabbixSender (data ingestion on port 10051).

Metrics pushed per relay:
  wpex.bytes_rx            — cumulative bytes received across all peers
  wpex.bytes_tx            — cumulative bytes sent across all peers
  wpex.active_peers        — number of currently connected peers
  wpex.total_peers         — total peers known to the relay
  wpex.handshake_success   — handshake success rate (%)
  wpex.total_handshakes    — total handshake attempts
  wpex.uptime_seconds      — relay process uptime in seconds
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from pyzabbix import ZabbixAPI, ZabbixSender, ZabbixMetric
from fastapi import APIRouter

logger = logging.getLogger("zabbix_sender")

# ── Configuration ────────────────────────────────────────────────────
ZABBIX_HOST      = os.environ.get("ZABBIX_HOST", "host.docker.internal")
ZABBIX_API_URL   = os.environ.get("ZABBIX_URL", f"http://{ZABBIX_HOST}:8080")
ZABBIX_SENDER_PORT = int(os.environ.get("ZABBIX_SENDER_PORT", "10051"))
ZABBIX_USER      = os.environ.get("ZABBIX_USER", "Admin")
ZABBIX_PASS      = os.environ.get("ZABBIX_PASS", "zabbix")
POLL_INTERVAL    = int(os.environ.get("ZABBIX_POLL_INTERVAL", "60"))

HOST_GROUP_NAME  = "WPEX Relays"

# ── Metric definitions ────────────────────────────────────────────────
ITEM_DEFS = [
    {"key": "wpex.bytes_rx",          "name": "Bytes Received (total)",       "units": "B", "value_type": 3},
    {"key": "wpex.bytes_tx",          "name": "Bytes Sent (total)",           "units": "B", "value_type": 3},
    {"key": "wpex.active_peers",      "name": "Active Peers",                 "units": "",  "value_type": 3},
    {"key": "wpex.total_peers",       "name": "Total Peers",                  "units": "",  "value_type": 3},
    {"key": "wpex.handshake_success", "name": "Handshake Success Rate",       "units": "%", "value_type": 0},
    {"key": "wpex.total_handshakes",  "name": "Total Handshakes",             "units": "",  "value_type": 3},
    {"key": "wpex.uptime_seconds",    "name": "Relay Uptime",                 "units": "s", "value_type": 0},
]

# ── State ─────────────────────────────────────────────────────────────
_last_sync = {
    "time": None,
    "status": "never",
    "hosts_pushed": 0,
    "errors": [],
}

router = APIRouter(prefix="/api/zabbix/sender", tags=["zabbix_sender"])


# ── Zabbix API helpers ────────────────────────────────────────────────
def _get_api() -> ZabbixAPI:
    zapi = ZabbixAPI(ZABBIX_API_URL)
    zapi.session.verify = False
    zapi.timeout = 10
    zapi.login(ZABBIX_USER, ZABBIX_PASS)
    return zapi


def _ensure_host_group(zapi: ZabbixAPI) -> str:
    groups = zapi.hostgroup.get(filter={"name": [HOST_GROUP_NAME]}, output=["groupid"])
    if groups:
        return groups[0]["groupid"]
    res = zapi.hostgroup.create(name=HOST_GROUP_NAME)
    return res["groupids"][0]


def _ensure_host(zapi: ZabbixAPI, host_name: str, groupid: str) -> str:
    hosts = zapi.host.get(filter={"host": [host_name]}, output=["hostid"])
    if hosts:
        return hosts[0]["hostid"]
    res = zapi.host.create(
        host=host_name,
        name=host_name,
        groups=[{"groupid": groupid}],
        interfaces=[{
            "type": 1, "main": 1, "useip": 1,
            "ip": "127.0.0.1", "dns": "", "port": "10050",
        }],
    )
    return res["hostids"][0]


def _ensure_items(zapi: ZabbixAPI, hostid: str) -> dict:
    """Ensure all metric items exist for this host (Zabbix trapper type=2)."""
    existing = zapi.item.get(
        hostids=hostid,
        search={"key_": "wpex."},
        output=["itemid", "key_"],
    )
    key_to_id = {i["key_"]: i["itemid"] for i in existing}

    for item in ITEM_DEFS:
        if item["key"] not in key_to_id:
            res = zapi.item.create(
                hostid=hostid,
                name=item["name"],
                key_=item["key"],
                type=2,               # Zabbix trapper
                value_type=item["value_type"],
                units=item["units"],
                delay=0,
            )
            key_to_id[item["key"]] = res["itemids"][0]
            logger.debug(f"Created Zabbix item {item['key']} for host {hostid}")

    return key_to_id


# ── Stats fetch helpers ───────────────────────────────────────────────
def _fetch_relay_stats(container_name: str) -> Optional[dict]:
    """Fetch /api/v1/stats from a wpex relay container."""
    try:
        r = requests.get(f"http://{container_name}:8080/api/v1/stats", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _extract_metrics(stats: dict) -> dict:
    """Parse wpex stats JSON into flat metrics dict."""
    peers = stats.get("peers", [])
    active_peers = sum(1 for p in peers if p.get("status") == "connected")
    bytes_rx = sum(p.get("bytes_received", 0) for p in peers)
    bytes_tx = sum(p.get("bytes_sent", 0) for p in peers)
    total_hs = stats.get("total_handshakes", 0)
    success_hs = stats.get("successful_handshakes", 0)
    success_rate = round((success_hs / total_hs * 100), 2) if total_hs > 0 else 0.0
    uptime = stats.get("uptime_seconds", 0)

    return {
        "wpex.bytes_rx":          bytes_rx,
        "wpex.bytes_tx":          bytes_tx,
        "wpex.active_peers":      active_peers,
        "wpex.total_peers":       len(peers),
        "wpex.handshake_success": success_rate,
        "wpex.total_handshakes":  total_hs,
        "wpex.uptime_seconds":    uptime,
    }


# ── Main collection job ───────────────────────────────────────────────
def collect_and_push():
    """
    For each wpex relay server in the DB:
      1. Fetch /api/v1/stats
      2. Register host + items in Zabbix (idempotent)
      3. Send metrics via ZabbixSender (trapper protocol, port 10051)
    """
    from database import get_db

    errors = []
    pushed = 0

    # Connect to Zabbix API
    try:
        zapi = _get_api()
        groupid = _ensure_host_group(zapi)
    except Exception as e:
        msg = f"Zabbix API unreachable: {e}"
        logger.error(msg)
        _last_sync.update({"time": datetime.now().isoformat(), "status": "error", "hosts_pushed": 0, "errors": [msg]})
        return

    # Load servers from DB
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM servers")
        server_names = [row[0] for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"DB read failed: {e}")
        _last_sync.update({"time": datetime.now().isoformat(), "status": "error", "hosts_pushed": 0, "errors": [str(e)]})
        return

    # Prepare ZabbixSender once (connects to port 10051)
    sender = ZabbixSender(zabbix_server=ZABBIX_HOST, zabbix_port=ZABBIX_SENDER_PORT)

    for name in server_names:
        container_name = f"wpex-{name}"

        # Fetch stats from relay
        stats = _fetch_relay_stats(container_name)
        if stats is None:
            logger.debug(f"No stats from {container_name}, skipping")
            continue

        try:
            # Ensure Zabbix host + items exist
            hostid = _ensure_host(zapi, container_name, groupid)
            _ensure_items(zapi, hostid)

            # Build and send metrics
            metrics = _extract_metrics(stats)
            zbx_metrics = [
                ZabbixMetric(container_name, key, str(val))
                for key, val in metrics.items()
            ]
            result = sender.send(zbx_metrics)
            logger.info(f"Pushed {len(zbx_metrics)} metrics for {container_name}: {result}")
            pushed += 1

        except Exception as e:
            err = f"{container_name}: {e}"
            logger.error(f"Failed to push metrics for {container_name}: {e}")
            errors.append(err)

    _last_sync.update({
        "time": datetime.now().isoformat(),
        "status": "ok" if not errors else "partial",
        "hosts_pushed": pushed,
        "errors": errors,
    })
    logger.info(f"Zabbix sync done — {pushed}/{len(server_names)} hosts pushed")


# ── Scheduler ─────────────────────────────────────────────────────────
_scheduler = BackgroundScheduler(daemon=True)


def start_scheduler():
    """Start the background polling scheduler."""
    _scheduler.add_job(
        collect_and_push,
        "interval",
        seconds=POLL_INTERVAL,
        id="zabbix_collector",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(f"Zabbix collector started — polling every {POLL_INTERVAL}s → {ZABBIX_API_URL}")


# ── REST endpoints ─────────────────────────────────────────────────────
@router.post("/trigger")
def manual_trigger():
    """Manually trigger a Zabbix sync and return the result."""
    collect_and_push()
    return _last_sync


@router.get("/status")
def sync_status():
    """Return the last sync status."""
    return _last_sync
