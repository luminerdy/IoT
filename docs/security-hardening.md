# Security Hardening

## Current Security Model

- ESP32 telemetry uses MQTT username/password authentication.
- Firmware `0.1.3-signed-ota` requires OTA commands to include both a SHA-256 checksum and a P-256 ECDSA signature.
- The OTA private signing key is local-only at `data/keys/ota_signing_key.pem`.
- Firmware downloads may still use local HTTP because the device verifies the downloaded image hash and signature before applying it.
- Dashboard `/firmware/...` responses are restricted to private, loopback, and link-local client addresses.

## Signed OTA

Generate or rotate the local OTA signing key:

```bash
mkdir -p data/keys
openssl ecparam -name prime256v1 -genkey -noout -out data/keys/ota_signing_key.pem
chmod 0600 data/keys/ota_signing_key.pem
openssl ec -in data/keys/ota_signing_key.pem -pubout -out data/keys/ota_signing_public.pem
```

Copy the public key coordinates into `firmware/include/ota_public_key.h`. Keep the private key out of git.

Stage and publish a signed OTA to the bench device only:

```bash
pw=$(awk -F'"' '/MQTT_PASSWORD/ {print $2; exit}' firmware/include/secrets.h)
MQTT_USERNAME=iot MQTT_PASSWORD="$pw" PYTHONPATH=app \
  python3 -m iot_home.publish_ota esp32-9c9c1fda3670 0.1.3-signed-ota \
  --base-url http://piserver.local:8000
```

Watch the OTA status:

```bash
mosquitto_sub -h localhost -p 1883 -u iot -P "$pw" \
  -t 'home/sensors/esp32-9c9c1fda3670/ota/status' -v
```

Expected success status sequence:

```text
downloading: ota download started
rebooting: firmware update applied
```

Expected bad-signature rejection:

```text
rejected: firmware signature invalid
```

## MQTT TLS And ACLs

Configure a parallel TLS listener on port `8883`:

```bash
scripts/configure_mosquitto_tls_acl.sh
```

This leaves the existing listener alone and adds ACL rules for device-style usernames. Add per-device users before migrating a sensor:

```bash
scripts/add_mqtt_device_user.sh esp32-9c9c1fda3670
```

To test TLS on a bench ESP32, copy the generated CA certificate into `firmware/include/secrets.h`, set:

```c
#define MQTT_PORT 8883
#define MQTT_USER "esp32-9c9c1fda3670"
#define MQTT_USE_TLS 1
```

Then USB flash `Sunroom Test` first and verify it reports telemetry before changing any other device.
