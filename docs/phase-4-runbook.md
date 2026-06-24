# Phase 4 Runbook

Goal: update ESP32 firmware over the local network from the Raspberry Pi.

## Current OTA Shape

- The Pi serves staged firmware artifacts from the dashboard under `/firmware/...`.
- The Pi publishes per-device OTA commands on `home/sensors/{deviceId}/command`.
- The ESP32 downloads the firmware over HTTP, verifies SHA-256, writes the next OTA partition, publishes OTA status, and reboots.
- USB flashing remains the recovery path.

## Prerequisites

Use the USB-connected `Sunroom Test` ESP32 (`esp32-9c9c1fda3670`) as the bench target for firmware and feature validation before publishing OTA commands to other devices.

If the dashboard code or service unit changes, restart the dashboard service:

```bash
sudo systemctl restart iot-home-dashboard.service
```

Verify firmware serving before publishing an OTA command:

```bash
curl -s -o /tmp/iot-fw-test.bin -w '%{http_code} %{size_download}\n' http://127.0.0.1:8000/firmware/0.1.1-ota-version/firmware.bin
```

Expected result: HTTP `200` and a nonzero byte count. The current simple dashboard server does not implement `HEAD`, so `curl -I` returns `501` even when firmware downloads work.

## Stage Firmware

Build firmware:

```bash
cd /home/scotty/IoT
.venv/bin/pio run -d firmware
```

Stage the built binary and manifest without publishing an OTA command:

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.publish_ota esp32-9c9c1fda3670 0.1.1-ota-version --base-url http://piserver.local:8000 --stage-only
```

The helper writes:

```text
data/firmware/0.1.1-ota-version/firmware.bin
data/firmware/0.1.1-ota-version/manifest.json
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
MQTT_USERNAME=iot MQTT_PASSWORD="$pw" PYTHONPATH=app python3 -m iot_home.publish_ota esp32-9c9c1fda3670 0.1.1-ota-version --base-url http://piserver.local:8000
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

## First Live Result

First live rollout succeeded on 2026-06-20:

- Rollout: `20260620T180807Z-0.1.0-ota-mvp`
- Device: `esp32-9c9c1fda3670`
- OTA status: `downloading`, then `rebooting`
- Post-OTA telemetry: received at `2026-06-20T18:08:33Z` with `restartReason` set to `Software`
- Follow-up: telemetry still reported `firmwareVersion` as `0.1.0-local`; align firmware build/version reporting before using version as the rollout confirmation signal.

Version-reporting rollout also succeeded on 2026-06-20:

- Rollout: `20260620T182134Z-0.1.1-ota-version`
- Device: `esp32-9c9c1fda3670`
- Post-OTA retained status: reported `firmwareVersion` as `0.1.1-ota-version` at `2026-06-20T18:22:24Z`
- Post-OTA telemetry: received at `2026-06-20T18:24:12Z` with `firmwareVersion` set to `0.1.1-ota-version`
