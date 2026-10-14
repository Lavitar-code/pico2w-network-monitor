# 📡 Pico 2 W Network Monitor

![MicroPython](https://img.shields.io/badge/MicroPython-Pico%202%20W-2B2728?logo=micropython)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Pico%202%20W-A22846?logo=raspberrypi&logoColor=white)
![asyncio](https://img.shields.io/badge/uasyncio-concorrenza-3776AB?logo=python&logoColor=white)

Monitor della rete domestica che gira interamente su un **Raspberry Pi Pico 2 W** (microcontrollore da pochi euro).
Scansiona la rete locale, riconosce i dispositivi collegati, segnala quelli mai visti prima e mostra tutto in una **dashboard web** servita direttamente dal Pico.

## Funzionalità

- **Scansione della rete**: trova i dispositivi attivi sulla subnet con probe TCP asincroni (20 IP in parallelo)
- **Rilevamento intrusi**: alert quando compare un dispositivo mai visto prima
- **Storico**: per ogni dispositivo registra prima/ultima volta visto e numero di rilevamenti
- **Dashboard web**: pagina responsive (PC e telefono) con stato online/offline, statistiche e alert, aggiornata ogni 30 s
- **API JSON**: `GET /api/status` per integrare i dati in altri strumenti
- **Affidabilità**: watchdog che riconnette il Wi-Fi se cade, LED di stato, riavvio automatico in caso di errore

## Architettura

Quattro task concorrenti con `uasyncio` sullo stesso microcontrollore:

```
main.py
 ├── task_scanner   → scansione periodica (ogni 3 min) o su richiesta dal web
 ├── task_web       → server HTTP con dashboard e API
 ├── task_watchdog  → controlla il Wi-Fi ogni 60 s e riconnette
 └── task_led       → heartbeat sul LED integrato
```

| File | Ruolo |
|---|---|
| `main.py` | Avvio, connessione Wi-Fi, orchestrazione dei task |
| `scanner.py` | Motore di scansione TCP asincrono e registro dispositivi |
| `web_server.py` | Server HTTP minimale, dashboard HTML e API JSON |
| `config.py` | Parametri: Wi-Fi, subnet, tempi, dispositivi noti |

## Installazione

**Serve:** Raspberry Pi Pico 2 W, cavo USB, [Thonny IDE](https://thonny.org).

1. **MicroPython sul Pico**: tieni premuto `BOOTSEL`, collega l'USB, trascina il file `.uf2` scaricato da [micropython.org](https://micropython.org/download/RPI_PICO2_W/) nel disco `RPI-RP2`.
2. **Configura** `config.py`:
   ```python
   WIFI_SSID     = "NOME_RETE_WIFI"
   WIFI_PASSWORD = "PASSWORD_WIFI"
   SUBNET        = "192.168.1"   # prime 3 cifre del tuo IP (vedi `ipconfig`)
   ```
   Puoi dare un nome ai tuoi dispositivi in `KNOWN_DEVICES`.
3. **Carica i file** sul Pico con Thonny (`main.py`, `config.py`, `scanner.py`, `web_server.py`).
4. **Avvia** (F5 o ricollega il Pico). In console compare l'indirizzo, es. `http://192.168.1.45`: aprilo da un browser sulla stessa rete.

> ⚠️ Non pubblicare mai il tuo `config.py` con la password vera del Wi-Fi.

## Limiti

Il Pico 2 W non supporta la modalità promiscua: niente packet sniffing né lettura del traffico DNS.
Il monitor rileva i dispositivi tramite connessioni TCP sulle porte più comuni, quindi un dispositivo con tutte le porte chiuse può non comparire.
Per analisi del traffico vera serve un Raspberry Pi completo con Linux e strumenti come `tcpdump` o Wireshark.

> Usalo solo sulla tua rete o su reti dove hai il permesso di farlo.

## Autore

**Vittorio Gaudiello** — [@Lavitar-code](https://github.com/Lavitar-code)
