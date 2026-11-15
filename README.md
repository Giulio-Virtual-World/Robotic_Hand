<p align="center">
  <img src="Ancora-Non-disponibile" alt="Robotic Hand - Copertina del progetto" width="100%">
</p>

# ROBOTIC HAND – Hand Tracking + Sasso Carta Forbici + Controllo ESP32

Progetto che riconosce la mano tramite webcam, capisce quali dita sono alzate e invia il risultato a un **ESP32** via **Bluetooth Low Energy (BLE)** per comandare una mano robotica.

Repository: <https://github.com/Giulio-Virtual-World/Robotic_Hand>

---

# INDICE
1. [Cosa fa questo script](#cosa-fa-questo-script)
2. [Requisiti](#requisiti)
3. [Installazione](#installazione)
4. [Configurazione di `api.py`](#configurazione-di-apipy)
5. [Avvio](#avvio)
6. [Comandi a runtime](#comandi-a-runtime)
7. [Modello](#modello)
8. [Come funziona il riconoscimento delle dita](#come-funziona-il-riconoscimento-delle-dita)
9. [Logica Sasso / Carta / Forbici](#logica-sasso--carta--forbici)
10. [Perché LIVE_STREAM e non IMAGE/VIDEO](#perché-live_stream-e-non-imagevideo)
11. [JSON output](#json-output)
12. [Risoluzione dei problemi](#risoluzione-dei-problemi)
13. [Licenza e crediti](#licenza-e-crediti)

---

# COSA FA QUESTO SCRIPT

1. Apre la webcam (indice `0`) e processa il flusso video in tempo reale usando la modalità `LIVE_STREAM` del `GestureRecognizer` di **MediaPipe** (asincrona, con callback). Viene tracciata **una sola mano** (`num_hands=1`).

2. Il modello riconosce anche i gesti "canned" (predefiniti): `Closed_Fist`, `Open_Palm`, `Victory`, `Thumb_Up`, `Thumb_Down`, `Pointing_Up`, `ILoveYou`, `None`. Questi gesti vengono mostrati nell'interfaccia **solo come riferimento informativo**: non vengono usati per decidere il gesto di gioco né per i comandi inviati all'ESP32.

3. In parallelo, calcola in modo indipendente (dai 21 landmark della mano) quante e quali dita sono alzate, e le mostra in un'interfaccia grafica overlay realizzata con **OpenCV**.

4. Deduce il gesto di "sasso carta forbici" dal pattern delle dita alzate e lo mostra a schermo.

5. Quando il pattern delle dita cambia, invia i dati all'**ESP32 via Bluetooth (BLE)** e, in parallelo, a un **webhook** opzionale (vedi [JSON output](#json-output)).

### Logica Sasso / Carta / Forbici

| Gesto   | Condizione                                                                 |
|---------|----------------------------------------------------------------------------|
| SASSO   | 0 dita alzate (pugno chiuso)                                               |
| CARTA   | 5 dita alzate (mano aperta)                                                |
| FORBICI | Indice e medio alzati, anulare e mignolo abbassati (il pollice è ininfluente) |

Qualsiasi altro pattern non corrisponde a nessuno dei tre gesti (`rps_label = None`).

> **Vecchia logica (non più usata):** `Closed_Fist → SASSO`, `Open_Palm → CARTA`, `Victory → FORBICI`, basata sui gesti canned del modello. È stata sostituita dal conteggio delle dita perché più flessibile.

---

# REQUISITI

### Software richiesto
| Componente | Dettaglio |
|---|---|
| Sistema operativo | **Windows** (`installer.py` e `start.py` usano `venv\Scripts\python.exe` e `cmd`) |
| Python | **3.10 o superiore**, in una versione supportata da MediaPipe (controlla su [pypi.org/project/mediapipe](https://pypi.org/project/mediapipe/)) |
| Librerie Python | `mediapipe`, `opencv-python`, `numpy`, `bleak`, `requests` |
| Software ESP32 | [Arduino IDE](https://www.arduino.cc/en/software) con il supporto schede ESP32 installato |

> Su Linux/macOS il programma può funzionare, ma `installer.py` e `start.py` no: va fatta l'installazione manuale e il percorso del Python del venv è diverso (`venv/bin/python`).

### Hardware richiesto
| Componente | Dettaglio |
|---|---|
| Ancora non disponibile | -- |

---

# INSTALLAZIONE

### Procedura passo-passo

1. **Scarica i file da GitHub**
   Vai su <https://github.com/Giulio-Virtual-World/Robotic_Hand/tree/main/source> e scarica **tutti** i file della cartella `source`:
   * `core.py` – programma principale (hand tracking)
   * `api.py` – comunicazione con ESP32 (BLE) e webhook
   * `installer.py` – crea il venv e installa le librerie
   * `start.py` – avvia `core.py` nel venv
   * `NOME_FILE.ino` – sketch Arduino da caricare sull'ESP32

2. **Metti tutti i file nella stessa cartella**
   `core.py` importa `api.py`, quindi devono stare insieme. Esempio: `C:\Robotic_Hand\`.

3. **Installa Python (se non lo hai già)**
   Scaricalo da [python.org](https://www.python.org/downloads/) e, durante l'installazione, spunta **"Add python.exe to PATH"**. Verifica aprendo `cmd` e digitando `python --version`.

4. **Esegui `installer.py`**
   Doppio clic sul file oppure, da terminale nella cartella del progetto:
   ```
   python installer.py
   ```
   Lo script crea l'ambiente virtuale `venv`, installa `mediapipe`, `opencv-python` e `numpy` e verifica che MediaPipe sia presente.

5. **Installa le librerie per il Bluetooth e il webhook**
   `installer.py` **non** installa `bleak` e `requests`, ma `api.py` ne ha bisogno. Dalla cartella del progetto:
   ```
   venv\Scripts\python.exe -m pip install bleak requests
   ```

6. **Carica lo sketch sull'ESP32**
   * Apri `NOME_FILE.ino` con l'Arduino IDE.
   * Installa il supporto ESP32 (*Strumenti → Scheda → Gestore schede → "esp32"*).
   * Seleziona la tua scheda e la porta COM, poi premi **Carica**.
   * Lo sketch deve esporre una characteristic GATT con UUID `0000ffe1-0000-1000-8000-00805f9b34fb` in scrittura (è l'UUID usato da `api.py`).

7. **Configura `api.py`**
   Inserisci indirizzo BLE e UUID del tuo ESP32 (vedi [Configurazione di `api.py`](#configurazione-di-apipy)).

8. **Avvia il programma**
   Esegui `start.py` (vedi [Avvio](#avvio)).

### Installazione manuale (alternativa a `installer.py`)

Se `installer.py` non dovesse funzionare, apri il terminale (`cmd`) ed esegui i comandi seguenti.

**Entra nella cartella del progetto:**
> `cd percorso\verso\la\cartella`

**Crea un ambiente virtuale (consigliato):**
> `python -m venv venv`

**Attiva l'ambiente virtuale:**
> `venv\Scripts\activate`

**Installa tutte le librerie necessarie:**
> `pip install mediapipe opencv-python numpy bleak requests`

**Verifica l'installazione di MediaPipe:**
> `pip show mediapipe`

---

# CONFIGURAZIONE DI `api.py`

In cima ad `api.py` ci sono tre costanti da adattare:

```python
ESP32_BLE_ADDRESS   = "xx:xx:xx:xx:xx:xx"                         # indirizzo BLE dell'ESP32
ESP32_BLE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"      # UUID della characteristic GATT
WEBHOOK_URL         = ""                                          # "" per disabilitare il webhook
```

* **`ESP32_BLE_ADDRESS`**: l'indirizzo BLE della tua scheda. Puoi trovarlo con un'app come *nRF Connect* (Android/iOS) cercando il nome con cui l'ESP32 si annuncia via Bluetooth. Su macOS l'indirizzo è un UUID e non un MAC.
* **`ESP32_BLE_CHAR_UUID`**: deve coincidere con quello definito nello sketch `.ino`.
* **`WEBHOOK_URL`**: URL a cui inviare lo stesso JSON via `POST`. Lascia `""` per disabilitarlo.

> ℹ️ I webhook di Discord accettano solo messaggi con campi specifici (es. `content`): il JSON di questo progetto verrebbe in genere rifiutato. Usa un endpoint che accetti JSON arbitrario oppure disabilita il webhook.

**Comportamento della connessione BLE:** `api.py` apre **una sola connessione persistente** al primo comando (può richiedere qualche secondo) e la riutilizza per tutti i successivi, che risultano quindi quasi istantanei. Se la connessione cade, si riconnette automaticamente al comando seguente. Gli invii non bloccano il programma: eventuali errori vengono solo stampati nel terminale.

---

# AVVIO

**Per avviare il programma esegui il file `start.py`** (apre una finestra `cmd` e lancia `core.py` nell'ambiente virtuale).

Se il file non dovesse funzionare, apri il terminale nella cartella del progetto e digita:

**Attiva l'ambiente virtuale:**
> `venv\Scripts\activate`

**Esegui lo script:**
> `python core.py`

All'avvio si apre una finestra con l'immagine della webcam (a specchio) e l'overlay con gesto, conteggio dita e FPS.

---

# COMANDI A RUNTIME

| Tasto | Azione |
|---|---|
| `q` | esci |
| `m` | mostra/nascondi i 21 landmark della mano (visibili di default) |

---

# MODELLO

Il task richiede un modello `.task` pre-addestrato (non è incluso nel pacchetto pip).

Lo script `core.py` lo scarica **automaticamente al primo avvio** nella stessa cartella di `core.py` (file `gesture_recognizer.task`). Serve quindi una connessione a internet solo la prima volta.

Se preferisci scaricarlo manualmente: <https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task>
e posizionalo accanto a `core.py`.

---

# COME FUNZIONA IL RICONOSCIMENTO DELLE DITA

Il riconoscimento delle dita alzate avviene in modo indipendente dal classificatore di gesti e si basa sui 21 landmark della mano forniti da MediaPipe.

Il criterio è interamente **basato sulle distanze** tra i landmark (calcolate in 2D, sul piano dell'immagine): non dipende dal fatto che l'immagine sia specchiata né dalla rotazione della mano nel piano. Può invece risentire di inclinazioni forti della mano rispetto alla webcam (ad esempio le dita puntate verso l'obiettivo), perché le distanze 2D si accorciano per effetto della prospettiva.

**Normalizzazione:** tutte le distanze vengono divise per la "dimensione della mano", cioè la distanza tra il polso (`WRIST`) e il MCP del medio (`MIDDLE_MCP`). In questo modo il risultato non cambia se la mano è più vicina o più lontana dalla webcam.
```python
hand_size = max(_dist(lm[WRIST], lm[MIDDLE_MCP]), 1e-6)
```

La funzione `_dist()` calcola la distanza euclidea (in 2D) tra due landmark:
```python
def _dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
```

**Per indice, medio, anulare e mignolo:** il dito è considerato **abbassato** se la punta (TIP) è abbastanza vicina alla base del dito stesso (MCP), altrimenti è alzato.

> * Se la distanza normalizzata TIP-MCP dell'indice è inferiore alla soglia, l'indice è abbassato.
> * Lo stesso vale per medio, anulare e mignolo, ciascuno con il proprio TIP e il proprio MCP.

```python
for i, (tip, mcp) in enumerate(zip(tips, mcps), start=1):
    finger_down = _dist(lm[tip], lm[mcp]) / hand_size < FINGER_CLOSE_RATIO
    fingers_up[i] = not finger_down
```

**Per il pollice:** è considerato **abbassato** se la sua punta (TIP) è abbastanza vicina alla base (MCP) di **almeno una** delle altre quattro dita (indice, medio, anulare o mignolo). Se non è vicina a nessuna di queste basi, il pollice è alzato.
```python
other_bases = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
thumb_down = any(
    _dist(lm[THUMB_TIP], lm[base]) / hand_size < THUMB_CLOSE_RATIO
    for base in other_bases
)
fingers_up[0] = not thumb_down
```

**Soglie:** sono definite come costanti in cima a [`core.py`](./source/core.py) e possono essere regolate in base alla propria mano e alla webcam:
```python
FINGER_CLOSE_RATIO = 0.60  # dita lunghe: punta vs. propria base (MCP)
THUMB_CLOSE_RATIO = 0.45   # pollice: punta vs. base (MCP) di un qualsiasi altro dito
```
> * Se un dito risulta abbassato quando in realtà è alzato, **abbassa** il valore della soglia.
> * Se un dito risulta alzato quando in realtà è piegato, **alza** il valore della soglia.

In questo modo il riconoscimento delle dita non dipende dalle categorie di gesto ("Closed_Fist", "Open_Palm", "Victory", ecc.) del classificatore di MediaPipe, ma viene ricavato direttamente dalla geometria dei landmark della mano.

---

# PERCHÉ LIVE_STREAM E NON IMAGE/VIDEO

* **IMAGE:** per una singola immagine statica (foto).
* **VIDEO:** per un file video già registrato, elaborato in modo sincrono frame per frame con `recognize_for_video()`.
* **LIVE_STREAM:** pensata apposta per input continuo in tempo reale (webcam). È **asincrona**: si invia un frame con `recognize_async(image, timestamp_ms)` e il risultato arriva **dopo**, tramite una funzione di callback (`result_callback`) passata in fase di creazione delle opzioni. Il timestamp deve essere monotono crescente, altrimenti MediaPipe genera un errore.

---

# JSON OUTPUT

Lo script invia le informazioni sul riconoscimento della mano tramite la funzione:
```python
api.send_command_to_esp32(rps_label, fingers_count, fingers_up)
```
La funzione riceve tre informazioni:
> * `rps_label`: il gesto riconosciuto tra `"SASSO"`, `"CARTA"`, `"FORBICI"` oppure `None`;
> * `fingers_count`: il numero totale di dita alzate, da `0` a `5`;
> * `fingers_up`: lista di cinque booleani che indica, nell'ordine, quali dita sono alzate.

La lista `fingers_up` ha il seguente ordine:
```python
[Pollice, Indice, Medio, Anulare, Mignolo]
```
Ad esempio `[False, True, True, False, False]` indica che sono alzati solamente **indice e medio**, corrispondenti al gesto **FORBICI**.

Il numero di dita alzate si ottiene direttamente dalla lista:
```python
fingers_count = sum(fingers_up)
```

### Quando viene inviato il comando

Il comando viene inviato **solo quando il pattern delle dita cambia** rispetto all'ultimo invio (per non ripetere lo stesso comando a ogni frame). Si confronta quindi l'intera lista `fingers_up`, non solo il conteggio: passare da "solo indice" a "solo medio" genera un nuovo invio anche se il numero di dita (1) è lo stesso.

```python
ex_fingers_pattern = globals().get('ex_fingers_pattern', -1)

if fingers_up != ex_fingers_pattern:
    globals()['ex_fingers_pattern'] = fingers_up
    ex_fingers_pattern = fingers_up

    api.send_command_to_esp32(rps_label, fingers_count, fingers_up)
```

> Il comando viene valutato solo quando una mano è visibile: se la mano esce dall'inquadratura non viene inviato alcun comando di "mano assente".

### Formato del messaggio

`core.py` non costruisce il JSON: lo fa `send_command_to_esp32()` in [`api.py`](./source/api.py), che trasforma `fingers_up` in una stringa di 5 cifre (`"1"` = alzato, `"0"` = abbassato) e lo invia via Bluetooth all'ESP32 (e allo stesso modo al webhook, se configurato).

```python
payload = {
    "rps_label": rps_label,
    "fingers_count": fingers_count,
    "fingers_pattern": fingers_pattern,  # ordine: Pollice, Indice, Medio, Anulare, Mignolo
    "ts": time.time(),
}
```

Esempio di messaggio (solo indice e medio alzati):
```json
{
  "rps_label": "FORBICI",
  "fingers_count": 2,
  "fingers_pattern": "01100",
  "ts": 1763211234.567
}
```

| Campo | Tipo | Descrizione |
|---|---|---|
| `rps_label` | stringa o `null` | `"SASSO"`, `"CARTA"`, `"FORBICI"` oppure `null` se il pattern non è uno dei tre |
| `fingers_count` | intero | dita alzate, da `0` a `5` |
| `fingers_pattern` | stringa | 5 cifre `0`/`1`, ordine Pollice, Indice, Medio, Anulare, Mignolo |
| `ts` | numero | timestamp Unix in secondi (con decimali) |

L'ESP32 riceve il messaggio e lo interpreta per eseguire le azioni corrispondenti.

---

# RISOLUZIONE DEI PROBLEMI

| Problema | Possibile causa / soluzione |
|---|---|
| `ModuleNotFoundError: No module named 'bleak'` (o `requests`) | Non hai eseguito il passo 5: `venv\Scripts\python.exe -m pip install bleak requests` |
| `'python' non è riconosciuto…` | Python non è nel PATH: reinstallalo spuntando "Add python.exe to PATH" oppure prova `py` al posto di `python` |
| `Impossibile aprire la webcam (indice 0)` | La webcam è occupata da un'altra app o non è la periferica `0`: chiudi le altre app o cambia l'indice in `cv2.VideoCapture(0)` |
| Download del modello fallito | Scarica il file manualmente (vedi [Modello](#modello)) e mettilo accanto a `core.py` |
| `[api] BLE: invio fallito` | Controlla indirizzo e UUID in `api.py`, che l'ESP32 sia acceso e vicino, che il Bluetooth del PC sia attivo e che l'ESP32 non sia già connesso ad un altro dispositivo |
| Le dita vengono riconosciute male | Regola `FINGER_CLOSE_RATIO` / `THUMB_CLOSE_RATIO` (vedi [Come funziona il riconoscimento delle dita](#come-funziona-il-riconoscimento-delle-dita)) e migliora luce e sfondo |

---

# LICENZA E CREDITI

Il codice è distribuito con licenza **AGPL-3.0** (come indicato nell'intestazione dei file sorgente).

**Author:** *Giulio Segre*

[*www.giulio-virtual-world.com*](https://www.giulio-virtual-world.com)

**Last modified date:** *15-11-2026*
