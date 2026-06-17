# Current Status

Last updated: 2026-06-16

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is moving from an AWS-oriented ESP32 design to a local-first Raspberry Pi system with MQTT, SQLite, a dashboard, and future local OTA.

## Current Phase

Phase 2: ESP32 firmware MVP

Status: Real ESP32 publishes through authenticated production Mosquitto; always-on collector/dashboard service setup still pending.

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

## Active Blockers

- Always-on collector/dashboard/broker services are not installed yet.

## Next Actions

1. Add Pi-side location mapping for `esp32-9c9c1fda3670`.
2. Install collector and dashboard as systemd services.
3. Run the dashboard against the real ESP32 reading.
4. Decide the next firmware feature: retained config handling or OTA foundation.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: FastAPI/HTMX is recommended but not yet locked.
- Pi dependency install approach: direct system packages vs isolated app environment.

## Where Details Live

- Accomplishments and dated work history: `docs/progress-log.md`
- Phase plan and task backlog: `docs/implementation-plan.md`
- Architecture decisions: `docs/decision-record.md`
- Hardware findings and checks: `docs/hardware-notes.md`
- MQTT topics and payloads: `docs/mqtt-schema.md`
- Overall architecture: `Local-First-Architecture.md`
