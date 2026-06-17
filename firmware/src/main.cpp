#include <Arduino.h>
#include <DHT.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <time.h>

#include "secrets.h"

#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "0.1.0-local"
#endif

namespace {
constexpr uint8_t LED_PIN = 2;
constexpr uint8_t DHT_PIN = 15;
constexpr uint8_t DHT_TYPE = DHT22;
constexpr unsigned long WIFI_RETRY_MS = 500;
constexpr unsigned long MQTT_RETRY_MS = 5000;
constexpr unsigned long REPORT_INTERVAL_MS = 300000;
constexpr float CHANGE_THRESHOLD_F = 0.5;
constexpr size_t TOPIC_LEN = 96;
constexpr size_t PAYLOAD_LEN = 512;

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

char deviceId[32];
char telemetryTopic[TOPIC_LEN];
char statusTopic[TOPIC_LEN];
char commandTopic[TOPIC_LEN];
char configTopic[TOPIC_LEN];

unsigned long lastReportMs = 0;
unsigned long lastMqttAttemptMs = 0;
uint32_t seq = 0;
uint32_t readErrors = 0;
float lastTemperatureF = NAN;

String isoTimestamp()
{
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 100)) {
    return String("1970-01-01T00:00:00Z");
  }
  if (timeinfo.tm_year + 1900 < 2024) {
    return String("1970-01-01T00:00:00Z");
  }

  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

bool waitForTime(unsigned long timeoutMs)
{
  unsigned long startMs = millis();
  Serial.print("Waiting for NTP time");
  while (millis() - startMs < timeoutMs) {
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 250) && timeinfo.tm_year + 1900 >= 2024) {
      Serial.println();
      Serial.printf(
        "Time synced: %04d-%02d-%02dT%02d:%02d:%02dZ\n",
        timeinfo.tm_year + 1900,
        timeinfo.tm_mon + 1,
        timeinfo.tm_mday,
        timeinfo.tm_hour,
        timeinfo.tm_min,
        timeinfo.tm_sec
      );
      return true;
    }
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.println("NTP time not ready; telemetry will use fallback timestamp until sync completes");
  return false;
}

const char *resetReason()
{
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON:
      return "PowerOn";
    case ESP_RST_SW:
      return "Software";
    case ESP_RST_PANIC:
      return "Panic";
    case ESP_RST_INT_WDT:
      return "InterruptWatchdog";
    case ESP_RST_TASK_WDT:
      return "TaskWatchdog";
    case ESP_RST_WDT:
      return "Watchdog";
    case ESP_RST_DEEPSLEEP:
      return "DeepSleep";
    case ESP_RST_BROWNOUT:
      return "Brownout";
    default:
      return "Unknown";
  }
}

void blink(unsigned int count, unsigned int delayMs)
{
  for (unsigned int i = 0; i < count; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
  }
}

void buildDeviceIdentity()
{
  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(
    deviceId,
    sizeof(deviceId),
    "esp32-%02x%02x%02x%02x%02x%02x",
    mac[0],
    mac[1],
    mac[2],
    mac[3],
    mac[4],
    mac[5]
  );
  snprintf(telemetryTopic, sizeof(telemetryTopic), "home/sensors/%s/telemetry", deviceId);
  snprintf(statusTopic, sizeof(statusTopic), "home/sensors/%s/status", deviceId);
  snprintf(commandTopic, sizeof(commandTopic), "home/sensors/%s/command", deviceId);
  snprintf(configTopic, sizeof(configTopic), "home/sensors/%s/config", deviceId);
}

void connectWifi()
{
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.printf("Connecting to WiFi SSID %s", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(WIFI_RETRY_MS);
    Serial.print(".");
  }
  Serial.println();
  Serial.printf("WiFi connected, IP=%s RSSI=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  waitForTime(15000);
}

void publishStatus(const char *status, bool retained)
{
  char payload[PAYLOAD_LEN];
  String now = isoTimestamp();
  snprintf(
    payload,
    sizeof(payload),
    "{\"deviceId\":\"%s\",\"status\":\"%s\",\"firmwareVersion\":\"%s\",\"datetime\":\"%s\"}",
    deviceId,
    status,
    FIRMWARE_VERSION,
    now.c_str()
  );
  mqtt.publish(statusTopic, payload, true);
  Serial.printf("Published status: %s\n", payload);
}

void onMqttMessage(char *topic, uint8_t *payload, unsigned int length)
{
  Serial.printf("MQTT message on %s: ", topic);
  for (unsigned int i = 0; i < length; i++) {
    Serial.print(static_cast<char>(payload[i]));
  }
  Serial.println();
}

bool connectMqtt()
{
  if (mqtt.connected()) {
    return true;
  }

  unsigned long nowMs = millis();
  if (nowMs - lastMqttAttemptMs < MQTT_RETRY_MS) {
    return false;
  }
  lastMqttAttemptMs = nowMs;

  char willPayload[160];
  snprintf(
    willPayload,
    sizeof(willPayload),
    "{\"deviceId\":\"%s\",\"status\":\"offline\",\"reason\":\"mqtt_lwt\"}",
    deviceId
  );

  Serial.printf("Connecting to MQTT %s:%d as %s\n", MQTT_HOST, MQTT_PORT, deviceId);
  bool connected = mqtt.connect(
    deviceId,
    MQTT_USER,
    MQTT_PASSWORD,
    statusTopic,
    1,
    true,
    willPayload
  );
  if (!connected) {
    Serial.printf("MQTT connect failed, state=%d\n", mqtt.state());
    blink(1, 100);
    return false;
  }

  Serial.println("MQTT connected");
  mqtt.subscribe(commandTopic, 1);
  mqtt.subscribe(configTopic, 1);
  publishStatus("online", true);
  return true;
}

bool shouldPublish(float temperatureF)
{
  if (isnan(lastTemperatureF)) {
    return true;
  }
  if (millis() - lastReportMs >= REPORT_INTERVAL_MS) {
    return true;
  }
  return fabs(temperatureF - lastTemperatureF) >= CHANGE_THRESHOLD_F;
}

void publishTelemetry(float temperatureF, float humidity)
{
  char payload[PAYLOAD_LEN];
  String now = isoTimestamp();
  seq++;

  snprintf(
    payload,
    sizeof(payload),
    "{\"schemaVersion\":\"2.0-local\","
    "\"seq\":%lu,"
    "\"deviceId\":\"%s\","
    "\"location\":\"UNMAPPED\","
    "\"firmwareVersion\":\"%s\","
    "\"sensorType\":\"DHT22\","
    "\"datetime\":\"%s\","
    "\"temperature\":%.1f,"
    "\"humidity\":%.1f,"
    "\"units\":{\"temperature\":\"F\"},"
    "\"rssi\":%d,"
    "\"uptimeSeconds\":%lu,"
    "\"numReadErrors\":%lu,"
    "\"restartReason\":\"%s\","
    "\"status\":\"OK\"}",
    static_cast<unsigned long>(seq),
    deviceId,
    FIRMWARE_VERSION,
    now.c_str(),
    temperatureF,
    humidity,
    WiFi.RSSI(),
    static_cast<unsigned long>(millis() / 1000),
    static_cast<unsigned long>(readErrors),
    resetReason()
  );

  bool ok = mqtt.publish(telemetryTopic, payload, true);
  Serial.printf("Published telemetry ok=%d: %s\n", ok, payload);
  if (ok) {
    lastTemperatureF = temperatureF;
    lastReportMs = millis();
    blink(1, 50);
  }
}
}

void setup()
{
  Serial.begin(115200);
  delay(1000);
  pinMode(LED_PIN, OUTPUT);
  dht.begin();

  Serial.printf("Starting firmware %s\n", FIRMWARE_VERSION);
  connectWifi();
  buildDeviceIdentity();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(PAYLOAD_LEN);
  mqtt.setKeepAlive(60);
}

void loop()
{
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  if (!connectMqtt()) {
    delay(100);
    return;
  }
  mqtt.loop();

  float humidity = dht.readHumidity();
  float temperatureC = dht.readTemperature();
  if (isnan(humidity) || isnan(temperatureC)) {
    readErrors++;
    Serial.printf("DHT22 read failed, errors=%lu\n", static_cast<unsigned long>(readErrors));
    delay(2000);
    return;
  }

  float temperatureF = (temperatureC * 1.8f) + 32.0f;
  if (shouldPublish(temperatureF)) {
    publishTelemetry(temperatureF, humidity);
  } else {
    Serial.printf("No publish: temp %.1fF humidity %.1f%% below threshold\n", temperatureF, humidity);
  }

  delay(2000);
}
