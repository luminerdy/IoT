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

- Firmware publishes `location: UNMAPPED`; Pi-side location mapping still needs to be implemented.
- The project-local test broker on port `1884` is useful for smoke tests but is not an installed service.
- OTA is not implemented yet.
