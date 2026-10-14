# =============================================================
#  PICO 2W - MONITOR DI RETE DOMESTICA
#  config.py - Modifica questi parametri prima di avviare
# =============================================================

# --- WiFi ---
WIFI_SSID     = "NOME_RETE_WIFI"       # Nome della tua rete WiFi
WIFI_PASSWORD = "PASSWORD_WIFI"        # Password della tua rete WiFi

# --- Rete locale ---
# Controlla il tuo router: di solito e' 192.168.1 oppure 192.168.0
SUBNET        = "192.168.1"            # Prime 3 cifre dell'IP della rete
SCAN_START    = 1                      # IP iniziale da scansionare (.1)
SCAN_END      = 254                    # IP finale da scansionare (.254)

# --- Timing ---
SCAN_INTERVAL = 180                    # Secondi tra una scansione e l'altra (180 = 3 min)
PROBE_TIMEOUT = 0.4                    # Timeout per ogni tentativo di connessione (sec)
MAX_CONCURRENT = 20                    # IP da scansionare in parallelo (non alzare troppo)

# --- Web Server ---
WEB_PORT      = 80                     # Porta del dashboard web (visita http://<IP_PICO>)

# --- Dispositivi noti (opzionale) ---
# Aggiungi qui i tuoi dispositivi per identificarli nel dashboard
# Formato: "IP": "Nome dispositivo"
KNOWN_DEVICES = {
    "192.168.1.1":   "Router",
    "192.168.1.2":   "PC principale",
    # "192.168.1.10":  "Smart TV",
    # "192.168.1.20":  "iPhone",
    # "192.168.1.30":  "Stampante",
}

# --- Sicurezza ---
ALERT_NEW_DEVICES = True               # Segnala dispositivi mai visti prima
MAX_ALERTS        = 50                 # Numero massimo di alert da conservare
MAX_HISTORY       = 10                 # Numero di scansioni da conservare nello storico

# --- Porte da testare per rilevare host attivi ---
PROBE_PORTS = [80, 443, 22, 8080, 53, 8888, 23, 21, 5000, 3000]
