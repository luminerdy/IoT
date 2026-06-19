# Current Status

Last updated: 2026-06-19

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is moving from an AWS-oriented ESP32 design to a local-first Raspberry Pi system with MQTT, SQLite, a dashboard, and future local OTA.

## Current Phase

Phase 4: Local OTA

Status: OTA MVP code is implemented and the OTA-capable firmware is USB-flashed; first live OTA rollout is pending a dashboard service restart so `/firmware/...` is served on port `8000`.

## Accomplished

- Reviewed existing project notes, current ESP32 code, sample AWS IoT payloads, and previous requirements.
- Chose local-first architecture with the Raspberry Pi as MQTT broker, collector, SQLite host, dashboard host, and future OTA coordinator.
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
- Cleared retained simulator MQTT messages and removed historical simulator rows from SQLite; dashboard now shows only the physical ESP32.
- Added OTA command handling to firmware and USB-flashed the OTA-capable build.
- Added Pi-side OTA artifact staging and MQTT command publishing.
- Added dashboard firmware file serving under `/firmware/...`; verified with a temporary dashboard on port `8001`.

## Active Blockers

- Normal local `git push` from this Pi is still unavailable because local GitHub HTTPS/SSH credentials are not configured.
- Restarting `iot-home-dashboard.service` requires an interactive sudo password, so the running service has not picked up `/firmware/...` file serving yet.

## Next Actions

1. Restart `iot-home-dashboard.service` locally so `/firmware/...` works on port `8000`.
2. Verify `curl -I http://127.0.0.1:8000/firmware/0.1.0-ota-mvp/firmware.bin` returns `200`.
3. Run one live OTA update on the USB-recoverable ESP32 using `docs/phase-4-runbook.md`.
4. After live OTA works, add rollback/failure-path testing and consider firmware signing.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: FastAPI/HTMX is recommended but not yet locked.
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
- Remote status: sanitized source tree is published to GitHub through the GitHub connector; normal local `git push` still needs credentials on this Pi.
- Local-only ignored files include runtime data, build output, `config/locations.json`, and `firmware/include/secrets.h`.
- Services: `iot-home-collector.service`, `iot-home-dashboard.service`, and `mosquitto.service` are enabled and running.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://piserver.local:8000` or `http://<pi-ip-address>:8000`.
- Staged OTA artifact for first live test: `data/firmware/0.1.0-ota-mvp/firmware.bin`; ignored by git because runtime/build artifacts stay local.
