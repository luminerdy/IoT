#include <unity.h>

#include <cstring>
#include <string>

#include "mqtt_provisioning.h"

namespace {

constexpr const char *DEVICE_ID = "esp32-device-a";
constexpr const char *CA_CERT =
  "-----BEGIN CERTIFICATE-----\n"
  "dGVzdC1jZXJ0aWZpY2F0ZQ==\n"
  "-----END CERTIFICATE-----\n";

std::string valid_profile()
{
  return std::string("{") +
    "\"schemaVersion\":1,"
    "\"mqttHost\":\"broker.test\","
    "\"mqttPort\":8883,"
    "\"mqttUsername\":\"" + DEVICE_ID + "\","
    "\"mqttPassword\":\"xxxxxxxxxxxxxxxx\","
    "\"mqttUseTls\":true,"
    "\"mqttCaCert\":\"-----BEGIN CERTIFICATE-----\\n"
    "dGVzdC1jZXJ0aWZpY2F0ZQ==\\n"
    "-----END CERTIFICATE-----\\n\"}";
}

bool parse(const std::string &payload, mqtt_provisioning::Settings *settings, char *error)
{
  return mqtt_provisioning::parse_profile(
    payload.c_str(), payload.size(), DEVICE_ID, settings, error, 96
  );
}

void test_valid_tls_profile_parses()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  TEST_ASSERT_TRUE(parse(valid_profile(), &settings, error));
  TEST_ASSERT_EQUAL_STRING("broker.test", settings.host);
  TEST_ASSERT_EQUAL_UINT16(8883, settings.port);
  TEST_ASSERT_EQUAL_STRING(DEVICE_ID, settings.username);
  TEST_ASSERT_EQUAL_STRING("xxxxxxxxxxxxxxxx", settings.password);
  TEST_ASSERT_TRUE(settings.use_tls);
  TEST_ASSERT_EQUAL_STRING(CA_CERT, settings.ca_cert);
  TEST_ASSERT_EQUAL_STRING("", error);
}

void test_malformed_or_non_object_profiles_are_rejected()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  TEST_ASSERT_FALSE(parse("{", &settings, error));
  TEST_ASSERT_EQUAL_STRING("provisioning profile malformed", error);
  TEST_ASSERT_FALSE(parse("[]", &settings, error));
  TEST_ASSERT_EQUAL_STRING("provisioning profile root invalid", error);
}

void test_unknown_missing_and_nested_fields_are_rejected()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  std::string unknown = valid_profile();
  unknown.replace(unknown.find("\"schemaVersion\""), 15, "\"unexpectedKey\"");
  TEST_ASSERT_FALSE(parse(unknown, &settings, error));
  TEST_ASSERT_EQUAL_STRING("provisioning profile fields invalid", error);

  std::string missing = valid_profile();
  size_t password_start = missing.find(",\"mqttPassword\"");
  size_t password_end = missing.find(",\"mqttUseTls\"", password_start);
  missing.erase(password_start, password_end - password_start);
  TEST_ASSERT_FALSE(parse(missing, &settings, error));
  TEST_ASSERT_EQUAL_STRING("provisioning profile fields invalid", error);

  std::string nested = valid_profile();
  const std::string host_field = "\"mqttHost\":\"broker.test\"";
  nested.replace(
    nested.find(host_field), host_field.size(), "\"mqttHost\":{\"value\":\"broker.test\"}"
  );
  TEST_ASSERT_FALSE(parse(nested, &settings, error));
  TEST_ASSERT_EQUAL_STRING("provisioning field types invalid", error);
}

void test_wrong_field_types_are_rejected()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  std::string payload = valid_profile();
  payload.replace(payload.find("\"mqttPort\":8883"), 15, "\"mqttPort\":\"8883\"");
  TEST_ASSERT_FALSE(parse(payload, &settings, error));
  TEST_ASSERT_EQUAL_STRING("provisioning field types invalid", error);
}

void test_host_and_port_bounds_are_enforced()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  std::string bad_host = valid_profile();
  bad_host.replace(bad_host.find("broker.test"), 11, "https://bad/");
  TEST_ASSERT_FALSE(parse(bad_host, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT host invalid", error);

  std::string bad_port = valid_profile();
  bad_port.replace(bad_port.find("8883"), 4, "0");
  TEST_ASSERT_FALSE(parse(bad_port, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT port invalid", error);
}

void test_username_must_equal_device_identity()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  std::string payload = valid_profile();
  payload.replace(payload.find(DEVICE_ID), strlen(DEVICE_ID), "esp32-device-b");
  TEST_ASSERT_FALSE(parse(payload, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT username must match device ID", error);
}

void test_password_length_is_bounded()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  std::string payload = valid_profile();
  payload.replace(payload.find("xxxxxxxxxxxxxxxx"), 16, "too-short");
  TEST_ASSERT_FALSE(parse(payload, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT password length invalid", error);
}

void test_tls_and_ca_are_required()
{
  mqtt_provisioning::Settings settings{};
  char error[96];
  std::string plaintext = valid_profile();
  plaintext.replace(plaintext.find("true"), 4, "false");
  TEST_ASSERT_FALSE(parse(plaintext, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT TLS is required", error);

  std::string bad_ca = valid_profile();
  size_t cert_start = bad_ca.find("-----BEGIN CERTIFICATE-----");
  bad_ca.replace(cert_start, 27, "not-a-certificate----------");
  TEST_ASSERT_FALSE(parse(bad_ca, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT CA certificate invalid", error);

  std::string bad_base64 = valid_profile();
  size_t body = bad_base64.find("dGVzdC1jZXJ0aWZpY2F0ZQ==");
  bad_base64.replace(body, 24, "dGVzdC1jZXJ0aWZpY2F0ZQ=!");
  TEST_ASSERT_FALSE(parse(bad_base64, &settings, error));
  TEST_ASSERT_EQUAL_STRING("MQTT CA certificate invalid", error);
}

}  // namespace

void setUp() {}
void tearDown() {}

int main(int, char **)
{
  UNITY_BEGIN();
  RUN_TEST(test_valid_tls_profile_parses);
  RUN_TEST(test_malformed_or_non_object_profiles_are_rejected);
  RUN_TEST(test_unknown_missing_and_nested_fields_are_rejected);
  RUN_TEST(test_wrong_field_types_are_rejected);
  RUN_TEST(test_host_and_port_bounds_are_enforced);
  RUN_TEST(test_username_must_equal_device_identity);
  RUN_TEST(test_password_length_is_bounded);
  RUN_TEST(test_tls_and_ca_are_required);
  return UNITY_END();
}
