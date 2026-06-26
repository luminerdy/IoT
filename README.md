# Local IoT Home Monitoring

Local-first ESP32 temperature and humidity monitoring system.

## Project Direction

ESP32 devices collect room temperature and humidity readings and publish them over the home network to this Raspberry Pi (`PiServer`). The Pi runs the message bus, collector, database, dashboard, and local OTA update coordinator.

AWS IoT is no longer part of the core architecture.

## Repository Layout

```text
docs/                           Active project documentation
app/iot_home/                   Pi collector, dashboard, simulator, and helper CLIs
config/                         Sample local Pi configuration
deploy/systemd/                 Collector and dashboard service units
firmware/                       ESP32 PlatformIO firmware
scripts/                        Pi setup and maintenance helpers
Local-First-Architecture.md
```

## Current MVP Status

1. Local MQTT, SQLite collection, and dashboard are running on the Pi.
2. The first physical ESP32 publishes authenticated MQTT telemetry and appears in the dashboard as `Sunroom Test`.
3. Runtime config works through retained MQTT config messages.
4. Local OTA MVP is live-validated on the USB-recoverable ESP32.
5. OTA failure-path hardening is validated for bad URL, bad SHA-256, interrupted download, and oversized image cases.
6. Next work is new-device provisioning, dashboard house image placement, firmware signing/rollback decisions, and broader fleet operations.

## Documentation

- [Current Status](docs/current-status.md)
- [Local-First Architecture](Local-First-Architecture.md)
- [Phase 1 Runbook](docs/phase-1-runbook.md)
- [Phase 2 Runbook](docs/phase-2-runbook.md)
- [Phase 4 Runbook](docs/phase-4-runbook.md)
- [Progress Log](docs/progress-log.md)
- [Decision Record](docs/decision-record.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Hardware Notes](docs/hardware-notes.md)

## Documentation Flow

- Update `docs/current-status.md` when the active phase, blockers, or next actions change.
- Update `docs/progress-log.md` with dated accomplishments.
- Update `docs/implementation-plan.md` with planned work and phase status.
- Update `docs/decision-record.md` when an architecture or implementation decision is accepted.
