#pragma once

// Copy this file to secrets.h and fill in local values.
// secrets.h is intentionally ignored by git.

#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

// Use the Pi hostname if mDNS works on your network, otherwise use the Pi IP.
#define MQTT_HOST "iot-pi.local"
#define MQTT_PORT 1883
#define MQTT_USER "iot"
#define MQTT_PASSWORD "replace-with-local-password"

// These are the migration fallback only. The USB provisioning tool stores a
// validated per-device TLS profile in NVS and takes precedence when present.
// Set to 1 for a compiled TLS fallback after the broker certificate is ready.
#define MQTT_USE_TLS 0
#define MQTT_CA_CERT "-----BEGIN CERTIFICATE-----\nreplace-with-local-ca-certificate\n-----END CERTIFICATE-----\n"
