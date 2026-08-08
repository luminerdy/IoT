# Implementation Plan

Use this file for planned work, phase status, and acceptance criteria. Move completed work into `docs/progress-log.md`. Record durable architecture choices in `docs/decision-record.md`.

## Current Roadmap

Active phase: Phase 5, fleet operations and daily-use dashboard.

Phases 0 through 4 are complete for the current local-first system. Remaining work is operational maturity: improving dashboard maintenance workflows, backing up data, and hardening MQTT access without disrupting the installed fleet.

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
- Added signed OTA anti-rollback with a monotonic build number for firmware `0.1.4-antirollback`.
- Wrote OTA partition, finalized update, and rebooted successfully.
- Published OTA status over MQTT.
- Added CLI rollout helper.
- Tested successful OTA on the USB-recoverable bench device.
- Tested successful OTA on canary/fleet devices.
- Tested bad URL, bad SHA-256, interrupted download, oversized image, and bad signature failure paths on the bench device.
- Tested signed build-number rollback rejection on the bench device.

Acceptance criteria:

- USB-connected bench ESP32 can be updated OTA. Done.
- At least one non-bench device can be updated OTA. Done.
- Failed update does not break the USB recovery path. Done.
- Firmware authorization is enforced by signature, not only by checksum. Done.

Phase 4 residuals moved to Phase 5/backlog:

- Continue future firmware rollouts in small batches.
- Add richer rollout controls if manual CLI rollout becomes tedious.
- Decide whether firmware version should remain a PlatformIO build flag or move to release metadata.

## Phase 5: Fleet Operations And Daily Dashboard

Status: In progress.

Goal: Make the system boring to operate: all sensors visible, recoverable, backed up, and easy to maintain from the Pi.

Priority 1: Fleet Stability

- Continue signed OTA rollout in small batches until the installed fleet is on `0.1.3-signed-ota` or newer. Done for the 21 mapped devices on 2026-07-01.
- Keep the USB bench device reserved for firmware and feature validation before fleet rollout. No firmware build may go to fleet devices until the exact build has passed bench ESP32 testing.
- Complete the `0.1.5-led-off` rollout only after resolving or explicitly isolating MasterBedroom's frequent MQTT reconnects and incomplete OTA download. Current state: 7 of 23 devices updated; all 23 online and non-stale; rollout paused.
- Require acknowledged `downloading → rebooting` OTA states and fresh target-version telemetry for every device before expanding a batch. Use the verified numeric Pi LAN address while ESP32 `.local` resolution remains unavailable.
- Watch recovered/replaced devices across normal 10-minute report intervals.
- Monitor the three attic sensors during the 2026-07-11 afternoon heat window. If `Attic` repeats the 2026-07-10 outage near the prior 137.5 F peak, inspect its power supply, regulator, wiring, and enclosure before considering firmware changes.
- Fix retained telemetry pollution by stopping retained telemetry publishes and/or deduping collector inserts on `(device_id, seq, datetime)`. Done for the 21 mapped devices with firmware `0.1.4-antirollback` and the live collector/database deployment on 2026-07-04.
- Use collector-side desired firmware version checking to record deployment
  attempts on version mismatch while keeping OTA publication operator-only.
  Done on 2026-08-07: `--auto-ota` was removed, the collector retains no
  command publisher path, and the admin-authenticated OTA CLI remains the
  distribution mechanism after bench validation.
- Keep retained MQTT config/status state, SQLite device rows, and `config/locations.json` clean when devices are removed, replaced, or renamed.
- Add a simple operator checklist for adding/replacing a sensor. Done in `docs/operations-runbook.md` on 2026-07-05.

Priority 2: Dashboard As The Daily Control Surface

- Rotate the main dashboard content through four operator views every 5 seconds: House Diagram, Device List Grid, Temperature Graph, and Latest Readings. Done; active on normal port `8000`.
- Upload the actual floorplan image under `data/dashboard-assets/`.
- Set `backgroundImage` in local `config/floorplan.json`.
- Tune local sensor overlay placement without committing private floorplan data.
- Add a dashboard admin view for device/location mapping. Done on 2026-07-08 with local-network-only writes to `config/locations.json`.
- Make graph grouping configurable if hard-coded groups become limiting.
- Keep the dedicated Attic group, alphabetical device-card order, hottest-first Latest Readings, and 75 F / 100 F graph references covered by the dashboard presentation contract test. Added on 2026-07-10.
- Keep suspect humidity flagging visible but non-disruptive.

Priority 3: Operations And Data Protection

- Add SQLite backup/export workflow. Done; the local SQLite backup runs daily at 02:05 before the 02:15 restic/S3 backup.
- Add restore verification for at least one backup. Done for both local SQLite backup and latest restic S3 snapshot; reverified on 2026-07-08.
- Add lossless scheduled database maintenance that verifies live and backup
  integrity, preserves row counts, runs `PRAGMA optimize`, and alerts on stale
  backups or storage thresholds. Done on 2026-08-07 with a daily systemd timer
  and focused tests.
- Replace ad hoc schema creation with numbered forward-only migrations and add
  the DATA-001 partial unique dedupe index. Done and live at schema version 2 on
  2026-08-07 with lossless production-backup and live comparisons. The
  concurrent-start race found during activation is fixed and tested in
  `cacfceb`; the collector was restarted with the fix and reverified.
- Add a compact operational runbook covering service status, logs, OTA rollout, config publish, and sensor replacement. Done in `docs/operations-runbook.md` on 2026-07-05.
- Decide how much local runtime state should stay JSON files versus moving to SQLite tables.

Priority 4: Security Hardening Without Fleet Disruption

- Keep signed OTA required for new firmware.
- Pin the PlatformIO `espressif32` platform and add `platformio run` to CI so firmware compilation is checked, not only static analysis. Done on 2026-07-03.
- Add MQTT ACL protection to the current port `1883` listener so shared credentials cannot publish fleet OTA/config commands. Done and live-activated on 2026-07-04.
- Add a first dashboard access-control layer before treating the LAN as a trusted boundary. Basic auth was implemented and live-tested on 2026-07-04, then intentionally removed the same day so trusted home-network clients can view the dashboard without credentials.
- Add signed OTA anti-rollback with a monotonic build number before the next feature firmware rollout. Done and rolled out to the 21 mapped devices on 2026-07-04.
- Stage MQTT TLS and per-device ACL migration on the bench device first. Done
  on 2026-08-07/08 with `0.1.9-nvs-tls` build `2026080707` and TEST-033.
- Add per-device credentials only after bench validation. Bench tooling is
  complete; production provisioning remains a separately approved incremental
  migration.
- Decide whether the public GitHub history needs a full rewrite or whether the current sanitized tip is sufficient.
- Keep existing public history without a rewrite and block new current-tree
  identifier residue with a hash-only baseline. Done in DR-021 on 2026-08-07.
- Expand Python coverage from the measured 52.6% baseline to the required 80%
  gate. Done on 2026-08-07: 114 tests measure 91.9% with branch coverage, and
  CI enforces an 80% floor.
- Add the TEST-023 broker ACL matrix. Done on 2026-08-07 against an isolated
  Mosquitto broker using the same tracked per-device ACL installed by the TLS
  setup script; no live broker configuration was changed.
- Extract firmware filter and publish-policy logic for native host tests. Done
  on 2026-08-07 with six passing PlatformIO native cases for TEST-010/011;
  ArduinoJson OTA parsing and nine TEST-012 manifest-validation cases are also
  complete. The combined 15-case native suite passes, and the exact ESP32
  candidate passed task-focused parser/preflight checks on the USB-connected
  Sunroom Test device. The complete TEST-030 release checklist remains required
  before any fleet rollout.

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
