#include <Arduino.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <Update.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/ecp.h>
#include <mbedtls/sha256.h>
#include <strings.h>
#include <time.h>

#include "ota_public_key.h"
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
constexpr unsigned long DEFAULT_REPORT_INTERVAL_MS = 600000;
constexpr float DEFAULT_CHANGE_THRESHOLD_F = 1.0;
constexpr unsigned long MIN_REPORT_INTERVAL_MS = 10000;
constexpr unsigned long MAX_REPORT_INTERVAL_MS = 3600000;
constexpr float MIN_CHANGE_THRESHOLD_F = 0.1;
constexpr float MAX_CHANGE_THRESHOLD_F = 10.0;
constexpr size_t FILTER_WINDOW_SIZE = 5;
constexpr uint8_t CHANGE_CONFIRMATION_SAMPLES = 3;
constexpr float MIN_VALID_TEMPERATURE_F = -40.0;
constexpr float MAX_VALID_TEMPERATURE_F = 140.0;
constexpr float MIN_VALID_HUMIDITY = 0.0;
constexpr float MAX_VALID_HUMIDITY = 100.0;
constexpr float OUTLIER_TEMPERATURE_DELTA_F = 8.0;
constexpr float OUTLIER_CONFIRMATION_DELTA_F = 2.0;
constexpr uint8_t OUTLIER_CONFIRMATION_SAMPLES = 3;
constexpr unsigned long OTA_NO_PROGRESS_TIMEOUT_MS = 15000;
constexpr size_t TOPIC_LEN = 96;
constexpr size_t PAYLOAD_LEN = 768;

DHT dht(DHT_PIN, DHT_TYPE);
#ifndef MQTT_USE_TLS
#define MQTT_USE_TLS 0
#endif

#if MQTT_USE_TLS
WiFiClientSecure wifiClient;
#else
WiFiClient wifiClient;
#endif
PubSubClient mqtt(wifiClient);

char deviceId[32];
char telemetryTopic[TOPIC_LEN];
char statusTopic[TOPIC_LEN];
char commandTopic[TOPIC_LEN];
char configTopic[TOPIC_LEN];
char responseTopic[TOPIC_LEN];
char otaStatusTopic[TOPIC_LEN];

unsigned long lastReportMs = 0;
unsigned long lastMqttAttemptMs = 0;
unsigned long reportIntervalMs = DEFAULT_REPORT_INTERVAL_MS;
uint32_t seq = 0;
uint32_t readErrors = 0;
uint32_t filteredReadings = 0;
float lastTemperatureF = NAN;
float changeThresholdF = DEFAULT_CHANGE_THRESHOLD_F;
float temperatureWindow[FILTER_WINDOW_SIZE];
float humidityWindow[FILTER_WINDOW_SIZE];
size_t sampleCount = 0;
size_t sampleIndex = 0;
uint8_t consecutiveTempChangeSamples = 0;
float candidateOutlierTemperatureF = NAN;
uint8_t candidateOutlierSamples = 0;

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
  snprintf(responseTopic, sizeof(responseTopic), "home/sensors/%s/response", deviceId);
  snprintf(otaStatusTopic, sizeof(otaStatusTopic), "home/sensors/%s/ota/status", deviceId);
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

#if MQTT_USE_TLS
  wifiClient.setCACert(MQTT_CA_CERT);
#endif

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
  mqtt.publish(statusTopic, payload, retained);
  Serial.printf("Published status: %s\n", payload);
}

float medianOf(const float *values, size_t count)
{
  float sorted[FILTER_WINDOW_SIZE];
  for (size_t i = 0; i < count; i++) {
    sorted[i] = values[i];
  }

  for (size_t i = 1; i < count; i++) {
    float current = sorted[i];
    size_t j = i;
    while (j > 0 && sorted[j - 1] > current) {
      sorted[j] = sorted[j - 1];
      j--;
    }
    sorted[j] = current;
  }

  if (count % 2 == 1) {
    return sorted[count / 2];
  }
  return (sorted[(count / 2) - 1] + sorted[count / 2]) / 2.0f;
}

void resetSensorFilter()
{
  sampleCount = 0;
  sampleIndex = 0;
  consecutiveTempChangeSamples = 0;
  candidateOutlierTemperatureF = NAN;
  candidateOutlierSamples = 0;
}

bool acceptSensorReading(float temperatureF, float humidity)
{
  if (
    temperatureF < MIN_VALID_TEMPERATURE_F ||
    temperatureF > MAX_VALID_TEMPERATURE_F ||
    humidity < MIN_VALID_HUMIDITY ||
    humidity > MAX_VALID_HUMIDITY
  ) {
    filteredReadings++;
    Serial.printf("Filtered implausible reading: temp %.1fF humidity %.1f%%\n", temperatureF, humidity);
    return false;
  }

  if (sampleCount >= 3) {
    float baselineTemperatureF = medianOf(temperatureWindow, sampleCount);
    if (fabs(temperatureF - baselineTemperatureF) > OUTLIER_TEMPERATURE_DELTA_F) {
      if (
        isnan(candidateOutlierTemperatureF) ||
        fabs(temperatureF - candidateOutlierTemperatureF) > OUTLIER_CONFIRMATION_DELTA_F
      ) {
        candidateOutlierTemperatureF = temperatureF;
        candidateOutlierSamples = 1;
      } else {
        candidateOutlierSamples++;
      }

      if (candidateOutlierSamples < OUTLIER_CONFIRMATION_SAMPLES) {
        filteredReadings++;
        Serial.printf(
          "Filtered possible temp outlier: temp %.1fF median %.1fF candidateCount=%u\n",
          temperatureF,
          baselineTemperatureF,
          candidateOutlierSamples
        );
        return false;
      }
    } else {
      candidateOutlierTemperatureF = NAN;
      candidateOutlierSamples = 0;
    }
  }

  temperatureWindow[sampleIndex] = temperatureF;
  humidityWindow[sampleIndex] = humidity;
  sampleIndex = (sampleIndex + 1) % FILTER_WINDOW_SIZE;
  if (sampleCount < FILTER_WINDOW_SIZE) {
    sampleCount++;
  }

  return true;
}

bool filteredSensorReading(float *temperatureF, float *humidity)
{
  if (sampleCount == 0) {
    return false;
  }

  *temperatureF = medianOf(temperatureWindow, sampleCount);
  *humidity = medianOf(humidityWindow, sampleCount);
  return true;
}

bool extractNumber(const char *payload, const char *key, float *value)
{
  char quotedKey[48];
  snprintf(quotedKey, sizeof(quotedKey), "\"%s\"", key);

  const char *keyPos = strstr(payload, quotedKey);
  if (keyPos == nullptr) {
    return false;
  }

  const char *colon = strchr(keyPos, ':');
  if (colon == nullptr) {
    return false;
  }

  char *end = nullptr;
  float parsed = strtof(colon + 1, &end);
  if (end == colon + 1) {
    return false;
  }
  if (isnan(parsed) || isinf(parsed)) {
    return false;
  }

  *value = parsed;
  return true;
}

bool extractString(const char *payload, const char *key, char *value, size_t valueLen)
{
  char quotedKey[48];
  snprintf(quotedKey, sizeof(quotedKey), "\"%s\"", key);

  const char *keyPos = strstr(payload, quotedKey);
  if (keyPos == nullptr) {
    return false;
  }

  const char *colon = strchr(keyPos, ':');
  if (colon == nullptr) {
    return false;
  }

  const char *start = strchr(colon + 1, '"');
  if (start == nullptr) {
    return false;
  }
  start++;

  const char *end = strchr(start, '"');
  if (end == nullptr || end == start) {
    return false;
  }

  size_t len = static_cast<size_t>(end - start);
  if (len >= valueLen) {
    return false;
  }

  memcpy(value, start, len);
  value[len] = '\0';
  return true;
}

void publishConfigResponse(const char *status, const char *message)
{
  char payload[PAYLOAD_LEN];
  String now = isoTimestamp();
  snprintf(
    payload,
    sizeof(payload),
    "{\"deviceId\":\"%s\","
    "\"type\":\"config\","
    "\"status\":\"%s\","
    "\"message\":\"%s\","
    "\"datetime\":\"%s\","
    "\"activeConfig\":{\"reportIntervalSeconds\":%lu,\"changeThresholdF\":%.1f}}",
    deviceId,
    status,
    message,
    now.c_str(),
    static_cast<unsigned long>(reportIntervalMs / 1000),
    changeThresholdF
  );
  mqtt.publish(responseTopic, payload, false);
  Serial.printf("Published config response: %s\n", payload);
}

void applyConfigPayload(const char *payload)
{
  if (strlen(payload) == 0) {
    reportIntervalMs = DEFAULT_REPORT_INTERVAL_MS;
    changeThresholdF = DEFAULT_CHANGE_THRESHOLD_F;
    lastTemperatureF = NAN;
    resetSensorFilter();
    publishConfigResponse("applied", "config cleared");
    return;
  }

  float intervalSeconds = 0.0f;
  float thresholdF = 0.0f;
  bool hasInterval = extractNumber(payload, "reportIntervalSeconds", &intervalSeconds);
  bool hasThreshold = extractNumber(payload, "changeThresholdF", &thresholdF);

  if (!hasInterval && !hasThreshold) {
    publishConfigResponse("rejected", "no supported config fields");
    return;
  }

  unsigned long newReportIntervalMs = reportIntervalMs;
  float newChangeThresholdF = changeThresholdF;

  if (hasInterval) {
    unsigned long parsedMs = static_cast<unsigned long>(intervalSeconds * 1000.0f);
    if (parsedMs < MIN_REPORT_INTERVAL_MS || parsedMs > MAX_REPORT_INTERVAL_MS) {
      publishConfigResponse("rejected", "reportIntervalSeconds out of range");
      return;
    }
    newReportIntervalMs = parsedMs;
  }

  if (hasThreshold) {
    if (thresholdF < MIN_CHANGE_THRESHOLD_F || thresholdF > MAX_CHANGE_THRESHOLD_F) {
      publishConfigResponse("rejected", "changeThresholdF out of range");
      return;
    }
    newChangeThresholdF = thresholdF;
  }

  reportIntervalMs = newReportIntervalMs;
  changeThresholdF = newChangeThresholdF;
  lastTemperatureF = NAN;
  resetSensorFilter();
  publishConfigResponse("applied", "config applied");
}

void publishOtaStatus(const char *status, const char *message, const char *version, const char *rolloutId)
{
  char payload[PAYLOAD_LEN];
  String now = isoTimestamp();
  snprintf(
    payload,
    sizeof(payload),
    "{\"deviceId\":\"%s\","
    "\"type\":\"ota\","
    "\"status\":\"%s\","
    "\"message\":\"%s\","
    "\"version\":\"%s\","
    "\"rolloutId\":\"%s\","
    "\"firmwareVersion\":\"%s\","
    "\"datetime\":\"%s\"}",
    deviceId,
    status,
    message,
    version,
    rolloutId,
    FIRMWARE_VERSION,
    now.c_str()
  );
  mqtt.publish(otaStatusTopic, payload, false);
  Serial.printf("Published OTA status: %s\n", payload);
}

int hexNibble(char c)
{
  if (c >= '0' && c <= '9') {
    return c - '0';
  }
  if (c >= 'a' && c <= 'f') {
    return c - 'a' + 10;
  }
  if (c >= 'A' && c <= 'F') {
    return c - 'A' + 10;
  }
  return -1;
}

bool decodeHex(const char *hex, uint8_t *output, size_t outputLen)
{
  if (strlen(hex) != outputLen * 2) {
    return false;
  }

  for (size_t i = 0; i < outputLen; i++) {
    int high = hexNibble(hex[i * 2]);
    int low = hexNibble(hex[(i * 2) + 1]);
    if (high < 0 || low < 0) {
      return false;
    }
    output[i] = static_cast<uint8_t>((high << 4) | low);
  }
  return true;
}

bool sha256Matches(const char *expectedSha, const uint8_t digest[32])
{
  char actualSha[65];
  for (size_t i = 0; i < 32; i++) {
    snprintf(actualSha + (i * 2), 3, "%02x", digest[i]);
  }
  actualSha[64] = '\0';
  return strcasecmp(actualSha, expectedSha) == 0;
}

bool otaSignatureValid(const char *signatureHex, const uint8_t digest[32])
{
  uint8_t signature[80];
  uint8_t publicX[32];
  uint8_t publicY[32];
  size_t signatureLen = strlen(signatureHex) / 2;

  if (signatureLen == 0 || signatureLen > sizeof(signature) || strlen(signatureHex) % 2 != 0) {
    return false;
  }
  if (!decodeHex(signatureHex, signature, signatureLen) ||
      !decodeHex(OTA_SIGNING_PUBKEY_X_HEX, publicX, sizeof(publicX)) ||
      !decodeHex(OTA_SIGNING_PUBKEY_Y_HEX, publicY, sizeof(publicY))) {
    return false;
  }

  mbedtls_ecdsa_context ctx;
  mbedtls_ecdsa_init(&ctx);

  bool valid = false;
  if (mbedtls_ecp_group_load(&ctx.grp, MBEDTLS_ECP_DP_SECP256R1) == 0 &&
      mbedtls_mpi_read_binary(&ctx.Q.X, publicX, sizeof(publicX)) == 0 &&
      mbedtls_mpi_read_binary(&ctx.Q.Y, publicY, sizeof(publicY)) == 0 &&
      mbedtls_mpi_lset(&ctx.Q.Z, 1) == 0 &&
      mbedtls_ecdsa_read_signature(&ctx, digest, 32, signature, signatureLen) == 0) {
    valid = true;
  }

  mbedtls_ecdsa_free(&ctx);
  return valid;
}

bool performOtaUpdate(
  const char *url,
  const char *expectedSha,
  const char *signatureHex,
  long expectedSize,
  const char *version,
  const char *rolloutId
)
{
  if (WiFi.status() != WL_CONNECTED) {
    publishOtaStatus("rejected", "wifi not connected", version, rolloutId);
    return false;
  }

  WiFiClient httpClient;
  HTTPClient http;
  http.setTimeout(OTA_NO_PROGRESS_TIMEOUT_MS);
  if (!http.begin(httpClient, url)) {
    publishOtaStatus("rejected", "invalid ota url", version, rolloutId);
    return false;
  }

  publishOtaStatus("downloading", "ota download started", version, rolloutId);
  int httpCode = http.GET();
  if (httpCode != HTTP_CODE_OK) {
    http.end();
    publishOtaStatus("failed", "firmware download failed", version, rolloutId);
    return false;
  }

  int contentLength = http.getSize();
  if (expectedSize > 0 && contentLength > 0 && contentLength != expectedSize) {
    http.end();
    publishOtaStatus("rejected", "firmware size mismatch", version, rolloutId);
    return false;
  }

  size_t updateSize = expectedSize > 0 ? static_cast<size_t>(expectedSize) : UPDATE_SIZE_UNKNOWN;
  if (!Update.begin(updateSize)) {
    http.end();
    publishOtaStatus("failed", "ota partition unavailable", version, rolloutId);
    return false;
  }

  mbedtls_sha256_context shaCtx;
  mbedtls_sha256_init(&shaCtx);
  mbedtls_sha256_starts_ret(&shaCtx, 0);

  WiFiClient *stream = http.getStreamPtr();
  uint8_t buffer[1024];
  size_t written = 0;
  unsigned long lastProgressMs = millis();
  bool ok = true;

  while (http.connected() && (contentLength < 0 || written < static_cast<size_t>(contentLength))) {
    size_t available = stream->available();
    if (available == 0) {
      if (millis() - lastProgressMs > OTA_NO_PROGRESS_TIMEOUT_MS) {
        ok = false;
        break;
      }
      delay(10);
      continue;
    }

    size_t toRead = min(available, sizeof(buffer));
    int bytesRead = stream->readBytes(buffer, toRead);
    if (bytesRead <= 0) {
      ok = false;
      break;
    }

    size_t bytesWritten = Update.write(buffer, static_cast<size_t>(bytesRead));
    if (bytesWritten != static_cast<size_t>(bytesRead)) {
      ok = false;
      break;
    }

    mbedtls_sha256_update_ret(&shaCtx, buffer, static_cast<size_t>(bytesRead));
    written += static_cast<size_t>(bytesRead);
    lastProgressMs = millis();
  }

  uint8_t digest[32];
  mbedtls_sha256_finish_ret(&shaCtx, digest);
  mbedtls_sha256_free(&shaCtx);
  http.end();

  if (!ok) {
    Update.abort();
    publishOtaStatus("failed", "firmware stream failed", version, rolloutId);
    return false;
  }
  if (expectedSize > 0 && written != static_cast<size_t>(expectedSize)) {
    Update.abort();
    publishOtaStatus("failed", "firmware length mismatch", version, rolloutId);
    return false;
  }
  if (!sha256Matches(expectedSha, digest)) {
    Update.abort();
    publishOtaStatus("rejected", "firmware sha256 mismatch", version, rolloutId);
    return false;
  }
  if (!otaSignatureValid(signatureHex, digest)) {
    Update.abort();
    publishOtaStatus("rejected", "firmware signature invalid", version, rolloutId);
    return false;
  }
  if (!Update.end(true)) {
    publishOtaStatus("failed", "firmware update finalize failed", version, rolloutId);
    return false;
  }

  publishOtaStatus("rebooting", "firmware update applied", version, rolloutId);
  delay(1000);
  ESP.restart();
  return true;
}

void applyCommandPayload(const char *payload)
{
  char command[32];
  if (!extractString(payload, "command", command, sizeof(command))) {
    publishOtaStatus("rejected", "missing command", "", "");
    return;
  }

  if (strcmp(command, "ota_update") != 0) {
    publishOtaStatus("rejected", "unsupported command", "", "");
    return;
  }

  char url[192];
  char sha256[65];
  char signature[161];
  char version[32];
  char rolloutId[64];
  float sizeValue = 0.0f;

  if (!extractString(payload, "url", url, sizeof(url)) ||
      !extractString(payload, "sha256", sha256, sizeof(sha256)) ||
      !extractString(payload, "signature", signature, sizeof(signature)) ||
      !extractString(payload, "version", version, sizeof(version)) ||
      !extractString(payload, "rolloutId", rolloutId, sizeof(rolloutId)) ||
      strlen(sha256) != 64 ||
      strlen(signature) == 0 ||
      strlen(signature) % 2 != 0) {
    publishOtaStatus("rejected", "invalid ota command", "", "");
    return;
  }

  long expectedSize = 0;
  if (extractNumber(payload, "size", &sizeValue) && sizeValue > 0.0f) {
    expectedSize = static_cast<long>(sizeValue);
  }

  performOtaUpdate(url, sha256, signature, expectedSize, version, rolloutId);
}

void onMqttMessage(char *topic, uint8_t *payload, unsigned int length)
{
  Serial.printf("MQTT message on %s: ", topic);
  for (unsigned int i = 0; i < length; i++) {
    Serial.print(static_cast<char>(payload[i]));
  }
  Serial.println();

  if (strcmp(topic, configTopic) == 0) {
    if (length >= PAYLOAD_LEN) {
      publishConfigResponse("rejected", "config payload too large");
      return;
    }

    char buffer[PAYLOAD_LEN];
    memcpy(buffer, payload, length);
    buffer[length] = '\0';
    applyConfigPayload(buffer);
    return;
  }

  if (strcmp(topic, commandTopic) == 0) {
    if (length >= PAYLOAD_LEN) {
      publishOtaStatus("rejected", "command payload too large", "", "");
      return;
    }

    char buffer[PAYLOAD_LEN];
    memcpy(buffer, payload, length);
    buffer[length] = '\0';
    applyCommandPayload(buffer);
  }
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
    consecutiveTempChangeSamples = 0;
    return true;
  }
  if (millis() - lastReportMs >= reportIntervalMs) {
    consecutiveTempChangeSamples = 0;
    return true;
  }

  if (fabs(temperatureF - lastTemperatureF) >= changeThresholdF) {
    consecutiveTempChangeSamples++;
    return consecutiveTempChangeSamples >= CHANGE_CONFIRMATION_SAMPLES;
  }

  consecutiveTempChangeSamples = 0;
  return false;
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
    "\"numFilteredReadings\":%lu,"
    "\"restartReason\":\"%s\","
    "\"activeConfig\":{\"reportIntervalSeconds\":%lu,\"changeThresholdF\":%.1f},"
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
    static_cast<unsigned long>(filteredReadings),
    resetReason(),
    static_cast<unsigned long>(reportIntervalMs / 1000),
    changeThresholdF
  );

  bool ok = mqtt.publish(telemetryTopic, payload, true);
  Serial.printf("Published telemetry ok=%d: %s\n", ok, payload);
  if (ok) {
    lastTemperatureF = temperatureF;
    lastReportMs = millis();
    consecutiveTempChangeSamples = 0;
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
  if (!acceptSensorReading(temperatureF, humidity)) {
    delay(2000);
    return;
  }

  float filteredTemperatureF = NAN;
  float filteredHumidity = NAN;
  if (!filteredSensorReading(&filteredTemperatureF, &filteredHumidity)) {
    delay(2000);
    return;
  }

  if (shouldPublish(filteredTemperatureF)) {
    publishTelemetry(filteredTemperatureF, filteredHumidity);
  } else {
    Serial.printf(
      "No publish: raw %.1fF %.1f%% filtered %.1fF %.1f%% below confirmed threshold\n",
      temperatureF,
      humidity,
      filteredTemperatureF,
      filteredHumidity
    );
  }

  delay(2000);
}
