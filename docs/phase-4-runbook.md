# Phase 4 Runbook

Goal: update ESP32 firmware over the local network from the Raspberry Pi.

## Current OTA Shape

- The Pi serves staged firmware artifacts from the dashboard under `/firmware/...`.
- The Pi publishes per-device OTA commands on `home/sensors/{deviceId}/command`.
- The ESP32 downloads the firmware over HTTP, verifies SHA-256, writes the next OTA partition, publishes OTA status, and reboots.
- USB flashing remains the recovery path.

## Prerequisites

The currently connected ESP32 has been USB-flashed with OTA-capable firmware.

The dashboard service must be restarted after deploying the code that serves `/firmware/...`:

```bash
sudo systemctl restart iot-home-dashboard.service
```

Verify firmware serving after restart:

```bash
curl -I http://127.0.0.1:8000/firmware/0.1.0-ota-mvp/firmware.bin
```

Expected result: HTTP `200`. If this returns `404`, the running dashboard service has not picked up the new `/firmware/...` route.

## Stage Firmware

Build firmware:

```bash
cd /home/scotty/IoT
.venv/bin/pio run -d firmware
```

Stage the built binary and manifest without publishing an OTA command:

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.publish_ota esp32-9c9c1fda3670 0.1.0-ota-mvp --base-url http://piserver.local:8000 --stage-only
```

The helper writes:

```text
data/firmware/0.1.0-ota-mvp/firmware.bin
data/firmware/0.1.0-ota-mvp/manifest.json
```

## Watch OTA Status

```bash
cd /home/scotty/IoT
pw=$(awk -F'"' '/MQTT_PASSWORD/ {print $2; exit}' firmware/include/secrets.h)
mosquitto_sub -h localhost -p 1883 -u iot -P "$pw" -t 'home/sensors/esp32-9c9c1fda3670/ota/status' -v
```

## Publish OTA Command

Only run this after confirming the staged firmware URL is reachable from the ESP32 network.

```bash
cd /home/scotty/IoT
pw=$(awk -F'"' '/MQTT_PASSWORD/ {print $2; exit}' firmware/include/secrets.h)
MQTT_USERNAME=iot MQTT_PASSWORD="$pw" PYTHONPATH=app python3 -m iot_home.publish_ota esp32-9c9c1fda3670 0.1.0-ota-mvp --base-url http://piserver.local:8000
```

Expected OTA status progression:

```text
downloading
rebooting
```

After reboot, verify telemetry:

```bash
mosquitto_sub -h localhost -p 1883 -u iot -P "$pw" -t 'home/sensors/esp32-9c9c1fda3670/telemetry' -C 1 -v
```
