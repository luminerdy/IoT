# Local IoT Home Monitoring

Local-first ESP32 temperature and humidity monitoring system.

## Project Direction

ESP32 devices collect room temperature and humidity readings and publish them over the home network to this Raspberry Pi (`IoT Pi`). The Pi runs the message bus, collector, database, dashboard, and local OTA update coordinator.

AWS IoT is no longer part of the core architecture.

## Repository Layout

```text
specs/                         Source-of-truth product and engineering requirements
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
| Phase 5: Fleet Operations | In progress | The fleet has 23 mapped devices reporting on `0.1.4-antirollback`, including three attic sensors. The dashboard includes rotating operator views, live device cards, dedicated attic temperature history, suspect outdoor humidity flagging, configurable floorplan support, and a `Manage Devices` mapping panel. Local SQLite backups run before the daily restic/S3 backup. |

Current next work is operational rather than MVP build-out:

- Keep watching recently recovered devices during normal telemetry intervals.
- Use `Bench Device` as the USB bench device before firmware or feature rollout.
- Replace the approximate dashboard house diagram with an uploaded house image and configurable sensor placement overlays.
- Keep daily backup checks and periodic restore drills in the operating routine.

## Documentation

- [Specification Package](specs/README.md)
- [Current Status](docs/current-status.md)
- [Local-First Architecture](Local-First-Architecture.md)
- [Phase 1 Runbook](docs/phase-1-runbook.md)
- [Phase 2 Runbook](docs/phase-2-runbook.md)
- [Phase 4 Runbook](docs/phase-4-runbook.md)
- [Progress Log](docs/progress-log.md)
- [Decision Record](docs/decision-record.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Hardware Notes](docs/hardware-notes.md)
- [SQLite Backup Runbook](docs/backup-runbook.md)
- [Operations Runbook](docs/operations-runbook.md)

## Documentation Flow

- Treat `specs/` as the source of truth for what the rebuilt system must do. When implementation and specs disagree, update the relevant spec first or explicitly record why the implementation is intentionally diverging.
- Before making behavior, security, API, data, deployment, or test changes, review the relevant `specs/` files and update the requirement IDs, acceptance criteria, or testing strategy that should govern the change.
- Every PR or local change that alters externally observable behavior should update the relevant spec file, the relevant operational/user documentation, and the project status/change log.
- Update `docs/current-status.md` when the active phase, blockers, or next actions change.
- Update `docs/progress-log.md` with dated accomplishments.
- Update `docs/implementation-plan.md` with planned work and phase status.
- Update `docs/decision-record.md` when an architecture or implementation decision is accepted.
