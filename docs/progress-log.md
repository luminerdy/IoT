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
- Local git push from this Pi is blocked by missing GitHub HTTPS/SSH credentials.
- Submitted project documentation to GitHub through the GitHub connector.

## 2026-06-18

### Always-On Services

- Added tracked systemd unit files for:
  - `iot-home-collector.service`
  - `iot-home-dashboard.service`
- Added `scripts/install_systemd_services.sh` to install the unit files, create `/etc/iot-home/iot-home.env`, enable the services, and start them.
- Installed and started both services on the Pi.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are running.
- Verified the dashboard is listening on `0.0.0.0:8000`.
- Verified the dashboard API shows `esp32-9c9c1fda3670` mapped to `Sunroom Test`.
- Verified a fresh real ESP32 reading reached the collector:
  - Temperature: `78.6 F`
  - Humidity: `53.9 %`
  - Timestamp: `2026-06-18T13:59:15Z`
  - RSSI: `-61`
- Published the sanitized local source tree to `luminerdy/IoT` through the GitHub connector after local HTTPS and SSH push attempts remained unavailable.

## 2026-06-19

### Phase 3 Started

- Added retained per-device runtime config handling to ESP32 firmware.
- Supported `reportIntervalSeconds` and `changeThresholdF` from `home/sensors/{deviceId}/config`.
- Added config apply/reject responses on `home/sensors/{deviceId}/response`.
- Added active config reporting in telemetry.
- Added `iot_home.publish_config` for publishing retained config from the Pi, including explicit defaults and retained-delete modes.
- Flashed retained-config firmware to the real ESP32.
- Verified a retained config update changed active config to `reportIntervalSeconds=30` and `changeThresholdF=0.2`.
- Verified telemetry reported the updated active config.
- Verified a non-retained invalid config was rejected without changing the active config.
- Restored retained config to firmware defaults: `reportIntervalSeconds=300` and `changeThresholdF=0.5`.
- Cleared retained simulator telemetry/status messages from MQTT.
- Backed up SQLite to `data/iot-before-sim-cleanup.db`.
- Removed historical `esp32-sim-*` rows from SQLite so the dashboard shows only the physical ESP32.

### Phase 4 Started

- Confirmed the default ESP32 partition table includes `ota_0` and `ota_1`, each `0x140000` bytes.
- Added firmware handling for `ota_update` commands on `home/sensors/{deviceId}/command`.
- Added firmware OTA status publishing on `home/sensors/{deviceId}/ota/status`.
- Added HTTP firmware download, SHA-256 verification, OTA partition write, and reboot handling.
- Added dashboard file serving for staged OTA artifacts under `/firmware/...`.
- Added `iot_home.publish_ota` to stage `firmware.bin`, write `manifest.json`, and publish a per-device OTA command.
- Staged `0.1.0-ota-mvp` under `data/firmware/0.1.0-ota-mvp/`.
- Verified staged firmware download and SHA-256 through a temporary dashboard server on port `8001`.
- USB-flashed the OTA-capable firmware to `esp32-9c9c1fda3670`.
- Verified the ESP32 came back online and published DHT22 telemetry after the OTA-capable USB flash.
- Attempted to restart `iot-home-dashboard.service`, but sudo required an interactive password. The running dashboard still returns 404 for `/firmware/...` until restarted.

## 2026-06-20

### First Live OTA Rollout

- Verified the normal dashboard service on port `8000` serves the staged OTA artifact with a `GET` request:
  - URL: `http://127.0.0.1:8000/firmware/0.1.0-ota-mvp/firmware.bin`
  - Result: HTTP `200`, `824272` bytes.
- Confirmed `curl -I` is not a valid check for the current dashboard server because it does not implement `HEAD` and returns HTTP `501`.
- Published OTA rollout `20260620T180807Z-0.1.0-ota-mvp` to `esp32-9c9c1fda3670`.
- Observed OTA status progression:
  - `downloading` at `2026-06-20T18:08:08Z`
  - `rebooting` at `2026-06-20T18:08:22Z`
- Verified post-OTA telemetry after reboot:
  - Timestamp: `2026-06-20T18:08:33Z`
  - Temperature: `78.6 F`
  - Humidity: `55.9 %`
  - RSSI: `-43`
  - Uptime: `9` seconds
  - Restart reason: `Software`
- Noted follow-up: telemetry still reports `firmwareVersion` as `0.1.0-local` even though the rollout version was `0.1.0-ota-mvp`.
- Updated the firmware build flag to report `FIRMWARE_VERSION` as `0.1.1-ota-version`.
- Built and staged `0.1.1-ota-version`; verified the dashboard served the new artifact with HTTP `200`, `824272` bytes.
- Published OTA rollout `20260620T182134Z-0.1.1-ota-version` to `esp32-9c9c1fda3670`.
- Verified retained device status after reboot reported `firmwareVersion` as `0.1.1-ota-version` at `2026-06-20T18:22:24Z`.
- Verified post-OTA telemetry reported `firmwareVersion` as `0.1.1-ota-version`:
  - Timestamp: `2026-06-20T18:24:12Z`
  - Temperature: `78.1 F`
  - Humidity: `51.0 %`
  - RSSI: `-44`
  - Uptime: `113` seconds
  - Restart reason: `Software`
- Verified the dashboard API now shows `Sunroom Test` online with `firmwareVersion` set to `0.1.1-ota-version`.

## 2026-06-21

### Web Dashboard Upgrade

- Upgraded `app/iot_home/dashboard.py` from the minimal polling table into a fuller local web app:
  - Summary metrics for device count, average temperature, average humidity, and average RSSI.
  - Per-device cards with online/stale/offline state.
  - Latest-reading table with firmware version and relative last-seen timestamps.
  - Dependency-free inline SVG 24-hour temperature and humidity trend.
- Added bounded SQLite history querying through `iot_home.db.reading_history`.
- Added `/api/history` with bounded `hours` and `limit` query parameters.
- Restarted `iot-home-dashboard.service` so the boot-enabled service loaded the new dashboard code.
- Verified `iot-home-dashboard.service` is enabled, active, and listening on `0.0.0.0:8000`.
- Verified the updated HTML, `/api/latest`, and `/api/history` are served from the live dashboard service.

### Filtered Telemetry Policy

- Confirmed the live retained ESP32 config was `reportIntervalSeconds=300` and `changeThresholdF=0.5`, producing roughly 5-minute readings.
- Decided to return the default report interval to 600 seconds to preserve the original AWS-cost-conscious cadence if telemetry is later forwarded to cloud services.
- Added firmware filtering policy for DHT22 readings:
  - sample every 2 seconds,
  - reject implausible temperature/humidity values,
  - median-filter the last 5 valid samples,
  - suppress one-off temperature jumps more than `8°F` from the recent median unless 3 similar samples arrive consecutively,
  - publish early only after 3 consecutive valid filtered samples exceed the configured temperature threshold.
- Updated default firmware and Pi config helper values to `reportIntervalSeconds=600` and `changeThresholdF=1.0`.
- Updated dashboard stale-device default to 1200 seconds for 10-minute telemetry with headroom.
- Built firmware version `0.1.2-filtered-telemetry`, staged it under `data/firmware/0.1.2-filtered-telemetry/`, verified the dashboard served the binary with HTTP `200`, and published the OTA command.
- Verified the ESP32 came back online and published telemetry with `firmwareVersion` set to `0.1.2-filtered-telemetry`, `numFilteredReadings=0`, and active config `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Could not restart `iot-home-dashboard.service` to load the 1200-second stale threshold because `sudo` requires an interactive password in this session. The updated default will load on the next service restart or reboot.

### Existing Device HTTP OTA

- Checked existing device `http://10.10.10.113/update`; it serves ElegantOTA and reports identity `{"id":"C215B80C","hardware":"ESP32"}`.
- Uploaded `0.1.2-filtered-telemetry` using ElegantOTA multipart `POST /update` with fields `MD5` and `firmware`.
- Verified the device joined local MQTT as `esp32-0cb815c288f4` with `firmwareVersion` set to `0.1.2-filtered-telemetry`.
- Published retained defaults for `esp32-0cb815c288f4`: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Added `esp32-0cb815c288f4` to `config/locations.json` as `GarageDriveay` and updated the current SQLite device row so the live dashboard shows it immediately.
- Updated dashboard code so `/api/latest` reloads `config/locations.json` on each request after the next service restart.
- Committed the local source and documentation changes with message `Add filtered telemetry and dashboard history`.
- Attempted to push to GitHub. HTTPS push failed because no username/token is configured locally; SSH push failed because this Pi does not have a GitHub public key configured.

## Next Work

- Add OTA rollback and failure-path tests.
