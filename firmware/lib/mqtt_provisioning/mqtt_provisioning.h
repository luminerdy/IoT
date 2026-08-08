#pragma once

#include <stddef.h>
#include <stdint.h>

namespace mqtt_provisioning {

constexpr size_t MAX_HOST_LENGTH = 253;
constexpr size_t MAX_USERNAME_LENGTH = 63;
constexpr size_t MIN_PASSWORD_LENGTH = 16;
constexpr size_t MAX_PASSWORD_LENGTH = 128;
constexpr size_t MAX_CA_CERT_LENGTH = 3072;
// ESP-IDF NVS strings are limited to 4000 bytes including the terminator.
constexpr size_t MAX_PROFILE_JSON_LENGTH = 3900;

struct Settings {
  char host[MAX_HOST_LENGTH + 1];
  uint16_t port;
  char username[MAX_USERNAME_LENGTH + 1];
  char password[MAX_PASSWORD_LENGTH + 1];
  bool use_tls;
  char ca_cert[MAX_CA_CERT_LENGTH + 1];
};

bool parse_profile(
  const char *payload,
  size_t length,
  const char *expected_device_id,
  Settings *settings,
  char *error,
  size_t error_length
);

}  // namespace mqtt_provisioning
