#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <Update.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/ecp.h>
#include <mbedtls/sha256.h>
#include <mbedtls/x509_crt.h>
#include <time.h>

#include "ota_public_key.h"
#include "ota_manifest.h"
#include "mqtt_provisioning.h"
#include "sensor_core.h"
#include "secrets.h"

#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "0.1.0-local"
#endif

#ifndef OTA_BUILD_NUMBER
#define OTA_BUILD_NUMBER 0
#endif

namespace {
constexpr uint8_t DHT_PIN = 15;
constexpr uint8_t DHT_TYPE = DHT22;
constexpr unsigned long WIFI_RECONNECT_MS = 10000;
constexpr unsigned long MQTT_RETRY_MS = 5000;
constexpr unsigned long NETWORK_FAILURE_REBOOT_MS = 15UL * 60UL * 1000UL;
constexpr unsigned long SAFETY_REBOOT_BASE_MS = 7UL * 24UL * 60UL * 60UL * 1000UL;
constexpr unsigned long SAFETY_REBOOT_STAGGER_MS = 24UL * 60UL * 60UL * 1000UL;
constexpr unsigned long DEFAULT_REPORT_INTERVAL_MS = 600000;
constexpr float DEFAULT_CHANGE_THRESHOLD_F = 1.0;
constexpr unsigned long MIN_REPORT_INTERVAL_MS = 10000;
constexpr unsigned long MAX_REPORT_INTERVAL_MS = 3600000;
constexpr float MIN_CHANGE_THRESHOLD_F = 0.1;
constexpr float MAX_CHANGE_THRESHOLD_F = 10.0;
constexpr unsigned long OTA_NO_PROGRESS_TIMEOUT_MS = 15000;
constexpr size_t TOPIC_LEN = 96;
constexpr size_t PAYLOAD_LEN = 768;
constexpr const char *ROLLBACK_PREF_NAMESPACE = "iot-ota";
constexpr const char *ROLLBACK_PREF_KEY = "build";
constexpr const char *RECOVERY_PREF_KEY = "recovery";
constexpr const char *MQTT_PREF_NAMESPACE = "iot-mqtt";
constexpr const char *MQTT_PREF_KEY = "config";
constexpr const char *MQTT_PROVISION_PREFIX = "IOT_MQTT_PROVISION ";
constexpr const char *MQTT_PROVISION_CLEAR = "IOT_MQTT_CLEAR";
constexpr const char *MQTT_PROVISION_STATUS = "IOT_MQTT_STATUS";
constexpr size_t MQTT_PROVISION_SERIAL_BUFFER =
  mqtt_provisioning::MAX_PROFILE_JSON_LENGTH + 512;

DHT dht(DHT_PIN, DHT_TYPE);
#ifndef MQTT_USE_TLS
#define MQTT_USE_TLS 0
#endif
#ifndef MQTT_CA_CERT
#define MQTT_CA_CERT ""
#endif

WiFiClient plainWifiClient;
WiFiClientSecure secureWifiClient;
class TlsNamedHostClient : public Client {
 public:
  explicit TlsNamedHostClient(WiFiClientSecure &client) : client_(client) {}

  void configure(const char *tls_hostname, const char *ca_cert)
  {
    tls_hostname_ = tls_hostname;
    ca_cert_ = ca_cert;
    client_.setCACert(ca_cert_);
  }

  int connect(IPAddress ip, uint16_t port) override
  {
    return client_.connect(ip, port, tls_hostname_, ca_cert_, nullptr, nullptr);
  }

  int connect(const char *host, uint16_t port) override
  {
    IPAddress address;
    if (!address.fromString(host) && !WiFi.hostByName(host, address)) {
      return 0;
    }
    return client_.connect(address, port, tls_hostname_, ca_cert_, nullptr, nullptr);
  }

  size_t write(uint8_t value) override { return client_.write(value); }
  size_t write(const uint8_t *buffer, size_t size) override { return client_.write(buffer, size); }
  int available() override { return client_.available(); }
  int read() override { return client_.read(); }
  int read(uint8_t *buffer, size_t size) override { return client_.read(buffer, size); }
  int peek() override { return client_.peek(); }
  void flush() override { client_.flush(); }
  void stop() override { client_.stop(); }
  uint8_t connected() override { return client_.connected(); }
  operator bool() override { return client_; }

 private:
  WiFiClientSecure &client_;
  const char *tls_hostname_ = "";
  const char *ca_cert_ = "";
};

TlsNamedHostClient tlsNamedHostClient(secureWifiClient);
PubSubClient mqtt;
mqtt_provisioning::Settings mqttSettings{};
mqtt_provisioning::Settings mqttProvisioningCandidate{};
bool mqttProfileProvisioned = false;
size_t mqttStoredProfileBytes = 0;
size_t mqttParsedCaBytes = 0;
uint32_t mqttParsedCaFingerprint = 0;
String serialProvisioningLine;
bool serialProvisioningOverflow = false;

char deviceId[32];
char telemetryTopic[TOPIC_LEN];
char statusTopic[TOPIC_LEN];
char commandTopic[TOPIC_LEN];
char configTopic[TOPIC_LEN];
char responseTopic[TOPIC_LEN];
char otaStatusTopic[TOPIC_LEN];

uint32_t mqttCaFingerprint(const char *certificate)
{
  uint32_t hash = 2166136261UL;
  for (const char *cursor = certificate; *cursor != '\0'; cursor++) {
    hash ^= static_cast<uint8_t>(*cursor);
    hash *= 16777619UL;
  }
  return hash;
}

bool mqttCaCertificateParses(const char *certificate)
{
  mbedtls_x509_crt parsed;
  mbedtls_x509_crt_init(&parsed);
  int result = mbedtls_x509_crt_parse(
    &parsed,
    reinterpret_cast<const unsigned char *>(certificate),
    strlen(certificate) + 1
  );
  mbedtls_x509_crt_free(&parsed);
  return result == 0;
}

unsigned long lastReportMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;
unsigned long networkFailureStartMs = 0;
unsigned long safetyRebootAtMs = 0;
bool wifiConnectionInitialized = false;
char bootRecoveryReason[24] = "none";
unsigned long reportIntervalMs = DEFAULT_REPORT_INTERVAL_MS;
uint32_t seq = 0;
uint32_t readErrors = 0;
uint32_t filteredReadings = 0;
float lastTemperatureF = NAN;
float changeThresholdF = DEFAULT_CHANGE_THRESHOLD_F;
sensor_core::SensorFilter sensorFilter;
sensor_core::PublishPolicy publishPolicy;

uint32_t storedBuildNumber()
{
  Preferences prefs;
  if (!prefs.begin(ROLLBACK_PREF_NAMESPACE, true)) {
    return 0;
  }
  uint32_t buildNumber = prefs.getUInt(ROLLBACK_PREF_KEY, 0);
  prefs.end();
  return buildNumber;
}

void rememberCurrentBuildNumber()
{
  if (OTA_BUILD_NUMBER <= 0) {
    Serial.println("OTA anti-rollback build number is not configured");
    return;
  }

  Preferences prefs;
  if (!prefs.begin(ROLLBACK_PREF_NAMESPACE, false)) {
    Serial.println("Failed to open OTA anti-rollback preferences");
    return;
  }

  uint32_t stored = prefs.getUInt(ROLLBACK_PREF_KEY, 0);
  if (OTA_BUILD_NUMBER > stored) {
    prefs.putUInt(ROLLBACK_PREF_KEY, OTA_BUILD_NUMBER);
    Serial.printf("Stored OTA anti-rollback build number %lu\n", static_cast<unsigned long>(OTA_BUILD_NUMBER));
  } else {
    Serial.printf("OTA anti-rollback build number already at %lu\n", static_cast<unsigned long>(stored));
  }
  prefs.end();
}

void loadBootRecoveryReason()
{
  Preferences prefs;
  if (!prefs.begin(ROLLBACK_PREF_NAMESPACE, true)) {
    return;
  }
  String stored = prefs.getString(RECOVERY_PREF_KEY, "none");
  prefs.end();
  snprintf(bootRecoveryReason, sizeof(bootRecoveryReason), "%s", stored.c_str());
}

void clearBootRecoveryReason()
{
  if (strcmp(bootRecoveryReason, "none") == 0) {
    return;
  }

  Preferences prefs;
  if (prefs.begin(ROLLBACK_PREF_NAMESPACE, false)) {
    prefs.remove(RECOVERY_PREF_KEY);
    prefs.end();
  }
  snprintf(bootRecoveryReason, sizeof(bootRecoveryReason), "none");
}

void restartForRecovery(const char *reason)
{
  Serial.printf("Recovery restart requested: %s\n", reason);
  Preferences prefs;
  if (prefs.begin(ROLLBACK_PREF_NAMESPACE, false)) {
    prefs.putString(RECOVERY_PREF_KEY, reason);
    prefs.end();
  }
  delay(250);
  ESP.restart();
}

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

void loadCompiledMqttSettings()
{
  snprintf(mqttSettings.connect_host, sizeof(mqttSettings.connect_host), "%s", MQTT_HOST);
  snprintf(mqttSettings.tls_hostname, sizeof(mqttSettings.tls_hostname), "%s", MQTT_HOST);
  mqttSettings.port = MQTT_PORT;
  snprintf(mqttSettings.username, sizeof(mqttSettings.username), "%s", MQTT_USER);
  snprintf(mqttSettings.password, sizeof(mqttSettings.password), "%s", MQTT_PASSWORD);
  mqttSettings.use_tls = MQTT_USE_TLS != 0;
  snprintf(mqttSettings.ca_cert, sizeof(mqttSettings.ca_cert), "%s", MQTT_CA_CERT);
  mqttProfileProvisioned = false;
  mqttStoredProfileBytes = 0;
  mqttParsedCaBytes = strlen(mqttSettings.ca_cert);
  mqttParsedCaFingerprint = mqttCaFingerprint(mqttSettings.ca_cert);
}

void loadMqttSettings()
{
  loadCompiledMqttSettings();

  Preferences prefs;
  if (!prefs.begin(MQTT_PREF_NAMESPACE, true)) {
    Serial.println("MQTT provisioning unavailable; using compiled fallback");
    return;
  }
  String stored = prefs.getString(MQTT_PREF_KEY, "");
  prefs.end();
  if (stored.length() == 0) {
    Serial.println("MQTT profile source: compiled fallback");
    return;
  }
  mqttStoredProfileBytes = stored.length();

  char error[96];
  if (!mqtt_provisioning::parse_profile(
        stored.c_str(),
        stored.length(),
        deviceId,
        &mqttProvisioningCandidate,
        error,
        sizeof(error)
      )) {
    Serial.printf("Stored MQTT provisioning rejected: %s; using compiled fallback\n", error);
    return;
  }
  if (!mqttCaCertificateParses(mqttProvisioningCandidate.ca_cert)) {
    Serial.println("Stored MQTT CA certificate rejected; using compiled fallback");
    return;
  }
  mqttParsedCaBytes = strlen(mqttProvisioningCandidate.ca_cert);
  mqttParsedCaFingerprint = mqttCaFingerprint(mqttProvisioningCandidate.ca_cert);
  mqttSettings = mqttProvisioningCandidate;
  mqttProfileProvisioned = true;
  Serial.println("MQTT profile source: NVS per-device TLS");
}

void configureMqttTransport()
{
  if (mqttSettings.use_tls) {
    tlsNamedHostClient.configure(mqttSettings.tls_hostname, mqttSettings.ca_cert);
    mqtt.setClient(tlsNamedHostClient);
  } else {
    mqtt.setClient(plainWifiClient);
  }
  mqtt.setServer(mqttSettings.connect_host, mqttSettings.port);
}

bool storeMqttProfile(const String &profile)
{
  Preferences prefs;
  if (!prefs.begin(MQTT_PREF_NAMESPACE, false)) {
    return false;
  }
  size_t written = prefs.putString(MQTT_PREF_KEY, profile);
  prefs.end();
  return written == profile.length();
}

bool clearMqttProfile()
{
  Preferences prefs;
  if (!prefs.begin(MQTT_PREF_NAMESPACE, false)) {
    return false;
  }
  bool removed = prefs.remove(MQTT_PREF_KEY);
  prefs.end();
  return removed || !mqttProfileProvisioned;
}

void restartAfterProvisioning(const char *message)
{
  Serial.println(message);
  Serial.flush();
  delay(250);
  ESP.restart();
}

void processSerialProvisioningLine(const String &line)
{
  if (line == MQTT_PROVISION_STATUS) {
    Serial.printf(
      "MQTT provisioning status: source=%s tls=%d profileBytes=%u parsedCaBytes=%u "
      "parsedCaFingerprint=%08lx activeCaBytes=%u activeCaFingerprint=%08lx\n",
      mqttProfileProvisioned ? "nvs" : "compiled",
      mqttSettings.use_tls ? 1 : 0,
      static_cast<unsigned int>(mqttStoredProfileBytes),
      static_cast<unsigned int>(mqttParsedCaBytes),
      static_cast<unsigned long>(mqttParsedCaFingerprint),
      static_cast<unsigned int>(strlen(mqttSettings.ca_cert)),
      static_cast<unsigned long>(mqttCaFingerprint(mqttSettings.ca_cert))
    );
    return;
  }
  if (line == MQTT_PROVISION_CLEAR) {
    if (!clearMqttProfile()) {
      Serial.println("MQTT provisioning clear failed");
      return;
    }
    restartAfterProvisioning("MQTT provisioning cleared; restarting");
    return;
  }
  if (!line.startsWith(MQTT_PROVISION_PREFIX)) {
    return;
  }

  String profile = line.substring(strlen(MQTT_PROVISION_PREFIX));
  char error[96];
  if (!mqtt_provisioning::parse_profile(
        profile.c_str(),
        profile.length(),
        deviceId,
        &mqttProvisioningCandidate,
        error,
        sizeof(error)
      )) {
    Serial.printf("MQTT provisioning rejected: %s\n", error);
    return;
  }
  if (!mqttCaCertificateParses(mqttProvisioningCandidate.ca_cert)) {
    Serial.println("MQTT provisioning rejected: MQTT CA certificate parse failed");
    return;
  }
  if (!storeMqttProfile(profile)) {
    Serial.println("MQTT provisioning rejected: NVS write failed");
    return;
  }
  restartAfterProvisioning("MQTT provisioning applied; restarting");
}

void maintainSerialProvisioning()
{
  while (Serial.available() > 0) {
    char value = static_cast<char>(Serial.read());
    if (value == '\r') {
      continue;
    }
    if (value == '\n') {
      if (serialProvisioningOverflow) {
        Serial.println("MQTT provisioning rejected: profile too large");
      } else if (serialProvisioningLine.length() > 0) {
        processSerialProvisioningLine(serialProvisioningLine);
      }
      serialProvisioningLine = "";
      serialProvisioningOverflow = false;
      continue;
    }
    if (serialProvisioningOverflow) {
      continue;
    }
    if (serialProvisioningLine.length() >=
        mqtt_provisioning::MAX_PROFILE_JSON_LENGTH + strlen(MQTT_PROVISION_PREFIX)) {
      serialProvisioningLine = "";
      serialProvisioningOverflow = true;
      continue;
    }
    serialProvisioningLine += value;
  }
}

void startWifiConnection()
{
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttemptMs = millis();
  Serial.printf("Connecting to WiFi SSID %s\n", WIFI_SSID);
}

void maintainWifi()
{
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnectionInitialized = false;
    if (millis() - lastWifiAttemptMs >= WIFI_RECONNECT_MS) {
      Serial.println("WiFi still disconnected; retrying");
      WiFi.disconnect();
      startWifiConnection();
    }
    return;
  }

  if (wifiConnectionInitialized) {
    return;
  }
  wifiConnectionInitialized = true;
  Serial.printf("WiFi connected, IP=%s RSSI=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  waitForTime(15000);
}

unsigned long deviceSafetyRebootDelayMs()
{
  uint32_t hash = 2166136261UL;
  for (const char *cursor = deviceId; *cursor != '\0'; cursor++) {
    hash ^= static_cast<uint8_t>(*cursor);
    hash *= 16777619UL;
  }
  return SAFETY_REBOOT_BASE_MS + (hash % SAFETY_REBOOT_STAGGER_MS);
}

void maintainRecoveryTimers()
{
  bool connected = WiFi.status() == WL_CONNECTED && mqtt.connected();
  unsigned long nowMs = millis();

  if (connected) {
    networkFailureStartMs = 0;
  } else if (networkFailureStartMs == 0) {
    networkFailureStartMs = nowMs;
  } else if (nowMs - networkFailureStartMs >= NETWORK_FAILURE_REBOOT_MS) {
    restartForRecovery("network_timeout");
  }

  if (nowMs >= safetyRebootAtMs) {
    restartForRecovery("weekly_safety");
  }
}

void publishStatus(const char *status, bool retained)
{
  char payload[PAYLOAD_LEN];
  String now = isoTimestamp();
  JsonDocument document;
  document["deviceId"] = deviceId;
  document["status"] = status;
  document["firmwareVersion"] = FIRMWARE_VERSION;
  document["buildNumber"] = static_cast<unsigned long>(OTA_BUILD_NUMBER);
  document["datetime"] = now.c_str();
  document["localIp"] = WiFi.localIP().toString();
  if (measureJson(document) >= sizeof(payload)) {
    Serial.println("Status payload too large");
    return;
  }
  serializeJson(document, payload, sizeof(payload));
  mqtt.publish(statusTopic, payload, retained);
  Serial.printf("Published status: %s\n", payload);
}

void resetSensorFilter()
{
  sensorFilter.reset();
  publishPolicy.reset();
}

bool acceptSensorReading(float temperatureF, float humidity)
{
  sensor_core::ReadingDecision decision = sensorFilter.accept(temperatureF, humidity);
  if (decision.result == sensor_core::ReadingResult::implausible) {
    filteredReadings++;
    Serial.printf("Filtered implausible reading: temp %.1fF humidity %.1f%%\n", temperatureF, humidity);
    return false;
  }
  if (decision.result == sensor_core::ReadingResult::pending_outlier) {
    filteredReadings++;
    Serial.printf(
      "Filtered possible temp outlier: temp %.1fF median %.1fF candidateCount=%u\n",
      temperatureF,
      decision.baseline_temperature_f,
      decision.candidate_samples
    );
    return false;
  }
  return true;
}

bool filteredSensorReading(float *temperatureF, float *humidity)
{
  return sensorFilter.filtered_reading(temperatureF, humidity);
}

void publishConfigResponse(const char *status, const char *message)
{
  char payload[PAYLOAD_LEN];
  char thresholdText[16];
  String now = isoTimestamp();
  snprintf(thresholdText, sizeof(thresholdText), "%.1f", changeThresholdF);
  JsonDocument document;
  document["deviceId"] = deviceId;
  document["type"] = "config";
  document["status"] = status;
  document["message"] = message;
  document["datetime"] = now.c_str();
  JsonObject activeConfig = document["activeConfig"].to<JsonObject>();
  activeConfig["reportIntervalSeconds"] = static_cast<unsigned long>(reportIntervalMs / 1000);
  activeConfig["changeThresholdF"] = serialized(thresholdText);
  if (measureJson(document) >= sizeof(payload)) {
    Serial.println("Config response payload too large");
    return;
  }
  serializeJson(document, payload, sizeof(payload));
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

  JsonDocument document;
  DeserializationError error = deserializeJson(document, payload);
  if (error || !document.is<JsonObject>()) {
    publishConfigResponse("rejected", "invalid config json");
    return;
  }

  JsonVariant intervalValue = document["reportIntervalSeconds"];
  JsonVariant thresholdValue = document["changeThresholdF"];
  bool hasInterval = !intervalValue.isNull();
  bool hasThreshold = !thresholdValue.isNull();

  if (!hasInterval && !hasThreshold) {
    publishConfigResponse("rejected", "no supported config fields");
    return;
  }

  unsigned long newReportIntervalMs = reportIntervalMs;
  float newChangeThresholdF = changeThresholdF;

  if (hasInterval) {
    if (!intervalValue.is<float>()) {
      publishConfigResponse("rejected", "reportIntervalSeconds invalid");
      return;
    }
    float intervalSeconds = intervalValue.as<float>();
    if (isnan(intervalSeconds) || isinf(intervalSeconds)) {
      publishConfigResponse("rejected", "reportIntervalSeconds invalid");
      return;
    }
    unsigned long parsedMs = static_cast<unsigned long>(intervalSeconds * 1000.0f);
    if (parsedMs < MIN_REPORT_INTERVAL_MS || parsedMs > MAX_REPORT_INTERVAL_MS) {
      publishConfigResponse("rejected", "reportIntervalSeconds out of range");
      return;
    }
    newReportIntervalMs = parsedMs;
  }

  if (hasThreshold) {
    if (!thresholdValue.is<float>()) {
      publishConfigResponse("rejected", "changeThresholdF invalid");
      return;
    }
    float thresholdF = thresholdValue.as<float>();
    if (isnan(thresholdF) || isinf(thresholdF)) {
      publishConfigResponse("rejected", "changeThresholdF invalid");
      return;
    }
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
  JsonDocument document;
  document["deviceId"] = deviceId;
  document["type"] = "ota";
  document["status"] = status;
  document["message"] = message;
  document["version"] = version;
  document["rolloutId"] = rolloutId;
  document["firmwareVersion"] = FIRMWARE_VERSION;
  document["datetime"] = now.c_str();
  if (measureJson(document) >= sizeof(payload)) {
    Serial.println("OTA status payload too large");
    return;
  }
  serializeJson(document, payload, sizeof(payload));
  mqtt.publish(otaStatusTopic, payload, false);
  Serial.printf("Published OTA status: %s\n", payload);
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
  if (!ota_manifest::decode_hex(signatureHex, signature, signatureLen) ||
      !ota_manifest::decode_hex(OTA_SIGNING_PUBKEY_X_HEX, publicX, sizeof(publicX)) ||
      !ota_manifest::decode_hex(OTA_SIGNING_PUBKEY_Y_HEX, publicY, sizeof(publicY))) {
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

bool otaMetadataSignatureValid(
  const char *metadataSignatureHex,
  const char *expectedSha,
  uint32_t buildNumber,
  const char *version,
  long expectedSize
)
{
  char metadata[256];
  snprintf(
    metadata,
    sizeof(metadata),
    "iot-home-ota-v2\n%s\n%lu\n%s\n%ld\n",
    expectedSha,
    static_cast<unsigned long>(buildNumber),
    version,
    expectedSize
  );

  uint8_t digest[32];
  mbedtls_sha256_context shaCtx;
  mbedtls_sha256_init(&shaCtx);
  mbedtls_sha256_starts_ret(&shaCtx, 0);
  mbedtls_sha256_update_ret(&shaCtx, reinterpret_cast<const uint8_t *>(metadata), strlen(metadata));
  mbedtls_sha256_finish_ret(&shaCtx, digest);
  mbedtls_sha256_free(&shaCtx);

  return otaSignatureValid(metadataSignatureHex, digest);
}

bool validateMetadataSignature(const ota_manifest::Manifest &manifest, void *)
{
  return otaMetadataSignatureValid(
    manifest.metadata_signature,
    manifest.sha256,
    manifest.build_number,
    manifest.version,
    static_cast<long>(manifest.size)
  );
}

bool validateFirmwareSignature(const char *signatureHex, const uint8_t digest[32], void *)
{
  return otaSignatureValid(signatureHex, digest);
}

bool performOtaUpdate(const ota_manifest::Manifest &manifest)
{
  const uint32_t configuredBuildNumber = OTA_BUILD_NUMBER > 0
    ? static_cast<uint32_t>(OTA_BUILD_NUMBER)
    : 0;
  const ota_manifest::PreflightResult preflight = ota_manifest::validate_preflight(
    manifest,
    configuredBuildNumber,
    storedBuildNumber(),
    validateMetadataSignature,
    nullptr
  );
  if (preflight != ota_manifest::PreflightResult::ready) {
    publishOtaStatus(
      "rejected",
      ota_manifest::preflight_message(preflight),
      manifest.version,
      manifest.rollout_id
    );
    return false;
  }

  if (WiFi.status() != WL_CONNECTED) {
    publishOtaStatus("rejected", "wifi not connected", manifest.version, manifest.rollout_id);
    return false;
  }

  WiFiClient httpClient;
  HTTPClient http;
  http.setTimeout(OTA_NO_PROGRESS_TIMEOUT_MS);
  if (!http.begin(httpClient, manifest.url)) {
    publishOtaStatus("rejected", "invalid ota url", manifest.version, manifest.rollout_id);
    return false;
  }

  publishOtaStatus("downloading", "ota download started", manifest.version, manifest.rollout_id);
  int httpCode = http.GET();
  if (httpCode != HTTP_CODE_OK) {
    http.end();
    publishOtaStatus("failed", "firmware download failed", manifest.version, manifest.rollout_id);
    return false;
  }

  int contentLength = http.getSize();
  if (contentLength > 0 && static_cast<uint32_t>(contentLength) != manifest.size) {
    http.end();
    publishOtaStatus("rejected", "firmware size mismatch", manifest.version, manifest.rollout_id);
    return false;
  }

  if (!Update.begin(static_cast<size_t>(manifest.size))) {
    http.end();
    publishOtaStatus("failed", "ota partition unavailable", manifest.version, manifest.rollout_id);
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
    publishOtaStatus("failed", "firmware stream failed", manifest.version, manifest.rollout_id);
    return false;
  }
  const ota_manifest::DownloadResult validation = ota_manifest::validate_download(
    manifest,
    written,
    digest,
    validateFirmwareSignature,
    nullptr
  );
  if (validation != ota_manifest::DownloadResult::valid) {
    Update.abort();
    const char *status = validation == ota_manifest::DownloadResult::length_mismatch
      ? "failed"
      : "rejected";
    publishOtaStatus(
      status,
      ota_manifest::download_message(validation),
      manifest.version,
      manifest.rollout_id
    );
    return false;
  }
  if (!Update.end(true)) {
    publishOtaStatus(
      "failed",
      "firmware update finalize failed",
      manifest.version,
      manifest.rollout_id
    );
    return false;
  }

  publishOtaStatus(
    "rebooting",
    "firmware update applied",
    manifest.version,
    manifest.rollout_id
  );
  delay(1000);
  ESP.restart();
  return true;
}

void applyCommandPayload(const char *payload, size_t length)
{
  ota_manifest::Manifest manifest = {};
  const ota_manifest::ParseResult result = ota_manifest::parse(payload, length, &manifest);
  if (result != ota_manifest::ParseResult::ok) {
    publishOtaStatus("rejected", ota_manifest::parse_message(result), "", "");
    return;
  }

  performOtaUpdate(manifest);
}

void onMqttMessage(char *topic, uint8_t *payload, unsigned int length)
{
  Serial.printf("MQTT message on %s length=%u\n", topic, length);

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
    applyCommandPayload(buffer, length);
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
  JsonDocument willDocument;
  willDocument["deviceId"] = deviceId;
  willDocument["status"] = "offline";
  willDocument["reason"] = "mqtt_lwt";
  if (measureJson(willDocument) >= sizeof(willPayload)) {
    Serial.println("MQTT LWT payload too large");
    return false;
  }
  serializeJson(willDocument, willPayload, sizeof(willPayload));

  Serial.printf(
    "Connecting to MQTT %s:%u as %s tls=%d tlsHost=%s\n",
    mqttSettings.connect_host,
    static_cast<unsigned int>(mqttSettings.port),
    deviceId,
    mqttSettings.use_tls ? 1 : 0,
    mqttSettings.tls_hostname
  );
  bool connected = mqtt.connect(
    deviceId,
    mqttSettings.username,
    mqttSettings.password,
    statusTopic,
    1,
    true,
    willPayload
  );
  if (!connected) {
    Serial.printf("MQTT connect failed, state=%d\n", mqtt.state());
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
  return publishPolicy.should_publish(
    temperatureF,
    lastTemperatureF,
    millis(),
    lastReportMs,
    reportIntervalMs,
    changeThresholdF
  );
}

void publishTelemetry(float temperatureF, float humidity)
{
  char payload[PAYLOAD_LEN];
  char temperatureText[16];
  char humidityText[16];
  char thresholdText[16];
  String now = isoTimestamp();
  seq++;
  snprintf(temperatureText, sizeof(temperatureText), "%.1f", temperatureF);
  snprintf(humidityText, sizeof(humidityText), "%.1f", humidity);
  snprintf(thresholdText, sizeof(thresholdText), "%.1f", changeThresholdF);

  JsonDocument document;
  document["schemaVersion"] = "2.0-local";
  document["seq"] = static_cast<unsigned long>(seq);
  document["deviceId"] = deviceId;
  document["location"] = "UNMAPPED";
  document["firmwareVersion"] = FIRMWARE_VERSION;
  document["buildNumber"] = static_cast<unsigned long>(OTA_BUILD_NUMBER);
  document["sensorType"] = "DHT22";
  document["datetime"] = now.c_str();
  document["temperature"] = serialized(temperatureText);
  document["humidity"] = serialized(humidityText);
  JsonObject units = document["units"].to<JsonObject>();
  units["temperature"] = "F";
  document["rssi"] = WiFi.RSSI();
  document["localIp"] = WiFi.localIP().toString();
  document["uptimeSeconds"] = static_cast<unsigned long>(millis() / 1000);
  document["numReadErrors"] = static_cast<unsigned long>(readErrors);
  document["numFilteredReadings"] = static_cast<unsigned long>(filteredReadings);
  document["restartReason"] = resetReason();
  document["recoveryReason"] = bootRecoveryReason;
  JsonObject activeConfig = document["activeConfig"].to<JsonObject>();
  activeConfig["reportIntervalSeconds"] = static_cast<unsigned long>(reportIntervalMs / 1000);
  activeConfig["changeThresholdF"] = serialized(thresholdText);
  document["status"] = "OK";
  if (measureJson(document) >= sizeof(payload)) {
    Serial.println("Telemetry payload too large");
    return;
  }
  serializeJson(document, payload, sizeof(payload));

  bool ok = mqtt.publish(telemetryTopic, payload, false);
  Serial.printf("Published telemetry ok=%d: %s\n", ok, payload);
  if (ok) {
    lastTemperatureF = temperatureF;
    lastReportMs = millis();
    publishPolicy.reset();
    clearBootRecoveryReason();
  }
}
}

void setup()
{
  Serial.setRxBufferSize(MQTT_PROVISION_SERIAL_BUFFER);
  Serial.begin(115200);
  delay(1000);
  dht.begin();

  Serial.printf("Starting firmware %s\n", FIRMWARE_VERSION);
  rememberCurrentBuildNumber();
  loadBootRecoveryReason();
  buildDeviceIdentity();
  loadMqttSettings();
  configureMqttTransport();
  serialProvisioningLine.reserve(
    mqtt_provisioning::MAX_PROFILE_JSON_LENGTH + strlen(MQTT_PROVISION_PREFIX)
  );
  Serial.println("MQTT provisioning ready on USB serial");
  safetyRebootAtMs = deviceSafetyRebootDelayMs();
  Serial.printf(
    "Safety reboot scheduled after %lu seconds\n",
    static_cast<unsigned long>(safetyRebootAtMs / 1000)
  );
  startWifiConnection();

  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(PAYLOAD_LEN);
  mqtt.setKeepAlive(60);
}

void loop()
{
  maintainSerialProvisioning();
  maintainWifi();

  if (!connectMqtt()) {
    maintainRecoveryTimers();
    delay(100);
    return;
  }
  mqtt.loop();
  maintainRecoveryTimers();

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
