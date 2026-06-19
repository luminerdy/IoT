# Phase 2 Runbook

Goal: build, flash, and verify real ESP32 local MQTT firmware.

## Current Test Device

- Serial port: `/dev/ttyUSB0`
- USB bridge: Silicon Labs CP2102
- Chip: ESP32-D0WDQ6 revision v1.0
- MAC: `9c:9c:1f:da:36:70`
- Local device ID: `esp32-9c9c1fda3670`

## Firmware Project

```text
firmware/
  platformio.ini
  include/secrets.sample.h
  include/secrets.h
  src/main.cpp
```

`firmware/include/secrets.h` is ignored by git and contains local WiFi/MQTT values.

## Location Mapping

Room names live on the Pi, not in firmware. Create a local ignored mapping file:

```bash
cd /home/scotty/IoT
cp config/locations.sample.json config/locations.json
```

Example:

```json
{
  "esp32-9c9c1fda3670": "Sunroom Test"
}
```

## Build

```bash
cd /home/scotty/IoT
.venv/bin/pio run -d firmware
```

## Upload

```bash
cd /home/scotty/IoT
.venv/bin/pio run -d firmware -t upload
```

## Monitor Serial

```bash
cd /home/scotty/IoT
.venv/bin/pio device monitor -d firmware --port /dev/ttyUSB0 --baud 115200
```

## Local MQTT Test

### Production Broker

System Mosquitto is configured for authenticated LAN access on port `1883`.

To recreate or update that configuration:

```bash
cd /home/scotty/IoT
bash scripts/configure_mosquitto_lan.sh iot
```

Use the same password stored in `firmware/include/secrets.h`.

Verify the listener:

```bash
ss -lntp | grep 1883
mosquitto_pub -h <pi-host-or-ip> -p 1883 -u iot -P '<password>' -t test/ping -m ok
```

## Runtime Config

Publish retained per-device config from the Pi:

```bash
cd /home/scotty/IoT
MQTT_USERNAME=iot MQTT_PASSWORD='<password>' PYTHONPATH=app python3 -m iot_home.publish_config esp32-9c9c1fda3670 --report-interval 300 --change-threshold 0.5
```

Supported fields:

- `--report-interval`: seconds between periodic telemetry publishes, 10 to 3600.
- `--change-threshold`: Fahrenheit temperature delta that triggers early telemetry, 0.1 to 10.0.

Publish the firmware defaults as retained config. This is the offline-safe reset path because devices that reconnect later will receive the retained defaults:

```bash
cd /home/scotty/IoT
MQTT_USERNAME=iot MQTT_PASSWORD='<password>' PYTHONPATH=app python3 -m iot_home.publish_config esp32-9c9c1fda3670 --defaults
```

To delete the retained config from the broker, publish an empty retained message. A connected ESP32 will apply firmware defaults when it receives this empty message, but an offline ESP32 will not receive it later because the retained message has been removed:

```bash
cd /home/scotty/IoT
MQTT_USERNAME=iot MQTT_PASSWORD='<password>' PYTHONPATH=app python3 -m iot_home.publish_config esp32-9c9c1fda3670 --clear
```

The ESP32 publishes config apply/reject messages to:

```text
home/sensors/esp32-9c9c1fda3670/response
```

### Temporary Test Broker

For WiFi testing without changing system config, run the project-local test broker on port `1884`:

```bash
cd /home/scotty/IoT
mosquitto -c config/mosquitto-local-test.conf
```

Start the collector against the same port:

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.collector --port 1884
```

## Verified Reading

The flashed ESP32 published telemetry through production Mosquitto to the local collector:

```text
device_id: esp32-9c9c1fda3670
temperature: 84.4 F
humidity: 46.6 %
datetime: 2026-06-16T21:34:05Z
rssi: -42
status: OK
```

## Current Limitations

- The project-local test broker on port `1884` is useful for smoke tests but is not an installed service.
- OTA work has moved to Phase 4; see `docs/phase-4-runbook.md`.
