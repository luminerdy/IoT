# Implementation Plan

Use this file for planned work, phase status, and acceptance criteria. Move completed work into `docs/progress-log.md`. Record durable architecture choices in `docs/decision-record.md`.

## Phase 0: Project Setup

Status: In progress

- Create local project documentation. Done.
- Initialize local git tracking. Done.
- Define MQTT topics and message schema. Draft done.
- Add quick current-status documentation. Done.
- Decide install approach for Pi dependencies.

Current next step:

- Start Phase 1 with simulated devices, unless ESP32 USB visibility becomes the immediate priority.

## Phase 1: Local Data Path MVP

Status: Complete.

Goal: Prove Pi-side broker, collector, database, and dashboard with simulated devices.

Tasks:

- Install/configure Mosquitto on the Pi. Done.
- Create a simulated ESP32 MQTT publisher. Done.
- Create SQLite schema. Done.
- Create collector service to subscribe to MQTT and store readings. Done.
- Create dashboard showing latest readings per room/device. Done.
- Add stale/offline detection. Done.
- Install collector and dashboard as systemd services. Done.

Acceptance criteria:

- Simulated devices publish telemetry to local MQTT. Done.
- Collector persists readings. Done.
- Dashboard updates without full page reload. Done.
- Dashboard shows stale/offline state. Done.
- Collector and dashboard restart after reboot through systemd. Service enablement done; reboot verification pending.

## Phase 2: ESP32 Firmware MVP

Status: Complete for the first real ESP32; broader fleet hardening pending.

Goal: Replace simulated telemetry with a real ESP32.

Tasks:

- Resolve USB visibility for connected ESP32. Done.
- Install PlatformIO and `esptool` on the Pi or define another build host. Done.
- Create PlatformIO firmware project. Done.
- Implement WiFi connection. Done.
- Implement local MQTT connection. Done.
- Implement DHT22 reads and validation. Done.
- Publish telemetry and status messages. Done.
- Include firmware version, RSSI, uptime, and error counters. Done.
- Configure production Mosquitto LAN listener or systemd-managed test broker. Done.
- Add Pi-side location mapping. Done.

Acceptance criteria:

- ESP32 publishes valid telemetry to production Mosquitto. Done.
- Dashboard displays the real ESP32 reading. Done.
- Device reconnects after broker restart or WiFi interruption. Partially verified by reconnecting to restarted test broker.

Operational follow-up:

- Clear old retained simulator MQTT messages if the dashboard should only show physical devices.

## Phase 3: Configuration

Status: Complete.

Goal: Allow runtime config without reflashing.

Tasks:

- Add retained per-device config topic. Done.
- ESP32 subscribes to config. Done.
- Validate and apply report interval. Done.
- Validate and apply temperature change threshold. Done.
- Report active config in telemetry or response. Done.
- Add Pi-side config publisher. Done.

Acceptance criteria:

- Report interval can be changed from the Pi. Done.
- Invalid config is rejected and reported. Done.

## Phase 4: Local OTA

Status: Signed OTA validated on the bench device; staged fleet rollout in progress.

Goal: Update ESP32 devices over the air from the Pi.

Tasks:

- Add OTA partitions to firmware build. Done; default ESP32 partition table already has `ota_0` and `ota_1`.
- Serve firmware binaries and manifest from the Pi. Done.
- Add MQTT OTA command handling. Done.
- Download firmware over HTTP from Pi. Done.
- Verify SHA-256. Done.
- Verify P-256 ECDSA firmware signature. Done for `0.1.3-signed-ota`.
- Write OTA partition and reboot. Done.
- Report OTA status over MQTT. Done.
- Add dashboard or CLI rollout control. CLI helper started.

Acceptance criteria:

- USB-connected test ESP32 can be updated OTA. Done.
- One canary device can be updated OTA. Done.
- Failed update does not break USB recovery path.

Hardening follow-up:

- Test bad URL, bad SHA-256, interrupted download, oversized image, and bad signature failure paths. Done on USB-recoverable `Sunroom Test`.
- Decide whether firmware version should remain a PlatformIO build flag or move to a single release metadata source.

## Phase 5: Fleet Operations

Status: In progress.

Goal: Make the system reliable for all room sensors.

Tasks:

- Improve the Raspberry Pi-hosted web dashboard as the main IoT data view.
- Add a dashboard house image upload and sensor placement overlay so readings can be positioned on the actual home image. Configurable overlay support is done; actual image upload/selection is pending.
- Keep the Temperature Graph useful for daily monitoring with grouped and individual device selection. Initial grouping done.
- Flag suspect outdoor DHT22 humidity in the dashboard. Initial `>=99%` outdoor DHT22 rule done.
- Add batch rollout control.
- Add rollback workflow.
- Add dashboard admin view for device/location mapping.
- Add backup/export for SQLite.
- Add systemd services for broker, collector, dashboard, and OTA coordinator.
- Add basic operational runbook.

Ready next for 2026-06-27:

- Confirm newly recovered devices remain stable across a few 10-minute telemetry intervals: `Laundryroom`, `Lightpole`, `MasterBedroom`, `SunroomDoor`, and `Entryway`.
- Keep `config/locations.json` and SQLite placeholders clean when devices are removed or renamed.
- Upload the actual house image under `data/dashboard-assets/`, set `backgroundImage` in `config/floorplan.json`, and tune the configurable temperature/humidity placement overlay.
- Continue signed OTA rollout in small batches after the first indoor soak remains stable.

Acceptance criteria:

- All devices can be monitored from the dashboard.
- Current new ESP32 batch is provisioned: `Studio` / `esp32-704bca480220` and `UnderAC` / `esp32-a4f00f75f358`.
- Dashboard is reachable from the Pi and LAN and shows current readings, online/stale/offline state, useful recent history, and grouped temperature graph selection.
- Floorplan sensor placement can be maintained through local JSON without editing dashboard JavaScript.
- Device mappings can be maintained on the Pi.
- OTA rollout can be paused and retried.
- Services restart after reboot.

## Near-Term Dashboard Work

Target date: 2026-06-21

Goal: turn the current basic table into a useful Raspberry Pi web dashboard for daily IoT monitoring.

Tasks:

- Verify the dashboard service is reachable at `http://127.0.0.1:8000` on the Pi and `http://piserver.local:8000` on the LAN. Done on the Pi for port `8000`; LAN URL remains available through the same service binding.
- Keep the current latest-reading table, but improve layout for phone and desktop use.
- Add at-a-glance cards for temperature, humidity, online/stale/offline state, RSSI, last seen, and firmware version.
- Add a recent history view or simple chart from SQLite readings. Done; Temperature Graph supports range selection plus grouped and individual device toggles.
- Add clear empty/error states if MQTT data or SQLite data is missing.
- Decide whether to keep the current standard-library HTTP server or move the dashboard to a fuller web stack.

## OTA Hardening Backlog

- Test bad OTA URL failure path: publish an OTA command with a reachable rollout ID but an invalid firmware URL; verify `ota/status` reports failure and the device keeps running the current firmware. Done for `Sunroom Test` with rollout `20260626T153900Z-bad-url-test`.
- Test bad SHA-256 failure path: publish an OTA command with a valid firmware URL and intentionally wrong SHA-256; verify download completes, validation fails, and no reboot occurs. Done for `Sunroom Test` with rollout `20260626T190800Z-bad-sha`.
- Test interrupted download failure path: serve a truncated firmware response or stop the HTTP server during download; verify the device reports failure and keeps running. Done for `Sunroom Test` with rollout `20260626T191300Z-interrupted`.
- Test oversized image failure path: publish or serve an image larger than the available OTA partition; verify OTA write fails cleanly and no reboot occurs. Done for `Sunroom Test` with rollout `20260626T203800Z-oversized`.
- Record expected `home/sensors/{deviceId}/ota/status` messages for each failure mode in `docs/mqtt-schema.md` or the Phase 4 runbook. Done in the Phase 4 runbook.
- Decide whether firmware version should remain a PlatformIO build flag or move to a single release metadata source.
- Continue signed OTA fleet rollout after bench validation and first indoor soak.
