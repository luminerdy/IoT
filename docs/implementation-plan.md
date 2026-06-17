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

Status: Core MVP complete; service installation deferred.

Goal: Prove Pi-side broker, collector, database, and dashboard with simulated devices.

Tasks:

- Install/configure Mosquitto on the Pi. Done.
- Create a simulated ESP32 MQTT publisher. Done.
- Create SQLite schema. Done.
- Create collector service to subscribe to MQTT and store readings. Done.
- Create dashboard showing latest readings per room/device. Done.
- Add stale/offline detection. Done.

Acceptance criteria:

- Simulated devices publish telemetry to local MQTT. Done.
- Collector persists readings. Done.
- Dashboard updates without full page reload. Done.
- Dashboard shows stale/offline state. Done.

## Phase 2: ESP32 Firmware MVP

Status: First real ESP32 telemetry verified; operational hardening pending.

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
- Add Pi-side location mapping.

Acceptance criteria:

- ESP32 publishes valid telemetry to production Mosquitto. Done.
- Dashboard displays the real ESP32 reading. Pending final dashboard check after service setup.
- Device reconnects after broker restart or WiFi interruption. Partially verified by reconnecting to restarted test broker.

## Phase 3: Configuration

Goal: Allow runtime config without reflashing.

Tasks:

- Add retained per-device config topic.
- ESP32 subscribes to config.
- Validate and apply report interval.
- Report active config in telemetry or status.

Acceptance criteria:

- Report interval can be changed from the Pi.
- Invalid config is rejected and reported.

## Phase 4: Local OTA

Goal: Update ESP32 devices over the air from the Pi.

Tasks:

- Add OTA partitions to firmware build.
- Serve firmware binaries and manifest from the Pi.
- Add MQTT OTA command handling.
- Download firmware over HTTP from Pi.
- Verify SHA-256.
- Write OTA partition and reboot.
- Report OTA status over MQTT.
- Add dashboard or CLI rollout control.

Acceptance criteria:

- USB-connected test ESP32 can be updated OTA.
- One canary device can be updated OTA.
- Failed update does not break USB recovery path.

## Phase 5: Fleet Operations

Goal: Make the system reliable for all room sensors.

Tasks:

- Add batch rollout control.
- Add rollback workflow.
- Add dashboard admin view for device/location mapping.
- Add backup/export for SQLite.
- Add systemd services for broker, collector, dashboard, and OTA coordinator.
- Add basic operational runbook.

Acceptance criteria:

- All devices can be monitored from the dashboard.
- Device mappings can be maintained on the Pi.
- OTA rollout can be paused and retried.
- Services restart after reboot.
