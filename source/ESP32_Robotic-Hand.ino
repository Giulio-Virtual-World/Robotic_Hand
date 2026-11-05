#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// --- Deve corrispondere a quanto usato in api.py ---------------------------
#define SERVICE_UUID        "0000ffe0-0000-1000-8000-00805f9b34fb" // A scelta
#define CHARACTERISTIC_UUID "0000ffe1-0000-1000-8000-00805f9b34fb" // UUID per il collegamento al pc
// -----------------------------------------------------------------------

int patternVector[5] = {1, 1, 1, 1, 1}; // vettore dita
int previusPatternVector[5] =  {1, 1, 1, 1, 1};

// Pin Ponti H (motori a,b,c,d,e)
const int a1 = 15;
const int a2 = 2;
const int b1 = 0;
const int b2 = 4;
const int c1 = 16;
const int c2 = 17;
const int d1 = 5;
const int d2 = 18;
const int e1 = 19;
const int e2 = 21;

// Config
const int contractionTimes[5]   = {700, 750, 750, 800, 1000}; // Quanto tempo ci mettono le dita per decontrarsi [ms] - (Pollice, Indice, Medio, Anulare, Mignolo)
const int decontractionTimes[5] = {500, 550, 550, 570, 700}; // Quanto tempo ci mettono le dita per contrarsi [ms] - (Pollice, Indice, Medio, Anulare, Mignolo)


BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// --- Stato condiviso tra onWrite() (arriva su un callback BLE) e loop() ----
// fingers_pattern e' una stringa di 5 cifre "1"/"0" nell'ordine
// [Pollice, Indice, Medio, Anulare, Mignolo], come prodotta da api.py
volatile bool newPatternAvailable = false;
String currentFingersPattern = "11111"; // Normalmente alzate

// --- Estrae il valore di una chiave stringa da un JSON "piatto" tipo -------
// {"rps_label": "...", "fingers_count": 3, "fingers_pattern": "01100", "ts": ...}
// Parser minimale scritto a mano per non aggiungere dipendenze (niente
// ArduinoJson): cerca "chiave":" e legge fino alla " di chiusura successiva.
String extractJsonStringValue(const String &json, const String &key) {
  String needle = "\"" + key + "\"";
  int keyIdx = json.indexOf(needle);
  if (keyIdx == -1) return "";

  int colonIdx = json.indexOf(':', keyIdx + needle.length());
  if (colonIdx == -1) return "";

  int quoteStart = json.indexOf('"', colonIdx + 1);
  if (quoteStart == -1) return "";

  int quoteEnd = json.indexOf('"', quoteStart + 1);
  if (quoteEnd == -1) return "";

  return json.substring(quoteStart + 1, quoteEnd);
}

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
    Serial.println("[BLE] Client connesso");
  }
  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    Serial.println("[BLE] Client disconnesso, riavvio advertising...");
    BLEDevice::startAdvertising();
  }
};

class CharCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pChar) override {
    String value = pChar->getValue().c_str();
    if (value.length() > 0) {
      Serial.println("[BLE] Messaggio ricevuto:");
      Serial.println(value);   // stampa il JSON grezzo, es: {"rps_label": "...", "fingers_count": 3, "ts": ...}

      String pattern = extractJsonStringValue(value, "fingers_pattern");
      if (pattern.length() == 5) {
        currentFingersPattern = pattern;
        newPatternAvailable = true;   // segnala al loop() che c'e' un nuovo pattern da gestire
      } else {
        Serial.println("[BLE] Attenzione: fingers_pattern assente o malformato nel JSON");
      }
    }
  }
};

void contractFinger(int i) {
  switch(i) {
    case 4:
      Serial.println("Contrazione Mignolo");
      digitalWrite(a1, LOW);
      break;
    case 3:
      Serial.println("Contrazione Anulare");
      digitalWrite(b1, LOW);
      break;
    case 2:
      Serial.println("Contrazione Medio");
      digitalWrite(c1, LOW);
      break;
    case 1:
      Serial.println("Contrazione Indice");
      digitalWrite(d1, LOW);
      break;
    case 0:
      Serial.println("Contrazione Pollice");
      digitalWrite(e1, LOW);
      break;

    default: Serial.println("Errore Contrazione: dito " + String(i) + " non valido");
  }
}
void decontractFinger(int i) {
  switch(i) {
    case 4:
      Serial.println("Decontrazione Mignolo");
      digitalWrite(a2, LOW);
      break;
    case 3:
      Serial.println("Decontrazione Anulare");
      digitalWrite(b2, LOW);
      break;
    case 2:
      Serial.println("Decontrazione Medio");
      digitalWrite(c2, LOW);
      break;
    case 1:
      Serial.println("Decontrazione Indice");
      digitalWrite(d2, LOW);
      break;
    case 0:
      Serial.println("Decontrazione Pollice");
      digitalWrite(e2, LOW);
      break;

    default: Serial.println("Errore Decontrazione: dito " + String(i) + " non valido");
  }
}

void stopAllFingers() { // Spegni i ponti H (si attivano con ingresso a massa)
  digitalWrite(a1, HIGH);
  digitalWrite(a2, HIGH);
  digitalWrite(b1, HIGH);
  digitalWrite(b2, HIGH);
  digitalWrite(c1, HIGH);
  digitalWrite(c2, HIGH);
  digitalWrite(d1, HIGH);
  digitalWrite(d2, HIGH);
  digitalWrite(e1, HIGH);
  digitalWrite(e2, HIGH);
}

void stopSingleFinger(int i) { // Spegne i due pin di un singolo dito
  switch(i) {
    case 4:
      digitalWrite(a1, HIGH);
      digitalWrite(a2, HIGH);
      break;
    case 3:
      digitalWrite(b1, HIGH);
      digitalWrite(b2, HIGH);
      break;
    case 2:
      digitalWrite(c1, HIGH);
      digitalWrite(c2, HIGH);
      break;
    case 1: 
      digitalWrite(d1, HIGH);
      digitalWrite(d2, HIGH);
      break;
    case 0:
      digitalWrite(e1, HIGH);
      digitalWrite(e2, HIGH);
      break;

    default: Serial.println("Errore nel fermare il dito: Dito " + String(i) + " non valido");
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Avvio BLE server ESP32...");

  BLEDevice::init("ESP32-RoboticHand");   // Nome del dispositivo bluetooth
  Serial.println(BLEDevice::getAddress().toString().c_str()); // Mostra l'indirizzo Mac in console
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic( // Crea la caratteristica per il collegamento al pc
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ   |
      BLECharacteristic::PROPERTY_WRITE  |
      BLECharacteristic::PROPERTY_NOTIFY
  );
  pCharacteristic->setCallbacks(new CharCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());

  pService->start(); // Avvia il servizio BLE

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.println("In attesa di connessioni BLE...");

  // Definisci e spegni i ponti H
  pinMode(a1, OUTPUT);
  pinMode(a2, OUTPUT);
  pinMode(b1, OUTPUT);
  pinMode(b2, OUTPUT);
  pinMode(c1, OUTPUT);
  pinMode(c2, OUTPUT);
  pinMode(d1, OUTPUT);
  pinMode(d2, OUTPUT);
  pinMode(e1, OUTPUT);
  pinMode(e2, OUTPUT);
  stopAllFingers();
}

void loop() {
  // Elabora il pattern SOLO quando ne arriva uno nuovo via BLE
  // (per non rifare la stessa azione ogni secondo a vuoto).
  if (newPatternAvailable) {
    newPatternAvailable = false;

    String pattern = currentFingersPattern; // ordine: Pollice,Indice,Medio,Anulare,Mignolo
    unsigned long durations[5] = {0, 0, 0, 0, 0}; // 0 = dito fermo

    // Avvia i movimenti e memorizza la durata di ciascun dito
    for(int i=0; i<5; i++) {
      patternVector[i] = (pattern[i] == '1') ? 1 : 0; // Converte il carattere ASCII in un vettore con numeri interi 0 oppure 1

      if (patternVector[i] != previusPatternVector[i]) { // se lo stato del dito e' cambiato
        if (patternVector[i]) {
          decontractFinger(i);
          durations[i] = decontractionTimes[i];
        } else {
          contractFinger(i);
          durations[i] = contractionTimes[i];
        }
        previusPatternVector[i] = patternVector[i]; // aggiorna lo stato precedente
      }
    }

    // Spegne ogni dito quando scade il suo tempo
    // Salva l'istante in cui sono partiti i motori. Tutti i tempi verranno misurati rispetto a questo momento.
    unsigned long startTime = millis();

    // Flag che tiene vivo il ciclo finché almeno un dito è ancora in movimento.
    bool anyActive = true;

    while (anyActive) {
      // Se tutti i diti hanno finito, ma trova un dito ancora attivo più sotto, lo rimette a true.
      anyActive = false;

      // Tempo trascorso da quando i motori sono partiti [ms].
      // La sottrazione è sicura anche se millis() va in overflow (~49 giorni), perché si usano unsigned long.
      unsigned long elapsed = millis() - startTime;

      // Controlla ogni dito, uno per uno
      for (int i = 0; i < 5; i++) {

        // durations[i] > 0 significa che il dito si sta muovendo.
        // 0 vale sia per le dita che non dovevano muoversi sia per quelle già fermate in un giro precedente del while, quindi vengono saltate.
        if (durations[i] > 0) {
          if (elapsed >= durations[i]) {
            stopSingleFinger(i); // Il tempo di questo dito è scaduto: spegni i suoi due pin del ponte H.            
            durations[i] = 0; // Azzera la durata: marca il dito come "già fermato", così nei giri successivi non viene spento di nuovo.
          } else {
            anyActive = true; // Il tempo non è ancora scaduto: il motore deve restare acceso.
          }
        }
      }
      delay(1); // Pausa di 1 ms tra un controllo e l'altro. Evita di occupare la CPU 100%.
    }
  }
}
