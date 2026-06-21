# Current Status

Last updated: 2026-06-21

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is a local-first Raspberry Pi IoT system with MQTT, SQLite, a boot-enabled web dashboard, runtime MQTT config, filtered ESP32 telemetry, and local OTA.

## Current Phase

Phase 4: Local OTA plus daily dashboard improvements

Status: OTA MVP is live-validated on the USB-recoverable ESP32, and the Raspberry Pi-hosted dashboard has been upgraded into the main daily IoT view. The dashboard service is enabled at boot and serves live device cards, summary metrics, latest readings, and a 24-hour trend from SQLite.

## Accomplished

- Reviewed existing project notes, current ESP32 code, sample AWS IoT payloads, and previous requirements.
- Chose local-first architecture with the Raspberry Pi as MQTT broker, collector, SQLite host, dashboard host, and OTA coordinator.
- Decided to keep ESP32 sensor nodes and DHT22 sensors.
- Removed AWS IoT from the core architecture.
- Removed local OLED/display requirements from ESP32 nodes.
- Decided the Pi owns room/location mapping.
- Drafted MQTT topics and payload schema.
- Created local project documentation and initialized git tracking.
- Checked the USB-connected ESP32 path. After changing USB cords, the ESP32 serial bridge is visible.
- Installed Mosquitto, Mosquitto CLI clients, Python MQTT bindings, and the SQLite CLI.
- Added simulated ESP32 MQTT publisher.
- Added SQLite schema and collector service.
- Added local dashboard with live browser-side polling and stale/offline state.
- Added Phase 1 runbook.
- Verified simulated MQTT telemetry flows into SQLite and is visible through the dashboard API.
- Installed `esptool` in the project virtual environment at `.venv/bin/esptool`.
- Verified ESP32 serial communication on `/dev/ttyUSB0`.
- Installed PlatformIO Core in the project virtual environment at `.venv/bin/pio`.
- Verified PlatformIO sees `/dev/ttyUSB0` as a CP2102 USB to UART Bridge Controller.
- Added PlatformIO firmware project under `firmware/`.
- Built and uploaded local MQTT firmware to the USB-connected ESP32.
- Verified real ESP32 telemetry reached SQLite through MQTT.
- Added project-local Mosquitto test broker config on port `1884`.
- Configured system Mosquitto for authenticated LAN access on port `1883`.
- Uploaded firmware configured for production MQTT credentials on port `1883`.
- Verified real ESP32 telemetry reaches SQLite through the production broker.
- Added Pi-side location mapping support with local ignored `config/locations.json`.
- Mapped `esp32-9c9c1fda3670` to `Sunroom Test` locally.
- Added systemd unit files and an install script for the collector and dashboard.
- Installed and enabled `iot-home-collector.service` and `iot-home-dashboard.service`.
- Verified the dashboard API shows the real ESP32 as `Sunroom Test` with a fresh online reading.
- Published the sanitized source tree to `luminerdy/IoT` through the GitHub connector.
- Added retained per-device runtime config handling for report interval and temperature change threshold.
- Added a Pi-side retained config publisher with explicit defaults and retained-delete modes.
- Verified retained config apply, telemetry active config reporting, invalid config rejection, and default restore on the real ESP32.
- Updated telemetry policy target to sample frequently, median-filter valid readings, reject implausible/outlier samples, publish every 10 minutes, and publish temperature-change events only after repeated confirmation.
- Updated existing ElegantOTA device at `10.10.10.113` over HTTP OTA to `0.1.2-filtered-telemetry`; it now reports as `esp32-0cb815c288f4` and is mapped locally to `GarageDriveay`.
- Cleared retained simulator MQTT messages and removed historical simulator rows from SQLite; dashboard now shows only the physical ESP32.
- Added OTA command handling to firmware and USB-flashed the OTA-capable build.
- Added Pi-side OTA artifact staging and MQTT command publishing.
- Added dashboard firmware file serving under `/firmware/...`; verified on the normal dashboard service on port `8000`.
- Ran the first live OTA rollout on `esp32-9c9c1fda3670`; the device reported `downloading`, then `rebooting`, then resumed telemetry after a software restart.
- Ran a second OTA rollout with `FIRMWARE_VERSION` set to `0.1.1-ota-version`; post-reboot MQTT status, telemetry, and dashboard API all report the new version.
- Upgraded the web dashboard with summary metrics, device cards, latest-reading table, and a 24-hour history API/trend view.
- Restarted `iot-home-dashboard.service`; verified it is enabled, active, listening on `0.0.0.0:8000`, and serving the updated app.

## Active Blockers

- Normal local `git push` from this Pi is still unavailable because local GitHub HTTPS/SSH credentials are not configured.
- Latest local changes are committed locally but not pushed to GitHub because HTTPS push needs a username/token and SSH push is denied by missing public-key auth.

## Next Actions

1. Add rollback/failure-path testing for bad URL, bad SHA-256, interrupted download, and oversized image cases.
2. Consider firmware signing after the failure-path tests are documented.
3. Decide whether dashboard history should stay as a lightweight inline SVG or move to a richer charting stack later.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: current dependency-free Python HTTP server is working; FastAPI/HTMX can still be revisited if routes/forms grow.
- Pi dependency install approach: direct system packages vs isolated app environment.
- OTA signing: current MVP uses SHA-256 validation only.

## Where Details Live

- Accomplishments and dated work history: `docs/progress-log.md`
- Phase plan and task backlog: `docs/implementation-plan.md`
- Architecture decisions: `docs/decision-record.md`
- Hardware findings and checks: `docs/hardware-notes.md`
- MQTT topics and payloads: `docs/mqtt-schema.md`
- Overall architecture: `Local-First-Architecture.md`

## Stop Point

- Local branch: `main`
- Latest local commit: run `git log --oneline -1` in `/home/scotty/IoT`
- Public GitHub repo: `luminerdy/IoT`
- Remote status: GitHub is behind the local commit. `git push origin main` fails because HTTPS credentials are missing, and SSH push fails because no GitHub public key is configured on this Pi.
- Local-only ignored files include runtime data, build output, `config/locations.json`, and `firmware/include/secrets.h`.
- Services: `iot-home-collector.service`, `iot-home-dashboard.service`, and `mosquitto.service` are enabled and running.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://piserver.local:8000` or `http://<pi-ip-address>:8000`.
- Dashboard app: summary metrics, device cards, latest readings, and `/api/history` 24-hour trend data are live on the boot-enabled dashboard service.
- Telemetry policy memory: ESP32s should read DHT22 frequently, reject impossible values and one-off large jumps, publish median-filtered temp/humidity every 600 seconds, and only publish early when filtered temperature differs by the configured threshold for 3 consecutive valid samples. Humidity is reported but does not trigger early publishes.
- Device mapping memory: `esp32-9c9c1fda3670` is `Sunroom Test`; `esp32-0cb815c288f4` is `GarageDriveay`.
- Reboot note: `app/iot_home/dashboard.py` now defaults stale-device detection to 1200 seconds to match the target 10-minute ESP32 report interval with headroom and reloads `config/locations.json` for `/api/latest`. The running dashboard service still needs a restart or reboot to load these code changes because `sudo systemctl restart iot-home-dashboard.service` requires an interactive password, but the current SQLite device row was updated so the live dashboard shows `GarageDriveay` now.
- After reboot, verify `http://127.0.0.1:8000/api/latest` shows both `Sunroom Test` and `GarageDriveay` online with firmware `0.1.2-filtered-telemetry`.
- Latest live-tested OTA artifact: `data/firmware/0.1.2-filtered-telemetry/firmware.bin`; ignored by git because runtime/build artifacts stay local.
