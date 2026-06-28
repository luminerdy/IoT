# Local IoT Home Monitoring

Local-first ESP32 temperature and humidity monitoring system.

## Project Direction

ESP32 devices collect room temperature and humidity readings and publish them over the home network to this Raspberry Pi (`IoT Pi`). The Pi runs the message bus, collector, database, dashboard, and local OTA update coordinator.

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

## Current Status

The original four implementation phases are done. The project is now in Phase 5: fleet operations and daily dashboard improvements.

| Phase | Status | Result |
| --- | --- | --- |
| Phase 1: Local Data Path MVP | Complete | Mosquitto, SQLite collection, and the local dashboard run on the Pi. |
| Phase 2: ESP32 Firmware MVP | Complete | ESP32 devices publish authenticated local MQTT telemetry with DHT22 readings and health fields. |
| Phase 3: Runtime Configuration | Complete | Devices accept retained MQTT config for report interval and temperature-change threshold. |
| Phase 4: Local OTA | Complete and hardened | OTA updates work locally; bad URL, bad SHA-256, interrupted download, and oversized image failures were validated on the USB-recoverable bench device. |
| Phase 5: Fleet Operations | In progress | The fleet is broadly migrated to `0.1.2-filtered-telemetry`, 20 mapped devices are reporting, and the dashboard now includes live device cards, grouped temperature history, suspect outdoor humidity flagging, and an approximate house diagram. |

Current next work is operational rather than MVP build-out:

- Continue watching recovered devices across several 10-minute telemetry intervals.
- Use `Bench Device` as the USB bench device before firmware or feature rollout.
- Replace the approximate dashboard house diagram with an uploaded house image and configurable sensor placement overlays.
- Continue signed OTA rollout in small batches before broader unattended fleet updates.

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
