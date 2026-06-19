# Local IoT Home Monitoring

Local-first ESP32 temperature and humidity monitoring system.

## Project Direction

ESP32 devices collect room temperature and humidity readings and publish them over the home network to this Raspberry Pi (`PiServer`). The Pi runs the message bus, collector, database, dashboard, and eventually the OTA update coordinator.

AWS IoT is no longer part of the core architecture.

## Repository Layout

```text
docs/                           Active project documentation
firmware/                       Future ESP32 PlatformIO firmware
dashboard/                      Future Pi dashboard and collector service
scripts/                        Future helper scripts
Local-First-Architecture.md
```

## Current MVP

1. Run a local MQTT broker on the Pi.
2. Build a Pi collector that reads MQTT telemetry and writes SQLite.
3. Build a local dashboard that shows current readings and stale/offline status.
4. Build ESP32 firmware that publishes local MQTT telemetry.
5. Add local OTA after the basic telemetry path is stable.

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
