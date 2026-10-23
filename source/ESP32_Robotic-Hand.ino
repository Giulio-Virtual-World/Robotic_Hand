#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// --- Deve corrispondere a quanto usato in api.py ---------------------------
#define SERVICE_UUID        "0000ffe0-0000-1000-8000-00805f9b34fb" // A scelta
#define CHARACTERISTIC_UUID "0000ffe1-0000-1000-8000-00805f9b34fb" // UUID per il collegamento al pc
// -----------------------------------------------------------------------

int patternVector[5]; // vettore dita
int previusPatternVector[5];

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

const int fingerContractionTime = 1000; // Quanto tempo ci mettono le dita per contrarsi [ms]


BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// --- Stato condiviso tra onWrite() (arriva su un callback BLE) e loop() ----
// fingers_pattern e' una stringa di 5 cifre "1"/"0" nell'ordine
// [Pollice, Indice, Medio, Anulare, Mignolo], come prodotta da api.py
volatile bool newPatternAvailable = false;
String currentFingersPattern = "00000";

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
    case 0:
      Serial.println("Contrazione Pollice");
      digitalWrite(a1, LOW);
      break;
    case 1:
      Serial.println("Contrazione Indice");
      digitalWrite(b1, LOW);
      break;
    case 2:
      Serial.println("Contrazione Medio");
      digitalWrite(c1, LOW);
      break;
    case 3:
      Serial.println("Contrazione Anulare");
      digitalWrite(d1, LOW);
      break;
    case 4:
      Serial.println("Contrazione Mignolo");
      digitalWrite(e1, LOW);
      break;

    default: Serial.println("Errore Contrazione: dito " + String(i) + " non valido");
  }
}
void decontractFinger(int i) {
  switch(i) {
    case 0:
      Serial.println("Decontrazione Pollice");
      digitalWrite(a2, LOW);
      break;
    case 1:
      Serial.println("Decontrazione Indice");
      digitalWrite(b2, LOW);
      break;
    case 2:
      Serial.println("Decontrazione Medio");
      digitalWrite(c2, LOW);
      break;
    case 3:
      Serial.println("Decontrazione Anulare");
      digitalWrite(d2, LOW);
      break;
    case 4:
      Serial.println("Decontrazione Mignolo");
      digitalWrite(e2, LOW);
      break;

    default: Serial.println("Errore Decontrazione: dito " + String(i) + " non valido");
  }
}

void stopFinger() { // Spegni i ponti H (si attivano con ingresso a massa)
  delay(fingerContractionTime);
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
  stopFinger();
}

void loop() {
  // Elabora il pattern SOLO quando ne arriva uno nuovo via BLE
  // (per non rifare la stessa azione ogni secondo a vuoto).
  if (newPatternAvailable) {
    newPatternAvailable = false;

    String pattern = currentFingersPattern; // ordine: Pollice,Indice,Medio,Anulare,Mignolo

    for(int i=0; i<5; i++) {
      patternVector[i] = (pattern[i] == '1') ? 1 : 0; // Converte il carattere ASCII in un vettore con numeri interi 0 oppure 1

      if (patternVector[i] != previusPatternVector[i] && i<5) { // se lo stato del dito e' cambiato
        patternVector[i] ? decontractFinger(i) : contractFinger(i);
        previusPatternVector[i] = patternVector[i]; // aggiorna lo stato precedente
      }
    }
    stopFinger(); // Ferma tutti i movimenti dei diti
  }
}
