# Decision Record

This file records project architecture decisions and the reasoning behind them.

## DR-001: Local-First Architecture

**Date:** 2026-06-16

**Decision:** Use the Raspberry Pi as the local MQTT broker, collector, database host, dashboard host, and future OTA coordinator.

**Reasoning:** The project does not need AWS IoT for normal operation. A local message bus reduces cloud dependency, simplifies the system, and keeps realtime dashboard data on the home network.

**Status:** Accepted

## DR-002: Keep ESP32 Sensor Nodes

**Date:** 2026-06-16

**Decision:** Continue using ESP32 devices for room sensors.

**Reasoning:** Existing hardware is already ESP32-based and suitable for WiFi, MQTT, OTA, and DHT22 sensor reads.

**Status:** Accepted

## DR-003: Remove ESP32 Local Displays

**Date:** 2026-06-16

**Decision:** Do not include OLED or other local displays on each ESP32.

**Reasoning:** The dashboard is the central display. Removing per-device displays simplifies firmware, wiring, power draw, enclosure needs, and failure modes.

**Status:** Accepted

## DR-004: Pi Owns Location Mapping

**Date:** 2026-06-16

**Decision:** Room/location mapping should live on the Pi, not in ESP32 firmware.

**Reasoning:** Room names and device placement can change without reflashing devices. ESP32 firmware should identify itself by stable device ID, while the Pi maps device IDs to human-readable locations.

**Status:** Accepted

## DR-005: Local OTA From Pi

**Date:** 2026-06-16

**Decision:** Implement OTA locally using MQTT commands and firmware binaries served by the Pi over HTTP.

**Reasoning:** The system still needs fleet updateability, but AWS IoT Jobs is unnecessary for a local home deployment. The Pi can coordinate staged rollouts, serve firmware, and track update status.

**Status:** Accepted for Phase 2

## DR-006: USB-Connected ESP32 as Test Target

**Date:** 2026-06-16

**Decision:** Use a USB-connected ESP32 on the Pi as a development and test device once visibility is resolved.

**Reasoning:** A local test device allows firmware smoke tests, serial logging, MQTT validation, and recovery flashing before OTA rollouts.

**Status:** Accepted, USB visibility resolved

## DR-007: Authenticated LAN MQTT

**Date:** 2026-06-17

**Decision:** Configure system Mosquitto for LAN access on port `1883` with username/password authentication.

**Reasoning:** ESP32 devices must reach the broker over WiFi, but anonymous LAN MQTT is unnecessary risk. Username/password authentication keeps the first local deployment simple while avoiding open anonymous publishing.

**Status:** Accepted

## DR-008: Public Repository Sanitization

**Date:** 2026-06-17

**Decision:** Publish only sanitized local-first project files to the public `luminerdy/IoT` repository.

**Reasoning:** Old reference files contained local credentials, local network details, and obsolete AWS-oriented material. The public repo should contain source, documentation, samples, and runbooks, while local secrets and runtime files remain ignored.

**Status:** Accepted

## DR-009: Retained MQTT Runtime Config

**Date:** 2026-06-19

**Decision:** Use retained per-device MQTT config messages on `home/sensors/{deviceId}/config` for runtime firmware settings.

**Reasoning:** Retained MQTT config gives each ESP32 the latest desired settings after reconnect without requiring a database lookup or reflashing. Devices validate supported fields, reject invalid values, and report the active config in responses and telemetry. Empty retained payloads delete broker state, so the Pi helper also supports publishing explicit defaults for offline-safe reset behavior.

**Status:** Accepted and validated on the real ESP32

## DR-010: OTA MVP Safety Boundary

**Date:** 2026-06-19

**Decision:** The first local OTA implementation will use MQTT commands, HTTP firmware downloads from the Pi dashboard, SHA-256 validation, and USB as the recovery path. Firmware signing and fleet rollout controls are deferred until the basic OTA path is proven.

**Reasoning:** The system is still local-only and has a USB-connected test ESP32 for recovery. SHA-256 validation catches corrupted or wrong binaries, while keeping the first OTA path small enough to test end to end. Signing should be added before exposing update controls beyond the trusted local network.

**Status:** Accepted and live-validated for OTA MVP

## DR-011: Filtered Telemetry Publishing

**Date:** 2026-06-21

**Decision:** ESP32 firmware should sample DHT22 readings frequently, filter raw readings locally, publish periodic telemetry every 600 seconds by default, and publish early temperature-change telemetry only after repeated confirmation.

**Reasoning:** Single DHT22 readings can move because of local air pockets, especially outdoors, and random way-off values should not drive MQTT/cloud-forwarded telemetry. A small rolling median plus outlier rejection keeps normal dashboard readings stable. Requiring 3 consecutive filtered samples above the configured temperature threshold avoids noisy early publishes while preserving the original cost-conscious 10-minute cadence if readings are later forwarded to AWS.

**Status:** Accepted and live-validated in `0.1.2-filtered-telemetry`

## DR-012: Existing Device Migration Through ElegantOTA

**Date:** 2026-06-21

**Decision:** Existing ESP32 devices that already expose ElegantOTA over trusted LAN HTTP can be migrated to the local-first firmware by uploading the tested `firmware.bin` through multipart `POST /update` with `MD5` and `firmware` fields.

**Reasoning:** Some installed devices predate the local MQTT/OTA command path but still provide authenticated HTTP OTA. Using their existing ElegantOTA updater avoids physical access and brings them onto the same MQTT telemetry, retained config, dashboard, and future local OTA path. Each migrated device must be verified through MQTT after upload, then mapped in `config/locations.json`.

**Status:** Accepted and validated on multiple legacy devices. Some legacy devices can still accept or reset uploads without subsequently reporting MQTT, so migration is not considered complete until verified through `/api/latest` or MQTT status/telemetry.

## DR-013: Recovery Path for Problem Legacy OTA Devices

**Date:** 2026-06-21

**Decision:** For legacy ElegantOTA devices that reset connections, stop serving HTTP, or fail to report MQTT after upload, do not keep blindly retrying the same HTTP upload. Verify MQTT and HTTP state first, then power-cycle the device, and use USB recovery if it remains unreachable or silent.

**Reasoning:** `UtilityF` accepted an ElegantOTA upload and then stopped serving legacy HTTP without reporting MQTT. `RoomJ` reset two upload attempts and stayed on legacy firmware. Repeating the same upload can obscure the actual failure mode and risks leaving the device in an uncertain state. A controlled recovery ladder preserves evidence and gives the best chance of recovering the device without unnecessary writes.

**Status:** Accepted as operational guidance. The specific devices that originally triggered this decision later reported or were retried, but the recovery ladder still applies to future legacy OTA failures.

## DR-014: Hard-Coded Temperature Graph Groups

**Date:** 2026-06-26

**Decision:** Keep the Temperature Graph selector groups hard-coded in `app/iot_home/dashboard.py` for now, with `Outside` limited to `OutdoorA`, `OutdoorB`, and `OutdoorC`; `Separate` containing `UtilityA`, `UtilityB`, `UtilityC`, `UtilityD`, and `UtilityE`; and all remaining locations treated as `Inside`.

**Reasoning:** The group list is small, stable enough for the current dashboard, and directly supports the daily monitoring workflow without adding a location taxonomy editor or another config format. The Pi already owns device-to-location mapping, so future work can move graph grouping into `locations.json`, SQLite, or dashboard admin controls if group membership starts changing often.

**Status:** Accepted for the current dashboard implementation; updated on 2026-06-27 to classify `UtilityE` with the other separate/equipment readings. Revisit when location/device mapping becomes editable from the dashboard.

## DR-015: OTA Failure-Path Safety Validation

**Date:** 2026-06-26

**Decision:** Treat the current local OTA MVP failure handling as validated for bad URL, bad SHA-256, interrupted download, and oversized image cases on the USB-recoverable bench ESP32.

**Reasoning:** Each failure mode was tested against `Bench Device` / `esp32-device-id` while it remained recoverable over USB. The device published clear terminal OTA statuses and stayed on firmware `0.1.2-filtered-telemetry`: bad URL produced `failed` / `firmware download failed`; bad SHA-256 produced `rejected` / `firmware sha256 mismatch`; interrupted download produced `failed` / `firmware length mismatch`; oversized image produced `failed` / `ota partition unavailable`. Retained status and dashboard checks showed no firmware change, no stale device state, and no reboot indication during the tested failures.

**Status:** Accepted for the local OTA MVP. Firmware signing, rollback workflow, and richer rollout controls remain Phase 5 hardening work before broad unattended fleet rollout.

## DR-016: Outdoor DHT22 Humidity Is Advisory

**Date:** 2026-06-26

**Decision:** Treat outdoor DHT22 humidity readings as advisory, and flag outdoor DHT22 humidity at or above `99%` as suspect in the dashboard.

**Reasoning:** Outdoor DHT22 humidity sensing degrades over time and is not very accurate even when healthy. The OutdoorA sensor is currently pegging near `99.9%`, which is more useful as a sensor-health signal than as an exact humidity measurement. Temperature can still be useful when stable, so the dashboard should flag suspect humidity without discarding the device or hiding its temperature.

**Status:** Accepted for the current dashboard. The rule is intentionally conservative and currently applies to outdoor DHT22 locations: `OutdoorA`, `OutdoorB`, and `OutdoorC`.

## DR-017: Signed OTA Before Fleet-Wide Security Rollout

**Date:** 2026-06-27

**Decision:** Require P-256 ECDSA signatures on OTA firmware commands starting with firmware `0.1.3-signed-ota`, while keeping MQTT TLS and per-device ACL migration opt-in until each device is tested.

**Reasoning:** SHA-256 alone proves a downloaded binary matches the OTA command, but it does not prove the binary was authorized by the local owner. A firmware signature closes that gap. MQTT TLS and ACLs are added as deployable hardening steps, but enabling them across the fleet requires per-device credential provisioning and bench validation first.

**Status:** Accepted after testing on `Bench Device` / `esp32-device-id`: USB flash succeeded, signed OTA was accepted and rebooted, and a deliberately altered signature was rejected as `firmware signature invalid`.
