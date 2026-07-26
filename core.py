"""

Author: Giulio Segre
Last modified date: 26-07-2026
www.giulio-virtual-world.com


=========================================================================================
 SASSO - CARTA - FORBICI  +  CONTEGGIO DITA IN TEMPO REALE
 Basato su MediaPipe Tasks - GestureRecognizer (modalita' LIVE_STREAM)
=========================================================================================

COSA FA QUESTO SCRIPT
----------------------
1. Apre la webcam e processa il flusso video in tempo reale usando la modalita'
   LIVE_STREAM del GestureRecognizer di MediaPipe (asincrona, con callback).
2. Riconosce i gesti "canned" (predefiniti) del modello:
   Closed_Fist, Open_Palm, Victory, Thumb_Up, Thumb_Down, Pointing_Up, ILoveYou, None.
3. In parallelo, calcola in modo indipendente (dai 21 landmark della mano) quante e
   quali dita sono alzate, e le mostra in una interfaccia grafica overlay su OpenCV.
   
   Mostra inoltre il gesto che si sta facendo per il gioco: "sasso carta forbici":
   
       Vecchia logica:
           Closed_Fist  -> SASSO
           Open_Palm    -> CARTA
           Victory      -> FORBICI

       Nuova logica:
          0 dita alzate   -> SASSO
          5 dita alzate   -> CARTA
          indice+medio    -> FORBICI


PERCHE' LIVE_STREAM E NON IMAGE/VIDEO
--------------------------------------
- IMAGE  : per una singola immagine statica (foto).
- VIDEO  : per un file video gia' registrato, elaborato in modo sincrono
           frame per frame con recognize_for_video().
- LIVE_STREAM: pensata apposta per input continuo in tempo reale (webcam).
  E' ASINCRONA: si invia un frame con recognize_async(image, timestamp_ms) e il
  risultato arriva DOPO, tramite una funzione di callback (result_callback) passata
  in fase di creazione delle opzioni. Il timestamp deve essere monotono crescente,
  altrimenti MediaPipe scarta il frame.

INSTALLAZIONE
--------------
    pip install mediapipe opencv-python

MODELLO
-------
Il task richiede un modello .task pre-addestrato (non e' incluso nel pacchetto pip).
Lo script lo scarica automaticamente al primo avvio nella cartella corrente.
Se preferisci scaricarlo manualmente:
    https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task

AVVIO
-----
    python core.py

COMANDI A RUNTIME
------------------
    q  -> esci
    m  -> mostra/nascondi i 21 landmark della mano
=========================================================================================
"""

import os
import time
import urllib.request
from collections import deque

import cv2
import numpy as np
import mediapipe as mp

# ----------------------------------------------------------------------------------------
# ALIAS ALLE CLASSI MEDIAPIPE (come da documentazione ufficiale)
# ----------------------------------------------------------------------------------------
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
VisionRunningMode = mp.tasks.vision.RunningMode
HandLandmarksConnections = mp.tasks.vision.HandLandmarksConnections

# ----------------------------------------------------------------------------------------
# CONFIGURAZIONE
# ----------------------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesture_recognizer.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)

# Indici dei landmark della mano (schema standard MediaPipe Hands, 21 punti)
WRIST = 0
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 3, 2
INDEX_TIP, INDEX_PIP, INDEX_MCP = 8, 6, 5
MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP = 12, 10, 9
RING_TIP, RING_PIP, RING_MCP = 16, 14, 13
PINKY_TIP, PINKY_PIP, PINKY_MCP = 20, 18, 17

FINGER_NAMES = ["Pollice", "Indice", "Medio", "Anulare", "Mignolo"]


# ----------------------------------------------------------------------------------------
# UTILITY: scarica il modello se non presente
# ----------------------------------------------------------------------------------------
def download_model_if_needed(path: str, url: str) -> None:
    if os.path.exists(path):
        return
    print(f"[INFO] Modello non trovato, scarico da:\n  {url}")
    try:
        urllib.request.urlretrieve(url, path)
        print(f"[INFO] Modello salvato in: {path}")
    except Exception as e:
        raise RuntimeError(
            "Impossibile scaricare automaticamente il modello. "
            f"Scaricalo manualmente da {url} e posizionalo in {path}.\n"
            f"Errore originale: {e}"
        )


# ----------------------------------------------------------------------------------------
# CONTEGGIO DITA A PARTIRE DAI LANDMARK
# ----------------------------------------------------------------------------------------
def _dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def count_fingers(hand_landmarks, handedness_label: str):
    """
    Restituisce (numero_dita_alzate, lista_booleana_per_dito[Pollice,Indice,Medio,Anulare,Mignolo])

    Logica:
    - Per le 4 dita lunghe (indice, medio, anulare, mignolo): un dito e' considerato
      "alzato" se la punta (TIP) e' sopra (coordinata y minore, in un sistema immagine
      con origine in alto a sinistra) l'articolazione PIP.
    - Per il pollice si usa un criterio GEOMETRICO basato sulle distanze interne alla
      mano, invece che sulla posizione assoluta x: il pollice e' considerato "disteso"
      se la sua punta (TIP) e' piu' lontana dalla base del mignolo (landmark 17) di
      quanto lo sia l'articolazione MCP del pollice stesso. Quando il pollice si piega
      verso il palmo, la punta si avvicina a quella zona; quando e' disteso, se ne
      allontana. Questo approccio funziona indipendentemente dal fatto che la mano sia
      destra o sinistra e indipendentemente da eventuali flip/specchiature dell'immagine
      (a differenza del confronto sulla sola coordinata x, che dipende da convenzioni
      di mirroring facili da invertire per errore).
    """
    lm = hand_landmarks  # lista di 21 landmark normalizzati (x, y, z) in [0, 1]

    fingers_up = [False, False, False, False, False]

    # --- Pollice (criterio a distanza, robusto e indipendente dalla mano/flip) ---
    dist_tip = _dist(lm[THUMB_TIP], lm[PINKY_MCP])
    dist_mcp = _dist(lm[THUMB_MCP], lm[PINKY_MCP])
    fingers_up[0] = dist_tip > dist_mcp * 1.1  # margine 10% per evitare falsi positivi

    # --- Indice, Medio, Anulare, Mignolo ---
    tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    pips = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
    for i, (tip, pip) in enumerate(zip(tips, pips), start=1):
        fingers_up[i] = lm[tip].y < lm[pip].y

    return sum(fingers_up), fingers_up


def classify_rps(fingers_up):
    """
    Classifica il gesto Sasso/Carta/Forbici a partire dal pattern delle 5 dita
    (Pollice, Indice, Medio, Anulare, Mignolo), invece di usare i gesti "canned"
    del modello MediaPipe (piu' rigidi e non sempre affidabili per questo scopo).

    Regole:
        SASSO    -> nessun dito alzato (pugno chiuso)
        CARTA    -> tutte e 5 le dita alzate (mano aperta)
        FORBICI  -> solo indice e medio alzati (anulare e mignolo abbassati;
                    il pollice puo' essere alzato o meno, non e' vincolante)

    Restituisce "SASSO", "CARTA", "FORBICI" oppure None se il pattern non
    corrisponde a nessuno dei tre gesti del gioco.
    """
    thumb, index, middle, ring, pinky = fingers_up

    if not any(fingers_up):
        return "SASSO"

    if all(fingers_up):
        return "CARTA"

    if index and middle and not ring and not pinky:
        return "FORBICI"

    return None


# ----------------------------------------------------------------------------------------
# GESTIONE ASINCRONA DEL RISULTATO (LIVE_STREAM)
# ----------------------------------------------------------------------------------------
class LatestResult:
    """Contenitore thread-safe minimale per l'ultimo risultato ricevuto dalla callback.
    La callback di LIVE_STREAM viene eseguita su un thread interno di MediaPipe,
    quindi NON va bloccata con logica pesante: si limita a salvare il risultato."""

    def __init__(self):
        self.result = None
        self.timestamp_ms = 0

    def update(self, result, output_image, timestamp_ms):
        self.result = result
        self.timestamp_ms = timestamp_ms


latest = LatestResult()


def on_result(result: GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
    latest.update(result, output_image, timestamp_ms)


# ----------------------------------------------------------------------------------------
# DISEGNO INTERFACCIA GRAFICA (overlay OpenCV)
# ----------------------------------------------------------------------------------------
def draw_landmarks(frame, hand_landmarks_px, connections):
    for connection in connections:
        start_idx, end_idx = connection.start, connection.end
        x1, y1 = hand_landmarks_px[start_idx]
        x2, y2 = hand_landmarks_px[end_idx]
        cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
    for (x, y) in hand_landmarks_px:
        cv2.circle(frame, (x, y), 4, (0, 120, 255), -1)


def draw_ui(frame, rps_label, canned_gesture_label, canned_gesture_score, fingers_count, fingers_up, fps):
    h, w, _ = frame.shape

    # Pannello semi-trasparente in alto (piu' alto per ospitare 4 righe distinte
    # senza sovrapposizioni, indipendentemente dalla risoluzione della webcam)
    PANEL_H = 160
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, PANEL_H), (30, 30, 30), -1)
    frame[:] = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    # --- Riga 1: Sasso/Carta/Forbici, dedotto dal pattern delle dita alzate ---
    if rps_label is not None:
        text = rps_label
        color = (0, 255, 0)
    elif fingers_up and any(fingers_up):
        text = "Nessuna delle 3 pose (S/C/F)"
        color = (0, 200, 255)
    else:
        text = "Nessuna mano rilevata"
        color = (0, 0, 255)

    cv2.putText(frame, text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)

    # --- Riga 2: gesto "canned" di MediaPipe, mostrato solo come riferimento informativo ---
    if canned_gesture_label is not None:
        ref_text = f"(gesto rilevato dal modello: {canned_gesture_label}, {canned_gesture_score:.0%})"
    else:
        ref_text = "(gesto rilevato dal modello: -)"
    cv2.putText(frame, ref_text, (15, 58), cv2.FONT_HERSHEY_SIMPLEX,
                0.45, (180, 180, 180), 1, cv2.LINE_AA)

    # --- Riga 3: conteggio dita (a sinistra) + FPS (a destra) ---
    cv2.putText(frame, f"Dita alzate: {fingers_count}", (15, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 130, 90), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 2, cv2.LINE_AA)

    # --- Riga 4: 5 indicatori delle dita, distribuiti sull'intera larghezza del frame ---
    # Il posizionamento e' calcolato dinamicamente in base alla larghezza reale (w),
    # cosi' tutti e 5 gli indicatori (incluso il mignolo) restano sempre visibili
    # qualunque sia la risoluzione della webcam, invece di usare offset fissi che su
    # risoluzioni strette (es. 640px) tagliavano fuori le ultime dita.
    margin = 25
    n = len(FINGER_NAMES)
    spacing = (w - 2 * margin) / n
    x0 = margin + spacing / 2
    row_y = 125

    for i, name in enumerate(FINGER_NAMES):
        up = fingers_up[i] if fingers_up else False
        color_dot = (0, 255, 0) if up else (80, 80, 80)
        cx = int(x0 + i * spacing)
        cv2.circle(frame, (cx, row_y), 10, color_dot, -1)
        label = name[:3]
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
        cv2.putText(frame, label, (cx - text_size[0] // 2, row_y + 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (255, 255, 255), 1, cv2.LINE_AA)

    # Istruzioni
    cv2.putText(frame, "q: esci   m: mostra/nascondi landmark", (15, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    # Firma in basso a destra (la larghezza del testo viene calcolata per allinearla
    # sempre al margine destro, qualunque sia la risoluzione del frame)
    signature = "By: Giulio Segre"
    sig_size = cv2.getTextSize(signature, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    sig_x = w - sig_size[0] - 15
    cv2.putText(frame, signature, (sig_x, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)


# ----------------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------------
def main():
    download_model_if_needed(MODEL_PATH, MODEL_URL)

    options = GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.LIVE_STREAM,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        result_callback=on_result,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Impossibile aprire la webcam (indice 0). Controlla la periferica.")

    show_landmarks = True
    fps_window = deque(maxlen=30)
    prev_time = time.time()

    # start_time serve per generare timestamp monotoni in millisecondi,
    # richiesti da recognize_async in modalita' LIVE_STREAM.
    start_time = time.time()

    with GestureRecognizer.create_from_options(options) as recognizer:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[WARN] Frame non letto dalla webcam, esco.")
                break

            # Effetto specchio (piu' naturale per l'utente davanti alla webcam)
            frame = cv2.flip(frame, 1)

            # Conversione BGR (OpenCV) -> RGB (MediaPipe) e creazione mp.Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            timestamp_ms = int((time.time() - start_time) * 1000)
            recognizer.recognize_async(mp_image, timestamp_ms)

            # --- Lettura dell'ultimo risultato disponibile (asincrono) ---
            canned_gesture_label = None
            canned_gesture_score = 0.0
            fingers_count = 0
            fingers_up = [False] * 5
            rps_label = None

            result = latest.result
            if result is not None and result.hand_landmarks:
                hand_landmarks = result.hand_landmarks[0]  # prima (unica) mano, num_hands=1
                handedness_label = result.handedness[0][0].category_name if result.handedness else "Right"

                # Gesto "canned" del modello (Closed_Fist, Open_Palm, Victory, ...):
                # mostrato solo come riferimento informativo in UI, NON usato per
                # decidere Sasso/Carta/Forbici (vedi sotto).
                if result.gestures and len(result.gestures[0]) > 0:
                    top_gesture = result.gestures[0][0]
                    canned_gesture_label = top_gesture.category_name
                    canned_gesture_score = top_gesture.score

                # Conteggio dita: fonte di verita' indipendente dal classificatore di gesti
                fingers_count, fingers_up = count_fingers(hand_landmarks, handedness_label)

                # Sasso/Carta/Forbici dedotto DIRETTAMENTE dal pattern delle dita alzate
                # (es. solo indice+medio alzati -> FORBICI), come richiesto.
                rps_label = classify_rps(fingers_up)

                # Disegno landmark (opzionale)
                if show_landmarks:
                    h, w, _ = frame.shape
                    px_landmarks = [(int(p.x * w), int(p.y * h)) for p in hand_landmarks]
                    draw_landmarks(frame, px_landmarks, HandLandmarksConnections.HAND_CONNECTIONS)

            # --- FPS ---
            now = time.time()
            fps_window.append(1.0 / max(now - prev_time, 1e-6))
            prev_time = now
            fps = sum(fps_window) / len(fps_window)

            draw_ui(frame, rps_label, canned_gesture_label, canned_gesture_score,
                    fingers_count, fingers_up, fps)

            cv2.imshow("Sasso Carta Forbici - MediaPipe GestureRecognizer", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("m"):
                show_landmarks = not show_landmarks

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
