# =============================================================
#  web_server.py - Dashboard HTTP servita dal Pico 2W
#  Visita http://<IP_PICO> dal browser del PC / telefono
# =============================================================

import socket
import json
import time
import scanner
from config import WEB_PORT


# ---- HTML del Dashboard -----------------------------------------

def _build_html():
    stats   = scanner.get_stats()
    devices = scanner.get_all_devices()
    alerts  = scanner.get_alerts()

    # Ordina: online prima, poi per IP
    devices.sort(key=lambda d: (0 if d["status"] == "online" else 1,
                                [int(x) for x in d["ip"].split(".")]))

    # Card dispositivi
    device_rows = ""
    for d in devices:
        status_cls  = "online" if d["status"] == "online" else "offline"
        known_badge = "" if d["known"] else '<span class="badge-unknown">NUOVO</span>'
        device_rows += f"""
        <div class="device-card {status_cls}">
          <div class="dev-header">
            <span class="dot {status_cls}"></span>
            <span class="dev-name">{d['name']}</span>
            {known_badge}
          </div>
          <div class="dev-ip">{d['ip']}</div>
          <div class="dev-meta">
            Visto {d['times_seen']}x &nbsp;|&nbsp; Ultimo: {scanner.format_time(d.get('last_seen'))}
          </div>
        </div>"""

    # Alert rows
    alert_rows = ""
    for a in alerts[:15]:
        lvl_cls = "warn" if a["level"] == "WARNING" else "info"
        alert_rows += f"""
        <div class="alert-row {lvl_cls}">
          <span class="alert-time">{scanner.format_time(a['timestamp'])}</span>
          <span class="alert-lvl">{a['level']}</span>
          <span class="alert-msg">{a['message']}</span>
        </div>"""

    if not alert_rows:
        alert_rows = '<div class="no-alerts">Nessun alert al momento ✓</div>'

    scan_btn_label = "⏳ Scansione in corso..." if stats["in_progress"] else "🔍 Avvia scansione ora"
    scan_btn_dis   = "disabled" if stats["in_progress"] else ""

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>Pico 2W · Monitor Rete</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    :root {{
      --bg:        #0d1117;
      --surface:   #161b22;
      --surface2:  #21262d;
      --border:    #30363d;
      --green:     #3fb950;
      --red:       #f85149;
      --yellow:    #d29922;
      --blue:      #58a6ff;
      --purple:    #bc8cff;
      --text:      #e6edf3;
      --muted:     #8b949e;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 1.5rem;
    }}
    header {{
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    header h1 {{
      font-size: 1.4rem;
      font-weight: 700;
      background: linear-gradient(135deg, var(--blue), var(--purple));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .subtitle {{ color: var(--muted); font-size: 0.8rem; margin-top: 2px; }}
    .wifi-icon {{ font-size: 2rem; }}

    /* Stats bar */
    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .stat-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem;
      text-align: center;
    }}
    .stat-num {{
      font-size: 2rem;
      font-weight: 700;
      line-height: 1;
    }}
    .stat-label {{ color: var(--muted); font-size: 0.75rem; margin-top: 4px; }}
    .c-green {{ color: var(--green); }}
    .c-red   {{ color: var(--red);   }}
    .c-blue  {{ color: var(--blue);  }}
    .c-yellow{{ color: var(--yellow);}}

    /* Sezioni */
    .section-title {{
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    /* Griglia dispositivi */
    .devices-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 0.75rem;
      margin-bottom: 2rem;
    }}
    .device-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem;
      transition: transform .15s, border-color .15s;
    }}
    .device-card:hover {{ transform: translateY(-2px); border-color: var(--blue); }}
    .device-card.online  {{ border-left: 3px solid var(--green); }}
    .device-card.offline {{ border-left: 3px solid var(--border); opacity: 0.55; }}
    .dev-header {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.4rem;
      flex-wrap: wrap;
    }}
    .dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .dot.online  {{ background: var(--green); box-shadow: 0 0 6px var(--green); }}
    .dot.offline {{ background: var(--muted); }}
    .dev-name  {{ font-weight: 600; font-size: 0.9rem; }}
    .dev-ip    {{ color: var(--blue); font-size: 0.8rem; font-family: monospace; }}
    .dev-meta  {{ color: var(--muted); font-size: 0.72rem; margin-top: 4px; }}
    .badge-unknown {{
      background: rgba(242,163,44,.15);
      color: var(--yellow);
      border: 1px solid rgba(242,163,44,.3);
      font-size: 0.65rem;
      padding: 1px 6px;
      border-radius: 4px;
      font-weight: 600;
    }}

    /* Alert */
    .alerts-box {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 2rem;
    }}
    .alert-row {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.6rem 1rem;
      border-bottom: 1px solid var(--border);
      font-size: 0.82rem;
    }}
    .alert-row:last-child {{ border-bottom: none; }}
    .alert-row.warn {{ background: rgba(248,81,73,.05); }}
    .alert-row.info {{ background: rgba(88,166,255,.05); }}
    .alert-time {{ color: var(--muted); font-family: monospace; white-space: nowrap; }}
    .alert-lvl  {{
      font-size: 0.7rem; font-weight: 700; padding: 2px 6px;
      border-radius: 4px; white-space: nowrap;
    }}
    .warn .alert-lvl {{ background: rgba(248,81,73,.2);  color: var(--red);  }}
    .info .alert-lvl {{ background: rgba(88,166,255,.2); color: var(--blue); }}
    .alert-msg {{ flex: 1; }}
    .no-alerts {{ color: var(--muted); padding: 1rem; text-align: center; font-size: 0.85rem; }}

    /* Bottone scan */
    .actions {{ margin-bottom: 2rem; display: flex; gap: 1rem; align-items: center; }}
    .btn {{
      background: linear-gradient(135deg, var(--blue), var(--purple));
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0.6rem 1.4rem;
      font-size: 0.9rem;
      font-family: inherit;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
      transition: opacity .2s, transform .1s;
    }}
    .btn:hover:not([disabled]) {{ opacity: 0.85; transform: translateY(-1px); }}
    .btn[disabled] {{ opacity: 0.4; cursor: not-allowed; }}
    .refresh-note {{ color: var(--muted); font-size: 0.75rem; }}

    footer {{ color: var(--muted); font-size: 0.75rem; text-align: center; padding-top: 1rem; }}
  </style>
</head>
<body>

<header>
  <div class="wifi-icon">📡</div>
  <div>
    <h1>Monitor Rete Domestica</h1>
    <div class="subtitle">Raspberry Pi Pico 2W &nbsp;|&nbsp; Ultima scansione: {scanner.format_time(stats['last_scan'])}</div>
  </div>
</header>

<!-- Statistiche -->
<div class="stats-bar">
  <div class="stat-card">
    <div class="stat-num c-green">{stats['online']}</div>
    <div class="stat-label">🟢 Online ora</div>
  </div>
  <div class="stat-card">
    <div class="stat-num c-blue">{stats['total_ever']}</div>
    <div class="stat-label">📋 Visti in totale</div>
  </div>
  <div class="stat-card">
    <div class="stat-num c-yellow">{stats['unknown']}</div>
    <div class="stat-label">⚠️ Sconosciuti online</div>
  </div>
  <div class="stat-card">
    <div class="stat-num c-blue">{stats['scan_count']}</div>
    <div class="stat-label">🔄 Scansioni eseguite</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="font-size:1rem; padding-top:0.3rem;">{'🟡 IN CORSO' if stats['in_progress'] else '✅ IDLE'}</div>
    <div class="stat-label">Stato scanner</div>
  </div>
</div>

<!-- Bottoni azione -->
<div class="actions">
  <a href="/scan" class="btn" {"" if not stats['in_progress'] else 'style="pointer-events:none;opacity:.4;"'}>
    {scan_btn_label}
  </a>
  <a href="/" class="btn" style="background: var(--surface2); border: 1px solid var(--border);">
    🔃 Aggiorna
  </a>
  <span class="refresh-note">La pagina si aggiorna automaticamente ogni 30 secondi</span>
</div>

<!-- Dispositivi -->
<div class="section-title">📱 Dispositivi rilevati</div>
<div class="devices-grid">
  {device_rows if device_rows else '<div style="color:var(--muted);grid-column:1/-1">Nessun dispositivo trovato. Avvia una scansione.</div>'}
</div>

<!-- Alert sicurezza -->
<div class="section-title">🚨 Alert sicurezza</div>
<div class="alerts-box">
  {alert_rows}
</div>

<footer>
  Pico 2W Network Monitor &nbsp;•&nbsp; Aggiornamento automatico ogni 30s
</footer>

</body>
</html>"""
    return html


# ---- HTTP Server semplice ----------------------------------------

def _parse_request(raw):
    """Estrae metodo e path dalla prima riga HTTP."""
    try:
        first_line = raw.split(b"\r\n")[0].decode()
        parts = first_line.split(" ")
        return parts[0], parts[1]
    except Exception:
        return "GET", "/"


def _send_response(conn, status, content_type, body):
    if isinstance(body, str):
        body = body.encode()
    response = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode() + body
    conn.sendall(response)


def _redirect(conn, location):
    response = (
        f"HTTP/1.1 302 Found\r\nLocation: {location}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode()
    conn.sendall(response)


import uasyncio as asyncio

async def run_web_server(scan_trigger_event=None):
    """Avvia il web server HTTP asincrono."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", WEB_PORT))
    server.setblocking(False)
    server.listen(5)
    print(f"[WEB] Server avviato sulla porta {WEB_PORT}")

    while True:
        try:
            conn, addr = server.accept()
            asyncio.create_task(_handle_client(conn, addr, scan_trigger_event))
        except OSError:
            pass
        await asyncio.sleep(0.05)


async def _handle_client(conn, addr, scan_trigger_event):
    try:
        conn.setblocking(False)
        raw = b""
        for _ in range(20):
            try:
                chunk = conn.recv(512)
                if chunk:
                    raw += chunk
                    if b"\r\n\r\n" in raw:
                        break
            except OSError:
                pass
            await asyncio.sleep(0.02)

        method, path = _parse_request(raw)
        print(f"[WEB] {method} {path} da {addr[0]}")

        if path == "/" or path.startswith("/?"):
            html = _build_html()
            _send_response(conn, "200 OK", "text/html", html)

        elif path == "/scan":
            # Avvia scansione se non già in corso
            if not scanner.scan_in_progress and scan_trigger_event is not None:
                scan_trigger_event.set()
            _redirect(conn, "/")

        elif path == "/api/status":
            data = {
                "stats":   scanner.get_stats(),
                "devices": scanner.get_all_devices(),
                "alerts":  scanner.get_alerts()[:10],
            }
            _send_response(conn, "200 OK", "application/json", json.dumps(data))

        else:
            _send_response(conn, "404 Not Found", "text/plain", "404 Not Found")

    except Exception as e:
        print(f"[WEB] Errore client: {e}")
    finally:
        conn.close()
