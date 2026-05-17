#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <time.h>

// ---------------- WIFI ----------------
const char* ssid = "Marina";
const char* password = "miisa395am";

// ---------------- MQTT ----------------
const char* mqtt_server = "192.168.1.6";

WiFiClient espClient;
PubSubClient client(espClient);

// ---------------- SENSORES ----------------
#define LUZ_PIN 4
#define DHTPIN 15
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);

// ---------------- BUFFER (RAM) ----------------
String buffer[50];
int bufferIndex = 0;

// ---------------- WIFI ----------------
void conectarWiFi() {

  WiFi.begin(ssid, password);

  Serial.print("📡 Conectando WiFi");

  int intentos = 0;

  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    Serial.print(".");
    intentos++;
  }

  if (WiFi.status() == WL_CONNECTED) {

    Serial.println("\n✅ WiFi conectado");

    Serial.print("🌐 IP ESP32: ");
    Serial.println(WiFi.localIP());

  } else {

    Serial.println("\n❌ Fallo WiFi");
  }
}

// ---------------- MQTT ----------------
void conectarMQTT() {

  while (!client.connected()) {

    Serial.print("📡 Conectando MQTT...");

    if (client.connect("ESP32_DHT22")) {

      Serial.println("✅ MQTT conectado");

    } else {

      Serial.print("❌ fallo rc=");
      Serial.println(client.state());

      delay(2000);
    }
  }
}

// ---------------- NTP ----------------
String getTime() {

  struct tm timeinfo;

  if (!getLocalTime(&timeinfo)) {
    return "no_time";
  }

  char bufferTime[30];

  strftime(bufferTime, sizeof(bufferTime),
           "%Y-%m-%d %H:%M:%S", &timeinfo);

  return String(bufferTime);
}

// ---------------- MQTT SEND ----------------
bool enviarMQTT(String json) {

  bool ok = client.publish(
    "iot/esp32/datos",
    json.c_str()
  );

  return ok;
}

// ---------------- SETUP ----------------
void setup() {

  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);

  delay(1000);

  pinMode(LUZ_PIN, INPUT_PULLUP);

  dht.begin();

  conectarWiFi();

  client.setServer(mqtt_server, 1883);

  configTime(0, 0, "pool.ntp.org");

  Serial.println("🕒 NTP sincronizado");
}

// ---------------- LOOP ----------------
void loop() {

  // ---------------- WIFI CHECK ----------------
  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("⚠️ WiFi caído");

    conectarWiFi();
  }

  // ---------------- MQTT CHECK ----------------
  if (!client.connected()) {

    conectarMQTT();
  }

  client.loop();

  // ---------------- SENSORES ----------------
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  int luz = digitalRead(LUZ_PIN);

  if (isnan(h) || isnan(t)) {

    Serial.println("⚠️ Error DHT22");

    delay(2000);

    return;
  }

  // ---------------- JSON ----------------
  String json = "{";

  json += "\"timestamp\":\"" + getTime() + "\",";
  json += "\"temperatura\":" + String(t) + ",";
  json += "\"humedad\":" + String(h) + ",";
  json += "\"luz\":" + String(luz == LOW ? "true" : "false");

  json += "}";

  Serial.println("----------------------");
  Serial.println(json);

  // ---------------- ENVÍO MQTT ----------------
  if (enviarMQTT(json)) {

    Serial.println("📡 MQTT enviado OK");

    // ---------------- VACIAR BUFFER ----------------
    if (bufferIndex > 0) {

      Serial.println("📤 Enviando buffer...");

      for (int i = 0; i < bufferIndex; i++) {

        enviarMQTT(buffer[i]);

        delay(300);
      }

      bufferIndex = 0;

      Serial.println("✅ Buffer vacío");
    }

  } else {

    Serial.println("💾 Guardado en buffer");

    if (bufferIndex < 50) {

      buffer[bufferIndex++] = json;

    } else {

      Serial.println("⚠️ Buffer lleno");

      bufferIndex = 0;
    }
  }

  delay(5000);
}