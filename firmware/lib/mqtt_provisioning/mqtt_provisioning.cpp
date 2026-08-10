#include "mqtt_provisioning.h"

#include <ArduinoJson.h>

#include <ctype.h>
#include <stdio.h>
#include <string.h>

namespace mqtt_provisioning {
namespace {

constexpr int PROFILE_SCHEMA_VERSION_V1 = 1;
constexpr int PROFILE_SCHEMA_VERSION_V2 = 2;
constexpr size_t EXPECTED_FIELD_COUNT_V1 = 7;
constexpr size_t EXPECTED_FIELD_COUNT_V2 = 8;
constexpr const char *CA_BEGIN = "-----BEGIN CERTIFICATE-----\n";
constexpr const char *CA_END = "\n-----END CERTIFICATE-----\n";

void set_error(char *error, size_t error_length, const char *message)
{
  if (error == nullptr || error_length == 0) {
    return;
  }
  snprintf(error, error_length, "%s", message);
}

bool copy_bounded(char *target, size_t target_length, const char *value)
{
  if (target == nullptr || target_length == 0 || value == nullptr) {
    return false;
  }
  size_t length = strlen(value);
  if (length >= target_length) {
    return false;
  }
  memcpy(target, value, length + 1);
  return true;
}

bool valid_host_name_or_ip(const char *host)
{
  if (host == nullptr) {
    return false;
  }
  size_t length = strlen(host);
  if (length == 0 || length > MAX_HOST_LENGTH) {
    return false;
  }
  for (size_t index = 0; index < length; index++) {
    unsigned char value = static_cast<unsigned char>(host[index]);
    if (!(isalnum(value) || value == '.' || value == '-')) {
      return false;
    }
  }
  return true;
}

bool valid_dns_hostname(const char *host)
{
  if (!valid_host_name_or_ip(host)) {
    return false;
  }
  size_t length = strlen(host);
  bool has_alpha = false;
  bool has_dot = false;
  char previous = '\0';
  for (size_t index = 0; index < length; index++) {
    char value = host[index];
    if (isalpha(static_cast<unsigned char>(value))) {
      has_alpha = true;
    }
    if (value == '.') {
      if (index == 0 || index + 1 == length || previous == '.') {
        return false;
      }
      has_dot = true;
    }
    if ((value == '-' && (index == 0 || index + 1 == length || previous == '.')) ||
        (previous == '-' && value == '.')) {
      return false;
    }
    previous = value;
  }
  return has_alpha && has_dot;
}

bool valid_ca_certificate(const char *certificate)
{
  if (certificate == nullptr) {
    return false;
  }
  size_t length = strlen(certificate);
  size_t begin_length = strlen(CA_BEGIN);
  size_t end_length = strlen(CA_END);
  if (length <= begin_length + end_length || length > MAX_CA_CERT_LENGTH) {
    return false;
  }
  if (strncmp(certificate, CA_BEGIN, begin_length) != 0 ||
      strcmp(certificate + length - end_length, CA_END) != 0) {
    return false;
  }
  if (strstr(certificate + begin_length, "-----BEGIN CERTIFICATE-----") != nullptr ||
      strstr(certificate, "-----END CERTIFICATE-----") !=
        certificate + length - end_length + 1) {
    return false;
  }

  const char *body_end = certificate + length - end_length;
  size_t encoded_length = 0;
  size_t padding = 0;
  bool saw_padding = false;
  for (const char *cursor = certificate + begin_length; cursor < body_end; cursor++) {
    unsigned char value = static_cast<unsigned char>(*cursor);
    if (value == '\n') {
      continue;
    }
    if (value == '=') {
      saw_padding = true;
      padding++;
    } else if (isalnum(value) || value == '+' || value == '/') {
      if (saw_padding) {
        return false;
      }
    } else {
      return false;
    }
    encoded_length++;
  }
  return encoded_length >= 4 && encoded_length % 4 == 0 && padding <= 2;
}

bool known_field(const char *key)
{
  return strcmp(key, "schemaVersion") == 0 || strcmp(key, "mqttHost") == 0 ||
    strcmp(key, "mqttConnectHost") == 0 || strcmp(key, "mqttTlsHostname") == 0 ||
    strcmp(key, "mqttPort") == 0 || strcmp(key, "mqttUsername") == 0 ||
    strcmp(key, "mqttPassword") == 0 || strcmp(key, "mqttUseTls") == 0 ||
    strcmp(key, "mqttCaCert") == 0;
}

}  // namespace

bool parse_profile(
  const char *payload,
  size_t length,
  const char *expected_device_id,
  Settings *settings,
  char *error,
  size_t error_length
)
{
  if (payload == nullptr || expected_device_id == nullptr || settings == nullptr) {
    set_error(error, error_length, "invalid provisioning input");
    return false;
  }
  if (length == 0 || length > MAX_PROFILE_JSON_LENGTH) {
    set_error(error, error_length, "provisioning profile size invalid");
    return false;
  }

  JsonDocument document;
  DeserializationError json_error = deserializeJson(document, payload, length);
  if (json_error) {
    set_error(error, error_length, "provisioning profile malformed");
    return false;
  }
  if (!document.is<JsonObject>()) {
    set_error(error, error_length, "provisioning profile root invalid");
    return false;
  }

  JsonObject object = document.as<JsonObject>();
  if (!object["schemaVersion"].is<int>()) {
    set_error(error, error_length, "provisioning schema invalid");
    return false;
  }
  int schema_version = object["schemaVersion"].as<int>();
  if (schema_version != PROFILE_SCHEMA_VERSION_V1 && schema_version != PROFILE_SCHEMA_VERSION_V2) {
    set_error(error, error_length, "provisioning schema invalid");
    return false;
  }

  size_t expected_field_count =
    schema_version == PROFILE_SCHEMA_VERSION_V1 ? EXPECTED_FIELD_COUNT_V1 : EXPECTED_FIELD_COUNT_V2;
  if (object.size() != expected_field_count) {
    set_error(error, error_length, "provisioning profile fields invalid");
    return false;
  }
  for (JsonPair pair : object) {
    if (!known_field(pair.key().c_str())) {
      set_error(error, error_length, "provisioning profile fields invalid");
      return false;
    }
  }

  if (schema_version == PROFILE_SCHEMA_VERSION_V1 && !object["mqttHost"].is<const char *>()) {
    set_error(error, error_length, "provisioning field types invalid");
    return false;
  }
  if (schema_version == PROFILE_SCHEMA_VERSION_V2 &&
      (!object["mqttConnectHost"].is<const char *>() ||
       !object["mqttTlsHostname"].is<const char *>())) {
    set_error(error, error_length, "provisioning field types invalid");
    return false;
  }
  if (!object["mqttUsername"].is<const char *>() ||
      !object["mqttPassword"].is<const char *>() ||
      !object["mqttCaCert"].is<const char *>() ||
      !object["mqttPort"].is<unsigned int>() || !object["mqttUseTls"].is<bool>()) {
    set_error(error, error_length, "provisioning field types invalid");
    return false;
  }

  const char *connect_host = schema_version == PROFILE_SCHEMA_VERSION_V1
    ? object["mqttHost"].as<const char *>()
    : object["mqttConnectHost"].as<const char *>();
  const char *tls_hostname = schema_version == PROFILE_SCHEMA_VERSION_V1
    ? object["mqttHost"].as<const char *>()
    : object["mqttTlsHostname"].as<const char *>();
  unsigned int port = object["mqttPort"].as<unsigned int>();
  const char *username = object["mqttUsername"].as<const char *>();
  const char *password = object["mqttPassword"].as<const char *>();
  bool use_tls = object["mqttUseTls"].as<bool>();
  const char *ca_cert = object["mqttCaCert"].as<const char *>();

  if (!valid_host_name_or_ip(connect_host)) {
    set_error(error, error_length, "MQTT connect host invalid");
    return false;
  }
  if (!valid_dns_hostname(tls_hostname)) {
    set_error(error, error_length, "MQTT TLS hostname invalid");
    return false;
  }
  if (port == 0 || port > 65535) {
    set_error(error, error_length, "MQTT port invalid");
    return false;
  }
  if (strcmp(username, expected_device_id) != 0 || strlen(username) > MAX_USERNAME_LENGTH) {
    set_error(error, error_length, "MQTT username must match device ID");
    return false;
  }
  size_t password_length = strlen(password);
  if (password_length < MIN_PASSWORD_LENGTH || password_length > MAX_PASSWORD_LENGTH) {
    set_error(error, error_length, "MQTT password length invalid");
    return false;
  }
  for (size_t index = 0; index < password_length; index++) {
    unsigned char value = static_cast<unsigned char>(password[index]);
    if (value < 33 || value > 126) {
      set_error(error, error_length, "MQTT password characters invalid");
      return false;
    }
  }
  if (!use_tls) {
    set_error(error, error_length, "MQTT TLS is required");
    return false;
  }
  if (!valid_ca_certificate(ca_cert)) {
    set_error(error, error_length, "MQTT CA certificate invalid");
    return false;
  }

  memset(settings, 0, sizeof(*settings));
  if (!copy_bounded(settings->connect_host, sizeof(settings->connect_host), connect_host) ||
      !copy_bounded(settings->tls_hostname, sizeof(settings->tls_hostname), tls_hostname) ||
      !copy_bounded(settings->username, sizeof(settings->username), username) ||
      !copy_bounded(settings->password, sizeof(settings->password), password) ||
      !copy_bounded(settings->ca_cert, sizeof(settings->ca_cert), ca_cert)) {
    set_error(error, error_length, "provisioning field length invalid");
    return false;
  }
  settings->port = static_cast<uint16_t>(port);
  settings->use_tls = true;
  set_error(error, error_length, "");
  return true;
}

}  // namespace mqtt_provisioning
