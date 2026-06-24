# Current Status

Last updated: 2026-06-24

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is a local-first Raspberry Pi IoT system with MQTT, SQLite, a boot-enabled web dashboard, runtime MQTT config, filtered ESP32 telemetry, and local OTA.

## Current Phase

Phase 4: Local OTA plus daily dashboard improvements

Status: The local OTA firmware is deployed broadly. The dashboard service is enabled at boot and serves live device cards, summary metrics, latest readings, and a 24-hour trend from SQLite.

## Accomplished

- Chose and documented the local-first architecture with the Raspberry Pi as MQTT broker, collector, SQLite host, dashboard host, and OTA coordinator.
- Removed AWS IoT and OLED/display requirements from the core ESP32 sensor-node architecture.
- Built the local MQTT/SQLite collector, dashboard, Pi-side location mapping, runtime retained MQTT config, and local OTA path.
- Installed and enabled `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service`.
- Built and deployed firmware version `0.1.2-filtered-telemetry`.
- Migrated the ESP32 fleet from the old ElegantOTA firmware to the local MQTT firmware where OTA was accepted.
- Published retained default runtime config for migrated devices: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Removed stale local placeholders for `Garage` duplicate `esp32-240ac4ecafd8` and `AtticChimney` `esp32-240ac4f9019c`.
- Added `Entryway` from `10.10.10.137` as expected device ID `esp32-94b97ed54c54`; it is now reporting telemetry.
- Retried `Lightpole` at `10.10.10.122`; it accepted upload and now reports firmware status as `esp32-94b97ed52a78`.

## Live Dashboard State

Latest SQLite/API check on 2026-06-24 shows these devices on `0.1.2-filtered-telemetry`:

- `BunkHouse` / `esp32-9c9c1fc5ce0c`: online, telemetry OK.
- `Den` / `esp32-3c71bf642440`: online, telemetry OK.
- `Entryway` / `esp32-94b97ed54c54`: online, telemetry OK. The device reports `UNMAPPED`, but the dashboard maps it through `config/locations.json`.
- `FrontBedroom` / `esp32-9c9c1fdd632c`: online, telemetry OK.
- `Garage` / `esp32-94b97ec7bcdc`: online, telemetry OK.
- `GarageDriveway` / `esp32-0cb815c288f4`: online, telemetry OK.
- `Kitchen` / `esp32-9c9c1fdd67ec`: online, telemetry OK.
- `Laundryroom` / `esp32-240ac4fa383c`: online, telemetry OK.
- `LaundryroomAC` / `esp32-4022d8ee4904`: online, telemetry OK.
- `Lightpole` / `esp32-94b97ed52a78`: manual physical follow-up pending; it reported firmware status but no DHT telemetry.
- `MasterBedroom` / `esp32-240ac4fa4290`: online, telemetry OK.
- `Office` / `esp32-240ac4f8fecc`: online, telemetry OK.
- `Porch` / `esp32-240ac4f8f574`: online, telemetry OK.
- `Sunroom` / `esp32-9c9c1fdd65d0`: online, telemetry OK.
- `Sunroom Test` / `esp32-9c9c1fda3670`: online, telemetry OK.
- `SunroomDoor` / `esp32-240ac4fa393c`: online, telemetry OK.
- `WallBehindWH` / `esp32-240ac4fa418c`: online, telemetry OK.
- `WaterHeater` / `esp32-9c9c1fc5cf1c`: online, telemetry OK.

## Active Blockers

- Normal local `git push` from this Pi is still unavailable because local GitHub HTTPS/SSH credentials are not configured.
- Latest local changes are not pushed to GitHub because HTTPS push needs a username/token and SSH push is denied by missing public-key auth.

## Next Actions

1. Lightpole is parked for manual physical inspection tomorrow; check DHT22 VCC, GND, DATA pin, pull-up, and configured GPIO before resuming software checks.
2. Confirm the newly recovered devices stay stable across a few 10-minute report intervals: `Laundryroom`, `MasterBedroom`, `SunroomDoor`, and `Entryway`.
3. Add OTA rollback/failure-path tests for bad URL, bad SHA-256, interrupted download, and oversized image cases.
4. Consider firmware signing after the failure-path tests are documented.
5. Configure GitHub push credentials or SSH key on the Pi.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: current dependency-free Python HTTP server is working; FastAPI/HTMX can still be revisited if routes/forms grow.
- Pi dependency install approach: direct system packages vs isolated app environment.
- OTA signing: current MVP uses SHA-256 validation only.

## Where Details Live

- Accomplishments and dated work history: `docs/progress-log.md`
- Phase plan and task backlog: `docs/implementation-plan.md`
- Architecture decisions: `docs/decision-record.md`
- Hardware findings and checks: `docs/hardware-notes.md`
- MQTT topics and payloads: `docs/mqtt-schema.md`
- Overall architecture: `Local-First-Architecture.md`

## Stop Point

- Local branch: `main`
- Latest local commit: run `git log --oneline -1` in `/home/scotty/IoT`
- Public GitHub repo: `luminerdy/IoT`
- Local-only ignored files include runtime data, build output, `config/locations.json`, and `firmware/include/secrets.h`.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://piserver.local:8000` or `http://<pi-ip-address>:8000`.
- Dashboard app: summary metrics, device cards, latest readings, and `/api/history` 24-hour trend data are live on the boot-enabled dashboard service.
- Telemetry policy memory: ESP32s should read DHT22 frequently, reject impossible values and one-off large jumps, publish median-filtered temp/humidity every 600 seconds, and only publish early when filtered temperature differs by the configured threshold for 3 consecutive valid samples. Humidity is reported but does not trigger early publishes.
- Latest live-tested OTA artifact: `data/firmware/0.1.2-filtered-telemetry/firmware.bin`; ignored by git because runtime/build artifacts stay local.
