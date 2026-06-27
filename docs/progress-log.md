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

### Fleet ElegantOTA HTTP Migration

- Verified all ten requested legacy update URLs initially served `/update` with HTTP `200`:
  - `Den` `10.10.10.107`
  - `FrontBedroom` `10.10.10.111`
  - `Garage` `10.10.10.110`
  - `Laundryroom` `10.10.10.102`
  - `LaundryroomAC` `10.10.10.105`
  - `MasterBedroom` `10.10.10.104`
  - `Office` `10.10.10.106`
  - `Porch` `10.10.10.114`
  - `WallBehindWH` `10.10.10.112`
  - `WaterHeater` `10.10.10.101`
- Added follow-up device candidate:
  - `Lightpole` `10.10.10.122`; this device reportedly connects infrequently. Probes returned `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`. Neighbor discovery resolved MAC `94:b9:7e:d5:2a:78`, so the expected local firmware device ID is `esp32-94b97ed52a78`.
- Uploaded `data/firmware/0.1.2-filtered-telemetry/firmware.bin` with MD5 `9071f35fb2984b23d05ab371a4192d48` using ElegantOTA multipart `POST /update`.
- Upload responses:
  - HTTP `200 OK`: `Den`, `FrontBedroom`, `Garage`, `LaundryroomAC`, `MasterBedroom`, `Office`, `Porch`, `WallBehindWH`, `WaterHeater`
  - Uncertain/failure: `Laundryroom` returned an empty reply during the first POST; retry returned HTTP `400` with body `OTA could not begin`, and old `/update` still responds.
- Confirmed MQTT reporting on `0.1.2-filtered-telemetry`:
  - `Den` -> `esp32-3c71bf642440`
  - `FrontBedroom` -> `esp32-9c9c1fdd632c`
  - `Garage` -> `esp32-94b97ec7bcdc`
  - `Porch` -> `esp32-240ac4f8f574`
  - `WallBehindWH` -> `esp32-240ac4fa418c`
- Added those mappings to ignored local `config/locations.json`, updated current SQLite device rows, and published retained defaults (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) to the confirmed migrated devices. Also pre-added `Lightpole` as `esp32-94b97ed52a78` based on the resolved MAC-derived ID.
- Final legacy `/update` probe after upload:
  - still HTTP `200`: `Laundryroom` `10.10.10.102`
  - no longer responding on old `/update`: all other nine requested IPs
- `LaundryroomAC`, `MasterBedroom`, `Office`, and `WaterHeater` had HTTP `200 OK` upload responses and old `/update` disappeared, but no MQTT status/telemetry had been seen by the final check.
- Attempted `systemctl restart iot-home-collector.service` so the collector would reload the new local mappings, but systemd required interactive authentication. A reboot should reload `config/locations.json` for collector writes; the dashboard API already reloads the mapping file dynamically.

### 12-Device Follow-Up Check

- Rechecked the 11 listed fleet devices plus `Sunroom Test` on 2026-06-21 at about 21:06 CDT.
- Dashboard API confirmed MQTT telemetry on firmware `0.1.2-filtered-telemetry` for `Den`, `FrontBedroom`, `Garage`, `LaundryroomAC`, `Porch`, `WallBehindWH`, and `Sunroom Test`. The existing `GarageDriveay` sensor is also online on the same firmware.
- Neighbor discovery showed `Sunroom Test` at `10.10.10.124`, matching MAC/device ID `9c:9c:1f:da:36:70` / `esp32-9c9c1fda3670`.
- Direct HTTP probes showed the migrated MQTT-reporting devices refuse port 80, which is expected after leaving the old ElegantOTA firmware.
- `Laundryroom` at `10.10.10.102` still serves legacy `Version 5.2.1` at `/` and returns HTTP `401` on `/update`.
- `MasterBedroom` (`10.10.10.104`), `Office` (`10.10.10.106`), `WaterHeater` (`10.10.10.101`), and `Lightpole` (`10.10.10.122`) failed direct HTTP checks and have no current MQTT telemetry records.
- Corrected the current SQLite `devices` row for `esp32-4022d8ee4904` from `UNMAPPED` to `LaundryroomAC`; collector service restart remains blocked by interactive systemd authentication, so a reboot or manual service restart is still needed for future collector log lines to load the newest location file.

### Post-Device-Reboot Follow-Up

- Rechecked after manual reboot of all target IoT devices except `Lightpole` on 2026-06-21 at about 21:32 CDT.
- `Office` came online as `esp32-240ac4f8fecc`; neighbor discovery maps that MAC-derived ID to `10.10.10.106`.
- `WaterHeater` came online as `esp32-9c9c1fc5cf1c`; neighbor discovery maps that MAC-derived ID to `10.10.10.101`.
- Added `Office` and `WaterHeater` to ignored local `config/locations.json`, updated their SQLite device rows, and published retained defaults (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) to both devices.
- Dashboard API now shows `Den`, `FrontBedroom`, `Garage`, `GarageDriveay`, `LaundryroomAC`, `Office`, `Porch`, `Sunroom Test`, `WallBehindWH`, and `WaterHeater` online on `0.1.2-filtered-telemetry`.
- `MasterBedroom` (`10.10.10.104`) still times out on `/` and `/update` and has no MQTT telemetry record.
- `Laundryroom` (`10.10.10.102`) still serves legacy `Version 5.2.1` at `/` and returns HTTP `401` on `/update`.
- `Lightpole` was not rebooted during this check and remains pending/not reporting.
- Attempted `systemctl restart iot-home-collector.service` after adding the new local mappings, but systemd still requires interactive authentication. The dashboard API shows the corrected labels; collector log labels will need a Pi reboot or manual service restart to load the new mapping file.

### Post-Pi-Reboot Verification

- Rechecked after the Pi reboot on 2026-06-21 at about 21:37 CDT.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are enabled and active since boot at 21:35:51 CDT.
- Verified the collector loaded `config/locations.json`; service logs show `Office` and `WaterHeater` by name.
- Verified `http://127.0.0.1:8000/api/latest` shows `Den`, `FrontBedroom`, `Garage`, `GarageDriveay`, `LaundryroomAC`, `Office`, `Porch`, `Sunroom Test`, `WallBehindWH`, and `WaterHeater` online on `0.1.2-filtered-telemetry`.
- Confirmed `Office` and `WaterHeater` mappings are present in `config/locations.json` and SQLite device rows.
- Rechecked remaining devices:
  - `Laundryroom` (`10.10.10.102`) still serves legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`; mapped ID `esp32-240ac4fa383c` still has no retained MQTT status or telemetry.
  - `MasterBedroom` (`10.10.10.104`) still fails direct HTTP checks on `/` and `/update`; no device ID has been discovered from MQTT.
  - `Lightpole` (`10.10.10.122`) still fails direct HTTP checks on `/` and `/update`; mapped expected ID `esp32-94b97ed52a78` still has no retained MQTT status or telemetry.

### SunroomDoor Added

- Added `SunroomDoor` at `10.10.10.109` on 2026-06-21 at about 21:43 CDT.
- Verified it still serves legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`.
- Neighbor discovery resolved MAC `24:0a:c4:fa:39:3c`, so the expected local firmware device ID is `esp32-240ac4fa393c`.
- Added `esp32-240ac4fa393c` to ignored local `config/locations.json` as `SunroomDoor`.
- Added a current SQLite device placeholder for `SunroomDoor` with status `legacy-pending` so the dashboard/API can track it before migration.

### Laundryroom OTA Retry

- Retried `Laundryroom` (`10.10.10.102`, expected `esp32-240ac4fa383c`) ElegantOTA migration on 2026-06-21 at about 21:50 CDT.
- Precheck confirmed it was still serving legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`.
- Reused `data/firmware/0.1.2-filtered-telemetry/firmware.bin` with MD5 `9071f35fb2984b23d05ab371a4192d48`.
- Authenticated multipart upload returned HTTP `200 OK` with body `OK`; this is different from the earlier `OTA could not begin` failure.
- Follow-up checks found the legacy HTTP endpoint no longer responding and neighbor discovery showing `10.10.10.102` as incomplete.
- No fresh MQTT status or telemetry arrived during two post-upload listen windows, and `/api/latest` still shows `Laundryroom` offline with no firmware version or last-seen timestamp.
- Updated the SQLite device status for `esp32-240ac4fa383c` to `ota-upload-ok-no-mqtt`.

### SunroomDoor OTA Attempt

- Tried migrating `SunroomDoor` (`10.10.10.109`, expected `esp32-240ac4fa393c`) on 2026-06-21 at about 21:55 CDT.
- Precheck confirmed it was still serving legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`; neighbor discovery still matched MAC `24:0a:c4:fa:39:3c`.
- Reused `data/firmware/0.1.2-filtered-telemetry/firmware.bin` with MD5 `9071f35fb2984b23d05ab371a4192d48`.
- Two authenticated multipart upload attempts reset the connection without returning `OK`.
- Follow-up checks showed `SunroomDoor` still serving legacy `Version 5.2.1`, still exposing authenticated `/update`, and not publishing MQTT as `esp32-240ac4fa393c`.
- Updated the SQLite device status for `esp32-240ac4fa393c` to `ota-upload-reset`.

### End-of-Day Handoff for 2026-06-22

- Final dashboard/API state before stopping: 10 devices are online on `0.1.2-filtered-telemetry`: `Den`, `FrontBedroom`, `Garage`, `GarageDriveay`, `LaundryroomAC`, `Office`, `Porch`, `Sunroom Test`, `WallBehindWH`, and `WaterHeater`.
- Offline mapped follow-up devices:
  - `Laundryroom` / `esp32-240ac4fa383c`: latest ElegantOTA upload returned `OK`, old HTTP disappeared, no MQTT yet; SQLite status `ota-upload-ok-no-mqtt`.
  - `SunroomDoor` / `esp32-240ac4fa393c`: two ElegantOTA uploads reset, old HTTP still serves `Version 5.2.1`, no MQTT; SQLite status `ota-upload-reset`.
  - `MasterBedroom` / unknown device ID: earlier upload returned HTTP `200 OK`, old HTTP disappeared, no MQTT.
  - `Lightpole` / `esp32-94b97ed52a78`: pre-mapped from MAC, currently not reachable/reporting.
- Tomorrow's first checks should be `/api/latest`, retained MQTT status/telemetry for the expected IDs, and direct HTTP probes for `10.10.10.102`, `10.10.10.109`, `10.10.10.104`, and `10.10.10.122`.
- Operational note for tomorrow: if a device accepted upload but has no MQTT, try physical power-cycle before another upload attempt; use USB recovery if it stays silent after power-cycle.

## 2026-06-24

### Device List Cleanup And Recovery

- Removed stale duplicate `Garage` device `esp32-240ac4ecafd8` from ignored local `config/locations.json` and from the live SQLite `devices` table. No historical readings existed for that ID. The remaining `Garage` device is `esp32-94b97ec7bcdc`.
- Added `Entryway` at `10.10.10.137`. Neighbor discovery resolved MAC `94:b9:7e:d5:4c:54`, so the expected local firmware device ID is `esp32-94b97ed54c54`.
- Uploaded `data/firmware/0.1.2-filtered-telemetry/firmware.bin` to `Entryway` through authenticated legacy `/update`; the upload returned HTTP `200 OK` with body `OK`.
- Published retained default config for `esp32-94b97ed54c54`. Follow-up live data now shows `Entryway` reporting telemetry on `0.1.2-filtered-telemetry`; the device still reports location `UNMAPPED`, and the dashboard maps it to `Entryway` through `config/locations.json`.
- Retried `Lightpole` at `10.10.10.122` using the same firmware artifact and MD5 `9071f35fb2984b23d05ab371a4192d48`; authenticated `/update` returned HTTP `200 OK` with body `OK`.
- Published retained default config for `esp32-94b97ed52a78`. Follow-up live data shows `Lightpole` online on `0.1.2-filtered-telemetry`, but as of the latest check it had status only and no DHT telemetry payload yet.
- Removed stale `AtticChimney` device `esp32-240ac4f9019c` from ignored local `config/locations.json` and from the live SQLite `devices` table. No historical readings existed for that ID.
- Live SQLite/API state now shows `Laundryroom`, `MasterBedroom`, and `SunroomDoor` reporting on `0.1.2-filtered-telemetry`; those are no longer offline recovery blockers.
- Corrected the local display spelling from `GarageDriveay` to `GarageDriveway` in `config/locations.json`, the live SQLite device row, and current documentation.
- Marked `Lightpole` as parked for manual physical inspection tomorrow. Check DHT22 VCC, GND, DATA pin, pull-up, and configured GPIO before resuming software-side follow-up.
- Expanded the OTA hardening backlog into concrete bad URL, bad SHA-256, interrupted download, and oversized image test cases.

### Lightpole ESP32 Replacement

- Identified the new USB-connected ESP32 MAC as `0c:b8:15:c2:8a:c8`, so its local firmware device ID is `esp32-0cb815c28ac8`.
- USB-flashed `0.1.2-filtered-telemetry` to the replacement board on `/dev/ttyUSB0`.
- Replaced the local `Lightpole` mapping from retired `esp32-94b97ed52a78` to `esp32-0cb815c28ac8`.
- Published retained default config for `esp32-0cb815c28ac8`: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Verified retained MQTT status: `esp32-0cb815c28ac8` is online on firmware `0.1.2-filtered-telemetry`.
- Serial monitor verified the board received and applied the retained config. While bench-connected over USB, it repeatedly read implausible `265.8F` / `99.9%` DHT values, which firmware filtered. Validate normal DHT telemetry after installing it on the verified lightpole wiring.
- Removed the retired `esp32-94b97ed52a78` row from live SQLite, set the replacement row to `Lightpole`, and cleared retained MQTT status/config/telemetry for the retired ID.
- After replacing the DHT22 sensor and rebooting the ESP32, `Lightpole` published valid telemetry: `85.3F`, `51.7%`, RSSI `-43`, status `OK`, sequence `2` at `2026-06-24T16:59:21Z`. The dashboard API maps the row to `Lightpole`.
- Moved `Lightpole` to its outside location and restored `Sunroom Test` as the USB-connected bench target. `esptool` confirmed `/dev/ttyUSB0` is MAC `9c:9c:1f:da:36:70`, device ID `esp32-9c9c1fda3670`. Use this device for code updates and new feature testing before fleet deployment.
- Added an approximate dashboard house diagram using the current known locations, with live temperature and humidity values placed in each zone. Added follow-up work to replace it with an uploaded house image and configurable sensor overlays. Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py` and tested the new page/API on temporary port `8002`; normal port `8000` needs a reboot or service restart to pick up the code.
- Refined the house diagram labels so humidity and last-seen sit on the line below location/temp, removed the per-room box outline, and changed `BunkHouse` from exterior/detached to an interior grandkids room.
- Updated the dashboard history graph into a selectable temperature graph with 6h, 12h, 24h, 48h, and 7-day ranges plus per-device toggles. History rows now use the configured location mapping, and the SQLite readings table has a created-at index plus a larger bounded history limit for longer chart ranges.
- Adjusted the dashboard house diagram placement: moved `Garage` and `GarageDriveway` to the right side, and moved `Lightpole` to the top row immediately right of `Porch`. Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py`.
- Published the dashboard graph, diagram placement, and memory updates to GitHub as draft PR #1 (`https://github.com/luminerdy/IoT/pull/1`) through the GitHub connector. Local `git push` remains blocked by missing HTTPS/SSH credentials on the Pi.

## 2026-06-26

### Temperature Graph Grouping

- Updated the dashboard Temperature Graph selector from one flat list of per-device toggles to three grouped sections with group-level `All` checkboxes and individual device checkboxes.
- Group membership is currently hard-coded in `app/iot_home/dashboard.py`:
  - `Outside`: `Porch`, `Lightpole`, `GarageDriveway`.
  - `Separate`: `Garage`, `WaterHeater`, `WallBehindWH`, `LaundryroomAC`.
  - `Inside`: all other reporting locations not in `Outside` or `Separate`.
- Preserved the existing graph behavior: new devices are selected by default, individual device toggles still work, and the selected readings count updates from the chosen devices.
- Added responsive styling so the three group panels sit side by side on desktop and stack on narrower screens.
- Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py`.
- Tested the updated dashboard on temporary port `8002` with live SQLite data and headless Chromium screenshots. The review server is currently running at `http://10.10.10.123:8002`.
- Attempted to restart `iot-home-dashboard.service` so the normal port `8000` would load the new code, but systemd required interactive authentication. Port `8000` may still show the older dashboard until the service is restarted manually or the Pi reboots.
- Confirmed the Pi rebooted at `2026-06-25 22:12:45 CDT`; `iot-home-dashboard.service` started at `2026-06-25 22:12:57 CDT` and normal port `8000` now serves the grouped Temperature Graph code.
- Live dashboard/API smoke test on port `8000` showed 18 mapped devices. The recovered follow-up devices `Laundryroom`, `Lightpole`, `MasterBedroom`, `SunroomDoor`, and `Entryway` were online with fresh telemetry and had readings in the last hour. `GarageDriveway` initially appeared stale, then reported again by the final check at `2026-06-26T18:23:13Z`.

### Humidity Quality Flagging

- Accepted the operating assumption that outdoor DHT22 humidity readings are approximate and can degrade over time.
- Added a dashboard-side suspect humidity flag for outdoor DHT22 locations when humidity is at or above `99%`.
- The current outdoor humidity flag applies to `Porch`, `Lightpole`, and `GarageDriveway`; live data flags `Porch` at `99.9%`, while current `Lightpole` and `GarageDriveway` readings are not flagged.
- Suspect humidity is excluded from the dashboard average humidity summary, while temperature and device status remain visible.
- Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py` and smoke-tested the modified dashboard on temporary port `8002`.
- Tried to restart `iot-home-dashboard.service` so normal port `8000` would load the suspect humidity flag, but systemd required interactive authentication. The change will load after a manual service restart or the planned reboot.

### USB Cable Check

- Plugged the retired old `Lightpole` ESP32 into the test cable to confirm the cable supports data.
- The Pi enumerated the board as a CP2102 serial bridge on `/dev/ttyUSB1`; the existing bench ESP32 remained on `/dev/ttyUSB0`.
- `esptool` connected to `/dev/ttyUSB1` and read MAC `94:b9:7e:d5:2a:78`, confirming the cable is data-capable.
- The probe/reset briefly caused retained MQTT/status and SQLite rows for retired device `esp32-94b97ed52a78`; cleared retained MQTT state and removed the transient SQLite row. Final API check showed `unmapped_count=0`.

### OTA Failure-Path Testing

- Tested the bad OTA URL failure path against USB-recoverable `Sunroom Test` / `esp32-9c9c1fda3670`.
- Published rollout `20260626T153900Z-bad-url-test` with a missing firmware URL: `http://piserver.local:8000/firmware/bad-url-test/missing.bin`.
- Observed OTA status progression on `home/sensors/esp32-9c9c1fda3670/ota/status`: `downloading` with message `ota download started`, then `failed` with message `firmware download failed`.
- Verified the retained status still reports firmware `0.1.2-filtered-telemetry`; the retained online timestamp did not refresh, so there was no indication of a reboot during the bad URL test.
- Tested the bad SHA-256 failure path against `Sunroom Test` using the valid staged firmware URL and an intentionally wrong SHA-256.
- First bad-SHA command used a version string longer than the firmware's 31-character field and was rejected as `invalid ota command`; reran with shorter version `bad-sha-test`.
- Published rollout `20260626T190800Z-bad-sha` with URL `http://10.10.10.123:8000/firmware/0.1.2-filtered-telemetry/firmware.bin`, size `825200`, and SHA-256 set to all `f` characters.
- Observed OTA status progression: `downloading` with message `ota download started`, then `rejected` with message `firmware sha256 mismatch`.
- Verified retained status still reports firmware `0.1.2-filtered-telemetry`; retained online timestamp did not refresh. Latest telemetry after the earlier bad-SHA attempt still had high uptime and `restartReason` set to `PowerOn`, so there was no indication of a reboot.
- Tested the interrupted download failure path against `Sunroom Test` using a temporary HTTP server on port `8003`.
- The temporary server advertised the full firmware `Content-Length` of `825200` bytes but sent only `65536` bytes before closing the connection. Server logs confirmed the ESP32 at `10.10.10.124` requested the interrupted firmware URL.
- Published rollout `20260626T191300Z-interrupted` with URL `http://10.10.10.123:8003/firmware-interrupted.bin`, the correct full SHA-256, and expected size `825200`.
- Observed OTA status progression: `downloading` with message `ota download started`, then `failed` with message `firmware length mismatch`.
- Stopped the temporary port `8003` server after the test. Retained status still reported firmware `0.1.2-filtered-telemetry`, and the dashboard still showed `Sunroom Test` online and not stale.
- Tested the oversized image failure path against `Sunroom Test` using a temporary HTTP server on port `8003`.
- The temporary server advertised `Content-Length: 2000000`, larger than the OTA partition capacity, and sent a small placeholder body. Server logs confirmed the ESP32 at `10.10.10.124` requested the oversized firmware URL.
- Published rollout `20260626T203800Z-oversized` with URL `http://10.10.10.123:8003/firmware-oversized.bin`, expected size `2000000`, and a placeholder SHA-256.
- Observed OTA status progression: `downloading` with message `ota download started`, then `failed` with message `ota partition unavailable`.
- Stopped the temporary port `8003` server after the test. Retained status still reported firmware `0.1.2-filtered-telemetry`, and the dashboard still showed `Sunroom Test` online and not stale.
- Added decision record `DR-015` accepting the OTA failure-path safety validation for the local OTA MVP, while leaving firmware signing, rollback workflow, and richer rollout controls as Phase 5 hardening work.
- Updated the implementation plan and current status so OTA failure-path testing is marked complete and new ESP32 provisioning is listed as an upcoming task.
- Added decision record `DR-016` accepting outdoor DHT22 humidity as advisory and documenting the dashboard suspect-humidity threshold.

## Ready Next

- After the planned reboot, verify port `8000` loads the suspect humidity flag and no retired `Lightpole` / `UNMAPPED` row is present.
- Provision the remaining new ESP32 devices when they arrive.
- Confirm newly recovered devices stay stable across a few 10-minute telemetry intervals.
- Confirm replacement `Lightpole` remains stable across a few 10-minute telemetry intervals.

## 2026-06-27

### Studio ESP32 Provisioned

- Detected a new ESP32 on `/dev/ttyUSB1`; existing bench `Sunroom Test` remained on `/dev/ttyUSB0`.
- Read MAC `70:4b:ca:48:02:20`, so the local device ID is `esp32-704bca480220`.
- USB-flashed firmware `0.1.2-filtered-telemetry` to `/dev/ttyUSB1`.
- Published retained default config: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Verified MQTT status, config response, and telemetry:
  - status: `online`
  - firmware: `0.1.2-filtered-telemetry`
  - config response: `applied`
  - telemetry: `78.6F`, `48.9%`, RSSI `-46`, status `OK`
- Mapped `esp32-704bca480220` to `Studio` in local `config/locations.json` and updated the current SQLite device/reading rows.
- Added `Studio` to the dashboard house diagram between `FrontBedroom` and `Entryway`.
- Verified `http://127.0.0.1:8000/api/latest` shows `Studio` online and `UNMAPPED` count is `0`.

### UnderAC ESP32 Provisioned

- Detected a new ESP32 on `/dev/ttyUSB1`; existing bench `Sunroom Test` remained on `/dev/ttyUSB0`.
- Read MAC `a4:f0:0f:75:f3:58`, so the local device ID is `esp32-a4f00f75f358`.
- USB-flashed firmware `0.1.2-filtered-telemetry` to `/dev/ttyUSB1`.
- Published retained default config: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Verified MQTT status, retained config, and telemetry:
  - status: `online`
  - firmware: `0.1.2-filtered-telemetry`
  - telemetry: `76.6F`, `54.4%`, RSSI `-45`, status `OK`
- Mapped `esp32-a4f00f75f358` to `UnderAC` in local `config/locations.json` and updated the current SQLite device/reading rows.
- Added `UnderAC` to the dashboard house diagram between `FrontBedroom` and `BunkHouse`.
- Added `UnderAC` to the dashboard Temperature Graph `Separate` group with other non-room/equipment readings.

### Wrap-Up Notes

- Decision: classify `UnderAC` as a `Separate` graph location because it is an equipment/utility reading rather than a normal room-comfort trend.
- Observation: both new boards were provisioned successfully over the same data-capable USB cable on `/dev/ttyUSB1`; `Sunroom Test` remained the bench device on `/dev/ttyUSB0`.
- Issue: `iot-home-dashboard.service` still cannot be restarted from this session because `systemctl`/`sudo` requires interactive authentication, so the new floorplan code should be verified after reboot.

### GitHub SSH and Dashboard Verification

- Created and configured a dedicated GitHub SSH key at `/home/scotty/.ssh/id_ed25519_github`.
- Switched the local repo remote to `git@github.com:luminerdy/IoT.git`.
- Added a repo-local `core.sshCommand` so Git bypasses the broken system SSH config symlink at `/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf`.
- Verified GitHub accepts the key as `luminerdy`.
- Reconciled the local `codex/dashboard-graph-diagram-memory` branch with its remote duplicate-history branch using a merge commit that keeps the local tree canonical.
- Pushed the reconciled branch to GitHub; `HEAD` and `origin/codex/dashboard-graph-diagram-memory` are now in sync at merge commit `ad87d94`.
- Verified normal port `8000` serves the suspect humidity flag and includes `Studio` and `UnderAC` in the house diagram floorplan.
- Verified live device state shows 20 mapped devices online, no `UNMAPPED` rows, and no retired `esp32-94b97ed52a78` row.
- Confirmed recovered-device telemetry is still arriving for `Laundryroom`, `Lightpole`, `MasterBedroom`, `SunroomDoor`, and `Entryway`.

### Ready Next

- New ESP32 provisioning is complete for the current batch: `Studio` and `UnderAC`.
- Continue watching recovered devices across a few 10-minute telemetry intervals.
- Start the next dashboard improvement: replace the approximate house diagram with an uploaded house image and configurable sensor placement overlays.
