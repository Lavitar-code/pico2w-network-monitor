# =============================================================
#  scanner.py - Motore di scansione della rete
#  Usa TCP async per rilevare host attivi senza privilegi root
# =============================================================

import uasyncio as asyncio
import time
import json

from config import (
    SUBNET, SCAN_START, SCAN_END,
    PROBE_TIMEOUT, MAX_CONCURRENT,
    PROBE_PORTS, KNOWN_DEVICES,
    ALERT_NEW_DEVICES, MAX_ALERTS, MAX_HISTORY
)

# ---- Stato globale ------------------------------------------------
device_registry  = {}   # { "ip": { name, first_seen, last_seen, status, times_seen } }
scan_history     = []   # Lista delle ultime N scansioni
alerts           = []   # Lista alert sicurezza
scan_in_progress = False
last_scan_time   = None
scan_count       = 0


# ---- Probe TCP asincrono -----------------------------------------

async def _probe_port(ip, port):
    """Prova a connettersi a ip:port. Ritorna True se l'host risponde."""
    try:
        conn = asyncio.open_connection(ip, port)
        reader, writer = await asyncio.wait_for(conn, PROBE_TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def is_host_alive(ip):
    """Controlla se un host e' attivo provando piu' porte comuni."""
    for port in PROBE_PORTS:
        if await _probe_port(ip, port):
            return True
    return False


# ---- Scansione subnet --------------------------------------------

async def _scan_batch(ips):
    """Scansiona un gruppo di IP in parallelo."""
    tasks   = [asyncio.create_task(is_host_alive(ip)) for ip in ips]
    results = await asyncio.gather(*tasks)
    return [(ip, alive) for ip, alive in zip(ips, results)]


async def scan_network():
    """Scansiona l'intera subnet e aggiorna il registro dei dispositivi."""
    global scan_in_progress, last_scan_time, scan_count

    if scan_in_progress:
        return []

    scan_in_progress = True
    scan_count += 1
    started_at   = time.time()
    found_ips    = []
    total        = SCAN_END - SCAN_START + 1
    scanned      = 0

    print(f"[SCAN #{scan_count}] Avvio scansione {SUBNET}.{SCAN_START} - {SUBNET}.{SCAN_END}")

    # Scansiona a gruppi di MAX_CONCURRENT IP
    batch = []
    for i in range(SCAN_START, SCAN_END + 1):
        batch.append(f"{SUBNET}.{i}")
        if len(batch) >= MAX_CONCURRENT:
            results  = await _scan_batch(batch)
            scanned += len(batch)
            for ip, alive in results:
                if alive:
                    found_ips.append(ip)
                    print(f"  [+] {ip}")
            batch = []
            # Piccola pausa per non sovraccaricare il chip
            await asyncio.sleep(0.05)

    # Ultimo batch parziale
    if batch:
        results  = await _scan_batch(batch)
        scanned += len(batch)
        for ip, alive in results:
            if alive:
                found_ips.append(ip)
                print(f"  [+] {ip}")

    elapsed       = time.time() - started_at
    last_scan_time = started_at
    scan_in_progress = False

    print(f"[SCAN #{scan_count}] Completata: {len(found_ips)} host attivi in {elapsed:.1f}s")

    # Aggiorna il registro
    _update_registry(found_ips, started_at)

    # Aggiungi allo storico
    _add_to_history(found_ips, started_at, elapsed)

    return found_ips


# ---- Registro dispositivi ----------------------------------------

def _update_registry(found_ips, now):
    """Aggiorna device_registry e genera alert per nuovi dispositivi."""
    global alerts

    # Marca tutti come offline temporaneamente
    for ip in device_registry:
        device_registry[ip]["status"] = "offline"

    for ip in found_ips:
        name = KNOWN_DEVICES.get(ip, "Dispositivo sconosciuto")
        is_new = ip not in device_registry

        if is_new:
            device_registry[ip] = {
                "ip":         ip,
                "name":       name,
                "first_seen": now,
                "last_seen":  now,
                "times_seen": 1,
                "status":     "online",
                "known":      ip in KNOWN_DEVICES,
            }
            if ALERT_NEW_DEVICES:
                _add_alert(
                    level="WARNING" if ip not in KNOWN_DEVICES else "INFO",
                    message=f"Nuovo dispositivo rilevato: {ip}  ({name})",
                    ip=ip,
                    timestamp=now,
                )
        else:
            entry = device_registry[ip]
            entry["last_seen"]  = now
            entry["times_seen"] += 1
            entry["status"]     = "online"
            entry["name"]       = name  # aggiorna se aggiunto a KNOWN_DEVICES


def _add_alert(level, message, ip, timestamp):
    global alerts
    alerts.insert(0, {
        "level":     level,
        "message":   message,
        "ip":        ip,
        "timestamp": timestamp,
    })
    if len(alerts) > MAX_ALERTS:
        alerts = alerts[:MAX_ALERTS]
    print(f"[ALERT {level}] {message}")


def _add_to_history(found_ips, started_at, elapsed):
    global scan_history
    scan_history.insert(0, {
        "scan_num":   scan_count,
        "timestamp":  started_at,
        "found":      len(found_ips),
        "elapsed":    round(elapsed, 1),
        "ips":        found_ips[:],
    })
    if len(scan_history) > MAX_HISTORY:
        scan_history = scan_history[:MAX_HISTORY]


# ---- Helpers pubblici --------------------------------------------

def get_online_devices():
    return [d for d in device_registry.values() if d["status"] == "online"]

def get_all_devices():
    return list(device_registry.values())

def get_alerts():
    return alerts

def get_stats():
    online  = len(get_online_devices())
    total   = len(device_registry)
    unknown = sum(1 for d in get_online_devices() if not d["known"])
    return {
        "online":     online,
        "total_ever": total,
        "unknown":    unknown,
        "scan_count": scan_count,
        "last_scan":  last_scan_time,
        "in_progress": scan_in_progress,
    }

def format_time(ts):
    if ts is None:
        return "Mai"
    t = time.localtime(int(ts))
    return f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
