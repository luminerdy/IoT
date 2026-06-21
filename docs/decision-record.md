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

**Status:** Accepted and validated on `10.10.10.113`, now `esp32-0cb815c288f4`
