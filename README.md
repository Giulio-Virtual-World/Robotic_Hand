# COSA FA QUESTO SCRIPT

1. Apre la webcam e processa il flusso video in tempo reale usando la modalita' `LIVE_STREAM` del GestureRecognizer di **MediaPipe** (asincrona, con callback).

2. Riconosce i gesti "canned" (predefiniti) del modello: `Closed_Fist`, `Open_Palm`, `Victory`, `Thumb_Up`, `Thumb_Down`, `Pointing_Up`, `ILoveYou`, `None`.

3. In parallelo, calcola in modo indipendente (dai 21 landmark della mano) quante e quali dita sono alzate, e le mostra in una interfaccia grafica overlay su **OpenCV**.

Mostra inoltre il gesto che si sta facendo per il gioco: "sasso carta forbici":

### Vecchia logica:
>     Closed_Fist  -> SASSO
>     Open_Palm    -> CARTA
>     Victory      -> FORBICI

### Nuova logica:
>     0 dita alzate   -> SASSO
>     5 dita alzate   -> CARTA
>     Indice + Medio  -> FORBICI

## PERCHE' LIVE_STREAM E NON IMAGE/VIDEO
- **IMAGE:** per una singola immagine statica (foto).
- **VIDEO:** per un file video gia' registrato, elaborato in modo sincrono
    frame per frame con `recognize_for_video()`.
- **LIVE_STREAM:** pensata apposta per input continuo in tempo reale (webcam).
    E' ASINCRONA: si invia un frame con `recognize_async(image, timestamp_ms)` e il
    risultato arriva DOPO, tramite una funzione di callback (`result_callback`) passata
    in fase di creazione delle opzioni. Il timestamp deve essere monotono crescente,
    altrimenti MediaPipe scarta il frame.


# INSTALLAZIONE
**Per installare gli script, modello e librerie esegui il file [`source/installer.py`](./source/installer.py).**

Se il file non dovesse funzionare puoi installarli manualmente aprendo il terminale (`cmd`) ed eseguendo i seguenti comandi:

**Entra nella cartella del progetto:**
> `cd percorso/verso/la/cartella`

**Crea un ambiente virtuale (consigliato):**
> `python -m venv venv`

**Avvia l'ambiente virtuale:**
> `venv\Scripts\activate`

**Installa le librerie necessarie:**
> `pip install mediapipe opencv-python`

**Installa numpy (necessario per alcune operazioni):**
> `pip install numpy`

**Verifica l'installazione di mediapipe:**
> `pip show mediapipe`


# AVVIO
**Per avviare lo script esegui il file [`source/start.py`](./source/start.py).**

Se il file non dovesse funzionare puoi avviarlo manualmente aprendo il terminale nella cartella del progetto e digitando i seguenti comandi:

**Avvia l'ambiente virtuale (se lo hai creato precedentemente):**
> `venv\Scripts\activate`

**Esegui lo script:**
> `python core.py`


# MODELLO
Il task richiede un modello .task pre-addestrato (non e' incluso nel pacchetto pip).

Lo script `core.py` lo scarica automaticamente al primo avvio nella cartella corrente.

Se preferisci scaricarlo manualmente: https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task


# COMANDI A RUNTIME
`q`  -> esci

`m`  -> mostra/nascondi i 21 landmark della mano


# COME FUNZIONA IL RICONOSCIMENTO DELLE DITA
Il riconoscimento delle dita alzate avviene in modo indipendente dal modello di riconoscimento dei gesti e si basa sui 21 landmark della mano forniti da MediaPipe.

Il criterio è interamente **basato sulle distanze** tra i landmark: non dipende quindi dall'orientamento della mano né dal fatto che l'immagine sia specchiata.

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

**Per il pollice:** la sua punta (TIP) deve essere abbastanza vicina alla base (MCP) di **qualsiasi altro dito** (indice, medio, anulare o mignolo) per essere considerato abbassato. Se non è vicina a nessuna di queste basi, il pollice è alzato.
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
THUMB_CLOSE_RATIO = 0.45   # pollice: punta vs. base (MCP) di qualsiasi altro dito
```
> * Se un dito risulta abbassato quando in realtà è alzato, **abbassa** il valore della soglia.
> * Se un dito risulta alzato quando in realtà è piegato, **alza** il valore della soglia.

In questo modo, il riconoscimento delle dita non dipende direttamente dalle categorie di gesto ("Closed_Fist", "Open_Palm", "Victory", ecc.) fornite dal classificatore di MediaPipe, ma viene ricavato direttamente dalla geometria dei landmark della mano.


# JSON OUTPUT
Lo script invia tramite Bluetooth all'ESP32 le informazioni relative al riconoscimento della mano attraverso la funzione:
```python
api.send_command_to_esp32(rps_label, fingers_count, fingers_up)
```
La funzione riceve tre informazioni principali:
> * `rps_label`: il gesto riconosciuto tra `"SASSO"`, `"CARTA"`, `"FORBICI"` oppure `None`;
> * `fingers_count`: il numero totale di dita riconosciute come alzate, da `0` a `5`;
> * `fingers_up`: una lista di cinque valori booleani che indica, nell'ordine, quali dita sono alzate.

La lista `fingers_up` ha il seguente ordine:
```python
[Pollice, Indice, Medio, Anulare, Mignolo]
```
Ad esempio:
```python
fingers_up = [False, True, True, False, False]
```
indica che sono alzati solamente **indice e medio**, corrispondenti al gesto **FORBICI**.

Il numero di dita alzate viene ottenuto direttamente dalla lista:
```python
fingers_count = sum(fingers_up)
```

Il comando verso l'ESP32 viene inviato solamente quando il numero di dita riconosciute cambia rispetto al valore precedentemente inviato (per evitare di inviare continuamente lo stesso comando a ogni frame della webcam). Questo viene gestito con la seguente logica:

```python
ex_fingers_count = globals().get('ex_fingers_count', -1)

if fingers_count != ex_fingers_count:
    globals()['ex_fingers_count'] = fingers_count
    ex_fingers_count = fingers_count

    api.send_command_to_esp32(
        rps_label,
        fingers_count,
        fingers_up
    )
```

Il formato JSON del messaggio effettivamente trasmesso dipende dall'implementazione della funzione `send_command_to_esp32()` presente nel file [`api.py`](./source/api.py). Lo script principale, infatti, non costruisce direttamente il JSON: passa alla funzione i tre valori già elaborati:
```python
api.send_command_to_esp32(rps_label, fingers_count, fingers_up)
```

Infine, il file [`api.py`](./source/api.py) si occupa di costruire il seguente JSON e inviarlo tramite Bluetooth all'ESP32, che riceve il messaggio e lo interpreta per eseguire le azioni corrispondenti.
```python
payload = {
        "rps_label": rps_label,
        "fingers_count": fingers_count,
        "fingers_pattern": fingers_pattern,
        "ts": time.time(),
    }
```


# CREDITI
**Author:** *Giulio Segre*

[*www.giulio-virtual-world.com*](https://www.giulio-virtual-world.com)

**Last modified date:** *19-10-2026*
