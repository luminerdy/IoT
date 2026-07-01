# Implementation Plan

Use this file for planned work, phase status, and acceptance criteria. Move completed work into `docs/progress-log.md`. Record durable architecture choices in `docs/decision-record.md`.

## Current Roadmap

Active phase: Phase 5, fleet operations and daily-use dashboard.

Phases 0 through 4 are complete for the current local-first system. Remaining work is operational maturity: finishing signed OTA rollout, improving dashboard maintenance workflows, backing up data, and hardening MQTT access without disrupting the installed fleet.

## Phase 0: Project Setup

Status: Complete.

Goal: Establish the local project, documentation, source tracking, and implementation direction.

Completed:

- Created local project documentation.
- Initialized local git tracking and connected the public GitHub repository.
- Defined MQTT topic and payload schema.
- Added `docs/current-status.md` for fast restart/context-switch recovery.
- Chose a pragmatic Pi dependency approach: system services plus project-local Python/PlatformIO tooling where useful.
- Sanitized public docs and samples so local secrets and identifiable runtime data stay out of the tracked tree.

Acceptance criteria:

- Repo has enough documentation to resume work after a pause. Done.
- Public repo excludes local secrets and runtime files. Done.
- Architecture direction is recorded. Done.

## Phase 1: Local Data Path MVP

Status: Complete.

Goal: Prove Pi-side broker, collector, database, and dashboard with simulated devices.

Completed:

- Installed/configured Mosquitto on the Pi.
- Created a simulated ESP32 MQTT publisher.
- Created SQLite schema and helper code.
- Created collector service to subscribe to MQTT and store readings.
- Created dashboard showing latest readings per room/device.
- Added stale/offline detection.
- Installed collector and dashboard as systemd services.
- Verified services are active and enabled.

Acceptance criteria:

- Simulated devices publish telemetry to local MQTT. Done.
- Collector persists readings. Done.
- Dashboard updates without full page reload. Done.
- Dashboard shows stale/offline state. Done.
- Broker, collector, and dashboard start at boot through systemd. Done.

## Phase 2: ESP32 Firmware MVP

Status: Complete.

Goal: Replace simulated telemetry with real ESP32 sensor nodes.

Completed:

- Resolved USB visibility and serial access for connected ESP32 devices.
- Installed PlatformIO and `esptool` on the Pi.
- Created PlatformIO firmware project.
- Implemented WiFi connection.
- Implemented local MQTT connection with username/password support.
- Implemented DHT22 reads, validation, and filtered telemetry publishing.
- Published telemetry, retained online/offline status, firmware version, RSSI, uptime, error counters, and restart reason.
- Configured production Mosquitto LAN listener.
- Added Pi-side location mapping.
- Migrated the installed fleet from the legacy OTA firmware where OTA was accepted.

Acceptance criteria:

- Real ESP32 devices publish valid telemetry to production Mosquitto. Done.
- Dashboard displays real sensor readings. Done.
- Devices reconnect after normal service/network interruptions. Done enough for current operations; continue observing as part of Phase 5.

## Phase 3: Runtime Configuration

Status: Complete.

Goal: Allow runtime config without reflashing.

Completed:

- Added retained per-device config topic.
- ESP32 firmware subscribes to config.
- Validates and applies `reportIntervalSeconds`.
- Validates and applies `changeThresholdF`.
- Reports active config in telemetry and config responses.
- Added Pi-side config publisher.
- Published retained default runtime config for migrated devices.

Acceptance criteria:

- Report interval can be changed from the Pi. Done.
- Temperature change threshold can be changed from the Pi. Done.
- Invalid config is rejected and reported without changing active config. Done.

## Phase 4: Local OTA And Firmware Safety

Status: Complete for the current system.

Goal: Update ESP32 devices over the local network from the Pi with a tested recovery path.

Completed:

- Confirmed OTA partition support in the default ESP32 partition table.
- Served firmware binaries and manifests from the Pi.
- Added MQTT OTA command handling.
- Downloaded firmware over HTTP from the Pi.
- Verified SHA-256 before applying firmware.
- Added P-256 ECDSA signed OTA verification for firmware `0.1.3-signed-ota`.
- Wrote OTA partition, finalized update, and rebooted successfully.
- Published OTA status over MQTT.
- Added CLI rollout helper.
- Tested successful OTA on the USB-recoverable bench device.
- Tested successful OTA on canary/fleet devices.
- Tested bad URL, bad SHA-256, interrupted download, oversized image, and bad signature failure paths on the bench device.

Acceptance criteria:

- USB-connected bench ESP32 can be updated OTA. Done.
- At least one non-bench device can be updated OTA. Done.
- Failed update does not break the USB recovery path. Done.
- Firmware authorization is enforced by signature, not only by checksum. Done.

Phase 4 residuals moved to Phase 5/backlog:

- Continue fleet-wide signed OTA rollout in small batches.
- Add richer rollout controls if manual CLI rollout becomes tedious.
- Decide whether firmware version should remain a PlatformIO build flag or move to release metadata.

## Phase 5: Fleet Operations And Daily Dashboard

Status: In progress.

Goal: Make the system boring to operate: all sensors visible, recoverable, backed up, and easy to maintain from the Pi.

Priority 1: Fleet Stability

- Continue signed OTA rollout in small batches until the installed fleet is on `0.1.3-signed-ota` or newer.
- Keep the USB bench device reserved for firmware and feature validation before fleet rollout.
- Watch recovered/replaced devices across normal 10-minute report intervals.
- Keep retained MQTT state, SQLite device rows, and `config/locations.json` clean when devices are removed, replaced, or renamed.
- Add a simple operator checklist for adding/replacing a sensor.

Priority 2: Dashboard As The Daily Control Surface

- Rotate the main dashboard content through four operator views every 5 seconds: House Diagram, Device List Grid, Temperature Graph, and Latest Readings. Done; active on normal port `8000`.
- Upload the actual floorplan image under `data/dashboard-assets/`.
- Set `backgroundImage` in local `config/floorplan.json`.
- Tune local sensor overlay placement without committing private floorplan data.
- Add a dashboard admin view for device/location mapping.
- Make graph grouping configurable if hard-coded groups become limiting.
- Keep suspect humidity flagging visible but non-disruptive.

Priority 3: Operations And Data Protection

- Add SQLite backup/export workflow. Initial local backup script and S3-ready runbook are in place.
- Add restore verification for at least one backup.
- Add a compact operational runbook covering service status, logs, OTA rollout, config publish, and sensor replacement.
- Decide how much local runtime state should stay JSON files versus moving to SQLite tables.

Priority 4: Security Hardening Without Fleet Disruption

- Keep signed OTA required for new firmware.
- Stage MQTT TLS and per-device ACL migration on the bench device first.
- Add per-device credentials only after bench validation.
- Decide whether the public GitHub history needs a full rewrite or whether the current sanitized tip is sufficient.

Acceptance criteria:

- Dashboard shows all expected devices with current readings and clear online/stale/offline state.
- All active fleet devices are on signed OTA firmware.
- Device mappings can be maintained on the Pi without source edits.
- Floorplan placement can be maintained locally without committing private data.
- OTA rollout can be paused, retried, and verified.
- SQLite data is backed up and restorable.
- Services recover after reboot.

## Phase 6: Optional Productization

Status: Not started.

Goal: Only start this if the local system grows beyond personal operations.

Candidate work:

- Replace the dependency-free dashboard server with FastAPI/HTMX or another fuller stack if forms, auth, or admin workflows outgrow the current server.
- Add dashboard login/auth if exposed beyond the trusted LAN.
- Add richer OTA rollout UI.
- Add alerting for stale devices, sensor failures, and suspect humidity.
- Add automated GitHub CI once the workflow is worth maintaining.
