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
Apri il terminale (`cmd`) ed esegui i seguenti comandi:

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
**Per avviare lo script esegui il file [`start.py`](./start.py).**

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


# CREDITI
**Author:** *Giulio Segre*

[*www.giulio-virtual-world.com*](https://www.giulio-virtual-world.com)

**Last modified date:** *26-07-2026*