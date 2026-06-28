#pragma once

// Copy this file to secrets.h and fill in local values.
// secrets.h is intentionally ignored by git.

#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

// Use the Pi hostname if mDNS works on your network, otherwise use the Pi IP.
#define MQTT_HOST "PiServer.local"
#define MQTT_PORT 1883
#define MQTT_USER "iot"
#define MQTT_PASSWORD "replace-with-local-password"

// Set to 1 after Mosquitto TLS is configured and this certificate matches
// the local CA that signed the broker certificate.
#define MQTT_USE_TLS 0
#define MQTT_CA_CERT R"EOF(
-----BEGIN CERTIFICATE-----
replace-with-local-ca-certificate
-----END CERTIFICATE-----
)EOF"
