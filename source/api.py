'''

Author: Giulio Segre
Last modified date: 06-08-2026
www.giulio-virtual-world.com

________________________________

This script allows external communications for "core.py"
*Why is it in English? Because I decided so!

________________________________

Libreria minimale per inviare comandi a un ESP32 via Bluetooth (BLE) e,
in parallelo, a un webhook. Pensata per essere chiamata cosi', da codice
sincrono, senza "await":

    import api
    api.send_command_to_esp32(rps_label, fingers_count)

La chiamata non blocca: BLE e webhook partono ciascuno su un thread a
parte e vengono "dimenticati" (fire-and-forget); eventuali errori vengono
solo stampati, cosi' un problema di connessione non pianta core.py.

NOVITA' rispetto alla versione precedente:
Invece di aprire una NUOVA connessione BLE (connect + service discovery +
write + disconnect) ad ogni comando -- operazione che richiede 1-3+ secondi
ogni volta -- questa versione mantiene UNA connessione BLE persistente,
aperta una sola volta all'avvio e riutilizzata per tutti gli invii
successivi. Il primo comando sara' un po' piu' lento (deve connettersi),
tutti i successivi saranno quasi istantanei. Se la connessione cade, si
riconnette automaticamente al comando successivo.

CONFIGURAZIONE: modifica le 3 costanti qui sotto.
DIPENDENZE:      pip install bleak requests
'''

import asyncio
import json
import threading
import time

import requests
from bleak import BleakClient

# --- CONFIG: da adattare al tuo ESP32 / server ---------------------------
ESP32_BLE_ADDRESS = "f4:2d:c9:8d:33:72"                          # indirizzo BLE dell'ESP32
ESP32_BLE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"     # UUID characteristic GATT
WEBHOOK_URL = "https://discord.com/api/webhooks/1532783717313941734/Ntwa9-xqSv_UOM03xi9D-mbs-8o1x9bH8vrxypGVbHgWGV7UCwLEKzKmSP-zD7mrqR2C" # "" per disabilitare
# ---------------------------------------------------------------------------


class _BLEConnection:
    """Gestisce una connessione BLE persistente su un thread/event-loop dedicato."""

    def __init__(self, address: str, char_uuid: str):
        self._address = address
        self._char_uuid = char_uuid
        self._client: BleakClient | None = None
        self._loop = asyncio.new_event_loop()
        self._lock = asyncio.Lock()
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _ensure_connected(self) -> None:
        if self._client is not None and self._client.is_connected:
            return
        self._client = BleakClient(self._address)
        await self._client.connect()
        print("[api] BLE: connesso (connessione persistente)")

    async def _write(self, payload: dict) -> None:
        async with self._lock:
            await self._ensure_connected()
            # response=False = "write senza conferma": piu' veloce, va bene
            # per un flusso di comandi non critici come questo.
            await self._client.write_gatt_char(
                self._char_uuid, json.dumps(payload).encode(), response=False
            )

    def send(self, payload: dict) -> None:
        """Invia il payload sulla connessione persistente (non blocca il chiamante)."""
        future = asyncio.run_coroutine_threadsafe(self._write(payload), self._loop)

        def _on_done(f):
            exc = f.exception()
            if exc:
                print(f"[api] BLE: invio fallito ({exc})")

        future.add_done_callback(_on_done)


_ble_connection = _BLEConnection(ESP32_BLE_ADDRESS, ESP32_BLE_CHAR_UUID)


def _send_webhook(payload: dict) -> None:
    if not WEBHOOK_URL:
        return
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[api] Webhook: invio fallito ({e})")


def send_command_to_esp32(rps_label, fingers_count, fingers_up=None) -> None:
    """Invia il comando via BLE (connessione persistente) e via webhook, senza bloccare.

    fingers_up: lista di 5 booleani nell'ordine [Pollice, Indice, Medio, Anulare, Mignolo],
    come restituita da core.py::count_fingers(). Viene codificata come stringa di 5 cifre
    "1"/"0" (es. "01100" = solo Indice e Medio alzati) e inviata nel campo "fingers_pattern".
    """
    fingers_pattern = "".join("1" if f else "0" for f in fingers_up) if fingers_up is not None else "00000"
    payload = {
        "rps_label": rps_label,
        "fingers_count": fingers_count,
        "fingers_pattern": fingers_pattern,  # ordine: Pollice,Indice,Medio,Anulare,Mignolo
        "ts": time.time(),
    }
    _ble_connection.send(payload)
    threading.Thread(target=_send_webhook, args=(payload,), daemon=True).start()


if __name__ == "__main__":
    time.sleep(3)  # da' tempo ai thread di finire prima che il programma esca
