# Progress Log

Use this file for dated accomplishments and important observations. Keep future tasks in `docs/implementation-plan.md` and durable decisions in `docs/decision-record.md`.

## 2026-06-16

### Reviewed Existing Material

- Reviewed existing project notes from local reference material.
- Reviewed current ESP32 code reference from local reference material.
- Reviewed sample AWS IoT payloads from local reference material.
- Reviewed existing AWS-oriented requirements document, `IoT Home Monitoring Requirements v2 2.md`.

### Architecture Direction Changed

- Decided future implementation will remain on ESP32 hardware.
- Removed need for a local OLED/display on each ESP32.
- Removed AWS IoT from the core architecture.
- Chose local-first design using this Raspberry Pi as:
  - MQTT message bus host
  - Data collector
  - SQLite database host
  - Realtime dashboard host
  - Future OTA coordinator

### Local Architecture Documented

- Added `Local-First-Architecture.md`.
- Captured local MQTT topic direction.
- Captured Pi-owned room/location mapping.
- Captured initial local OTA approach.

### USB Test ESP32 Investigation

- Checked for `/dev/ttyUSB*` and `/dev/ttyACM*`; no serial device was visible.
- Checked USB enumeration with elevated `lsusb`; no ESP32 serial bridge was visible.
- Noted likely follow-up items:
  - Confirm data-capable USB cable.
  - Confirm ESP32 board exposes a USB serial interface.
  - Install PlatformIO and/or `esptool`.
  - Ensure user has serial device permissions.
- After changing USB cords, `lsusb` shows `10c4:ea60 Silicon Labs CP210x UART Bridge`.
- Kernel logs show the CP210x adapter attached as `/dev/ttyUSB0`.
- `/dev/ttyUSB0` exists with `root:dialout` ownership and `0660` permissions.
- Installed `esptool` in the project virtual environment.
- Verified ESP32 chip access with `.venv/bin/esptool --port /dev/ttyUSB0 chip-id`.
- Identified chip as ESP32-D0WDQ6 revision v1.0, MAC `9c:9c:1f:da:36:70`.
- Read serial at 115200 baud for 10 seconds; no firmware log lines appeared.
- Added `scotty` to the `dialout` group from another terminal.
- Verified account-level groups now include `dialout`.
- Installed PlatformIO Core in the project virtual environment.
- Verified `.venv/bin/pio device list` detects `/dev/ttyUSB0` as a CP2102 USB to UART Bridge Controller.

### Project Tracking Started

- Created local documentation structure under `/home/scotty/IoT/docs`.
- Added initial README, progress log, decision record, implementation plan, and hardware notes.
- Added `docs/current-status.md` as the quick restart/context-switch summary.
- Established documentation flow:
  - `docs/current-status.md` for where we are right now.
  - `docs/progress-log.md` for accomplishments.
  - `docs/implementation-plan.md` for plans and next tasks.
  - `docs/decision-record.md` for accepted decisions and reasoning.

### Phase 1 Started

- Installed Mosquitto broker, Mosquitto CLI clients, `python3-paho-mqtt`, and `sqlite3`.
- Added `app/iot_home/simulator.py` for simulated ESP32 MQTT telemetry.
- Added `app/iot_home/collector.py` to subscribe to MQTT and write SQLite readings.
- Added `app/iot_home/dashboard.py` for a local dashboard with browser-side polling.
- Added shared SQLite schema/helpers in `app/iot_home/db.py`.
- Added `docs/phase-1-runbook.md`.
- Verified simulator to MQTT to collector to SQLite with three simulated devices.
- Verified dashboard API reads latest SQLite device state.
- Added stale/offline state to the dashboard API and UI.

### Phase 2 Started

- Created PlatformIO firmware project under `firmware/`.
- Added local MQTT firmware that removes AWS IoT and OLED/display dependencies.
- Preserved DHT22 reads on GPIO 15.
- Added retained MQTT online/offline status and local telemetry topic publishing.
- Added ignored `firmware/include/secrets.h` for WiFi/MQTT settings and tracked `secrets.sample.h`.
- Built firmware successfully with PlatformIO.
- Found system Mosquitto only listened on localhost port `1883`.
- Added project-local Mosquitto test config on LAN port `1884`.
- Uploaded firmware to ESP32 on `/dev/ttyUSB0`.
- Verified real ESP32 telemetry in SQLite:
  - Device: `esp32-9c9c1fda3670`
  - Temperature: `82.9 F`
  - Humidity: `44.4 %`
  - Timestamp: `2026-06-16T20:05:57Z`
  - RSSI: `-61`
- Fixed initial `1970-01-01T00:00:00Z` timestamp by waiting for NTP time before publishing.
- Increased MQTT keepalive to 60 seconds after broker logs showed a timeout with the default.
- Added MQTT username/password support to firmware, collector, and simulator.
- Added `scripts/configure_mosquitto_lan.sh` to configure system Mosquitto for authenticated LAN access on port `1883`.
- Built firmware successfully for authenticated MQTT on port `1883`; upload is pending Mosquitto config.
- Configured system Mosquitto to listen on the LAN with username/password authentication.
- Verified authenticated publish to production Mosquitto.
- Uploaded authenticated port `1883` firmware to ESP32.
- Verified real ESP32 telemetry through production Mosquitto into SQLite:
  - Device: `esp32-9c9c1fda3670`
  - Temperature: `84.4 F`
  - Humidity: `46.6 %`
  - Timestamp: `2026-06-16T21:34:05Z`
  - RSSI: `-42`
- Added Pi-side location mapping support with ignored `config/locations.json`.
- Added local mapping from `esp32-9c9c1fda3670` to `Sunroom Test`.
- Created public GitHub repository `luminerdy/IoT`.
- Sanitized local git history to remove old reference files, local IPs, credentials, and legacy AWS-oriented material before public publishing.
- Verified staged/local history scans did not find known WiFi password, MQTT password, local LAN IPs, old AWS endpoint, or key material patterns.
- Local git push from this Pi is blocked by missing GitHub HTTPS/SSH credentials; remote currently has only the README created through the GitHub connector.

## Next Work

- Run the dashboard against the real ESP32 reading.
- Install collector/dashboard as systemd services.
- Push sanitized local `main` to `luminerdy/IoT` from a GitHub-authenticated terminal.
