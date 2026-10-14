# =============================================================
#  main.py - Entry point principale per Raspberry Pi Pico 2W
#  Carica questo file (insieme agli altri) sul Pico 2W
# =============================================================

import network
import time
import uasyncio as asyncio
from machine import Pin

import scanner
import web_server
from config import (
    WIFI_SSID, WIFI_PASSWORD,
    SCAN_INTERVAL, WEB_PORT, SUBNET
)

# LED integrato nel Pico 2W
led = Pin("LED", Pin.OUT)

# Evento per triggerare scansione manuale dal web
scan_event = asyncio.Event()


# ---- Connessione WiFi --------------------------------------------

def connect_wifi():
    """Connetti il Pico 2W alla rete WiFi. Ritorna l'IP assegnato."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan.ifconfig()[0]

    print(f"[WIFI] Connessione a '{WIFI_SSID}'...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 30
    blink   = 0
    while not wlan.isconnected() and timeout > 0:
        led.value(blink % 2)
        blink  += 1
        timeout -= 1
        time.sleep(0.5)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        led.on()
        print(f"[WIFI] Connesso! IP: {ip}")
        print(f"[WIFI] Dashboard: http://{ip}")
        return ip
    else:
        led.off()
        raise RuntimeError("Impossibile connettersi al WiFi. Controlla SSID e password in config.py")


# ---- Task principali asincroni -----------------------------------

async def task_scanner():
    """Task: esegui scansioni periodiche e su richiesta."""
    # Prima scansione all'avvio (piccolo ritardo per stabilizzare)
    await asyncio.sleep(3)
    print("[MAIN] Prima scansione di avvio...")
    await scanner.scan_network()

    while True:
        # Attendi l'evento manuale O il timeout periodico
        try:
            await asyncio.wait_for(scan_event.wait(), SCAN_INTERVAL)
            scan_event.clear()
            print("[MAIN] Scansione manuale richiesta dal web")
        except asyncio.TimeoutError:
            print(f"[MAIN] Scansione periodica (ogni {SCAN_INTERVAL}s)")

        # Non lanciare se già in corso
        if not scanner.scan_in_progress:
            await scanner.scan_network()


async def task_led_heartbeat():
    """Task: batte il LED ogni 5s per indicare che il sistema e' vivo."""
    while True:
        await asyncio.sleep(5)
        led.off()
        await asyncio.sleep(0.1)
        led.on()


async def task_web():
    """Task: avvia il web server."""
    await web_server.run_web_server(scan_trigger_event=scan_event)


async def task_watchdog():
    """Task: controlla connettivita' WiFi e riconnette se necessario."""
    wlan = network.WLAN(network.STA_IF)
    while True:
        await asyncio.sleep(60)
        if not wlan.isconnected():
            print("[WIFI] Connessione persa! Tentativo di riconnessione...")
            led.off()
            try:
                connect_wifi()
            except Exception as e:
                print(f"[WIFI] Riconnessione fallita: {e}")


# ---- Avvio -------------------------------------------------------

async def main():
    print("=" * 50)
    print("  Pico 2W - Monitor Rete Domestica")
    print("=" * 50)

    # Connetti WiFi (bloccante all'avvio)
    ip = connect_wifi()

    print(f"\n[MAIN] Subnet target: {SUBNET}.x")
    print(f"[MAIN] Dashboard web: http://{ip}:{WEB_PORT}")
    print(f"[MAIN] Intervallo scansione: {SCAN_INTERVAL}s")
    print("[MAIN] Avvio task asincroni...\n")

    # Avvia tutti i task in parallelo
    await asyncio.gather(
        task_scanner(),
        task_web(),
        task_led_heartbeat(),
        task_watchdog(),
    )


# ---- Esecuzione --------------------------------------------------

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n[MAIN] Interruzione manuale.")
    led.off()
except Exception as e:
    print(f"\n[MAIN] Errore fatale: {e}")
    led.off()
    # Il Pico si riavviera' automaticamente grazie al watchdog HW
    import machine
    time.sleep(5)
    machine.reset()
