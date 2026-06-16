#include <Arduino.h>
#include <DHTesp.h>
#include <HTTPClient.h>
#include <WiFi.h>

// Para demo com rede, troque SEND_HTTP para true. A API ja esta publica no Cloud Run.
// No Wokwi web, localhost aponta para o simulador, nao para a maquina local.
// Obs.: endpoint e HTTPS; em ESP32 pode exigir WiFiClientSecure/setInsecure.
static const bool SEND_HTTP = false;
static const char *API_URL = "https://sentinela-api-520322249774.us-central1.run.app/analyze";

static const char *WIFI_SSID = "Wokwi-GUEST";
static const char *WIFI_PASSWORD = "";

static const int DHT_PIN = 15;
static const int SMOKE_PIN = 34;
static const int LED_PIN = 2;
static const int BUZZER_PIN = 18;

static const char *DEVICE_ID = "esp32-wokwi-001";
static const char *IMAGE_URI = "amazon-fire-001.jpg";

DHTesp dht;

String isoDemoTime(unsigned long elapsedMs) {
  unsigned long seconds = elapsedMs / 1000;
  char buffer[25];
  snprintf(buffer, sizeof(buffer), "2026-06-16T12:%02lu:%02luZ", (seconds / 60) % 60, seconds % 60);
  return String(buffer);
}

float readSmokePpm() {
  int raw = analogRead(SMOKE_PIN);
  return map(raw, 0, 4095, 80, 950);
}

float fallbackTemperature() {
  return 32.0 + 10.0 * sin(millis() / 15000.0);
}

float fallbackHumidity() {
  return 45.0 - 12.0 * sin(millis() / 18000.0);
}

String riskLabel(float smokePpm, float temperatureC) {
  if (smokePpm >= 800 || temperatureC >= 50) {
    return "critical";
  }
  if (smokePpm >= 400 || temperatureC >= 38) {
    return "high";
  }
  if (smokePpm >= 150 || temperatureC >= 32) {
    return "moderate";
  }
  return "low";
}

void updateActuators(const String &level) {
  bool alert = level == "high" || level == "critical";
  digitalWrite(LED_PIN, alert ? HIGH : LOW);

  if (level == "critical") {
    tone(BUZZER_PIN, 1800, 160);
  } else if (level == "high") {
    tone(BUZZER_PIN, 1200, 80);
  } else {
    noTone(BUZZER_PIN);
  }
}

String buildPayload(float smokePpm, float temperatureC, float humidityPct) {
  String payload;
  payload.reserve(520);
  payload += "{";
  payload += "\"request_id\":\"wokwi-demo-001\",";
  payload += "\"image\":{";
  payload += "\"source_type\":\"sample\",";
  payload += "\"uri\":\"";
  payload += IMAGE_URI;
  payload += "\",";
  payload += "\"captured_at\":\"2026-06-16T12:00:00Z\"";
  payload += "},";
  payload += "\"sensor\":{";
  payload += "\"device_id\":\"";
  payload += DEVICE_ID;
  payload += "\",";
  payload += "\"smoke_ppm\":";
  payload += String(smokePpm, 1);
  payload += ",";
  payload += "\"temperature_c\":";
  payload += String(temperatureC, 1);
  payload += ",";
  payload += "\"humidity_pct\":";
  payload += String(humidityPct, 1);
  payload += ",";
  payload += "\"battery_pct\":87,";
  payload += "\"latitude\":-3.4653,";
  payload += "\"longitude\":-62.2159,";
  payload += "\"measured_at\":\"";
  payload += isoDemoTime(millis());
  payload += "\"";
  payload += "}";
  payload += "}";
  return payload;
}

void connectWifi() {
  if (!SEND_HTTP) {
    return;
  }

  Serial.print("Conectando WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(250);
    Serial.print(".");
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi indisponivel; mantendo demo pelo Serial.");
  }
}

void postPayload(const String &payload) {
  if (!SEND_HTTP || WiFi.status() != WL_CONNECTED) {
    return;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  int status = http.POST(payload);
  Serial.print("HTTP status: ");
  Serial.println(status);
  if (status > 0) {
    Serial.println(http.getString());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  dht.setup(DHT_PIN, DHTesp::DHT22);

  Serial.println("Sentinela Orbital - ESP32 Wokwi");
  Serial.println("Autor: Guilherme Yamada Dantas - RM568506");
  Serial.println("Modo padrao: payload no Serial; HTTP opcional via SEND_HTTP.");
  connectWifi();
}

void loop() {
  TempAndHumidity dhtData = dht.getTempAndHumidity();
  float temperatureC = isnan(dhtData.temperature) ? fallbackTemperature() : dhtData.temperature;
  float humidityPct = isnan(dhtData.humidity) ? fallbackHumidity() : dhtData.humidity;
  float smokePpm = readSmokePpm();
  String level = riskLabel(smokePpm, temperatureC);
  String payload = buildPayload(smokePpm, temperatureC, humidityPct);

  updateActuators(level);

  Serial.println();
  Serial.print("sensor_level=");
  Serial.print(level);
  Serial.print(" smoke_ppm=");
  Serial.print(smokePpm, 1);
  Serial.print(" temperature_c=");
  Serial.print(temperatureC, 1);
  Serial.print(" humidity_pct=");
  Serial.println(humidityPct, 1);
  Serial.println(payload);

  postPayload(payload);
  delay(5000);
}
