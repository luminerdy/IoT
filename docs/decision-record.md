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

**Status:** Accepted, blocked on USB visibility

