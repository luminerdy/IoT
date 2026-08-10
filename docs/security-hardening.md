# Security Hardening

## Current Security Model

- ESP32 telemetry uses MQTT username/password authentication.
- Firmware `0.1.4-antirollback` requires OTA commands to include a SHA-256 checksum, a P-256 ECDSA firmware signature, a monotonic `buildNumber`, and a P-256 ECDSA metadata signature over the checksum/build/version/size tuple.
- The OTA private signing key is local-only at `data/keys/ota_signing_key.pem`.
- Firmware downloads may still use local HTTP because the device verifies the downloaded image hash and signature before applying it.
- Dashboard password auth is intentionally disabled; dashboard pages and APIs are available to clients on the home network.
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
MQTT_USERNAME=iot-admin MQTT_PASSWORD='<admin-password>' PYTHONPATH=app \
  python3 -m iot_home.publish_ota esp32-device-id 0.1.4-antirollback \
  --base-url http://iot-pi.local:8000 \
  --build-number 2026070401
```

Watch the OTA status:

```bash
pw=$(awk -F'"' '/MQTT_PASSWORD/ {print $2; exit}' firmware/include/secrets.h)
mosquitto_sub -h localhost -p 1883 -u iot -P "$pw" \
  -t 'home/sensors/esp32-device-id/ota/status' -v
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

Expected rollback rejection from `0.1.4-antirollback` and newer:

```text
rejected: firmware rollback rejected
```

## MQTT TLS And ACLs

Protect the current LAN listener on port `1883` with ACLs before the TLS/per-device migration:

```bash
scripts/configure_mosquitto_lan.sh iot iot-admin
```

The `iot` user remains compatible with the current shared-credential fleet and collector for telemetry/status flow, but cannot publish retained runtime config or OTA commands. Use `iot-admin` for Pi-side config and OTA publisher commands:

```bash
MQTT_USERNAME=iot-admin MQTT_PASSWORD='<admin-password>' PYTHONPATH=app \
  python3 -m iot_home.publish_config esp32-device-id --report-interval 600 --change-threshold 1.0
```

Configure a parallel TLS listener on port `8883`:

```bash
scripts/configure_mosquitto_tls_acl.sh
```

This installs the reviewed
`deploy/mosquitto/iot-home-per-device.acl` at a separate broker path and enables
per-listener settings so it does not replace the interim shared-fleet ACL on
1883. The same ACL is exercised in CI against an isolated broker with two
devices, the read-only collector, and the admin publisher. Add per-device users
before migrating a sensor:

```bash
scripts/add_mqtt_device_user.sh esp32-device-id
```

Do not place a per-device password in `secrets.h`. Firmware
`0.1.9-nvs-tls` and newer accepts a bounded TLS-only profile over the physical
USB serial port and stores the complete profile atomically in NVS. The username
must equal the hardware-derived device ID. The host tool never accepts the
password through argv:

```bash
PYTHONPATH=app .venv/bin/python -m iot_home.provision_mqtt \
  --serial-port /dev/ttyUSB0 \
  --device-id esp32-device-id \
  --connect-host 10.10.10.123 \
  --tls-hostname PiServer.local \
  --mqtt-port 8883 \
  --ca-cert /etc/mosquitto/certs/iot-home/ca.crt
```

It prompts without echo. For automation, `--password-file` accepts only a
mode-0600 file. `--connect-host` may be the Pi LAN IP; `--tls-hostname` remains
the DNS SAN used for SNI and certificate verification. A valid NVS profile
overrides the compiled migration fallback;
clear only during a controlled rollback:

```bash
PYTHONPATH=app .venv/bin/python -m iot_home.provision_mqtt \
  --serial-port /dev/ttyUSB0 --clear
```

Bench the exact firmware against an isolated TLS listener using the tracked
per-device ACL before running the root-owned TLS installer or changing any live
broker listener. After the isolated test, clear the NVS profile and verify the
bench device returns to production. Migrate live devices one at a time; retire
the shared credential and LAN listener only after every active device is on its
unique identity.
