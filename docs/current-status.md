# Current Status

Last updated: 2026-06-26

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is a local-first Raspberry Pi IoT system with MQTT, SQLite, a boot-enabled web dashboard, runtime MQTT config, filtered ESP32 telemetry, and local OTA.

## Current Phase

Phase 5: Fleet operations plus daily dashboard improvements

Status: The local OTA firmware is deployed broadly. OTA failure-path hardening is validated on the USB-recoverable bench device. The dashboard service is enabled at boot and serves live device cards, summary metrics, latest readings, a grouped selectable temperature graph from SQLite, and an approximate house diagram.

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
- Replaced `Lightpole` with the USB-flashed ESP32 `esp32-0cb815c28ac8`; after replacing the DHT22 sensor it reports valid telemetry.
- Restored `Sunroom Test` (`esp32-9c9c1fda3670`) as the USB-connected bench device for firmware changes and feature testing before fleet deployment.
- Added a first-pass dashboard house diagram using approximate zones from the known sensor locations; the diagram was tested on temporary port `8002`.
- Updated the dashboard graph to support selectable 6h, 12h, 24h, 48h, and 7-day temperature ranges with grouped and per-device toggles.
- Adjusted the house diagram placements so `Garage` and `GarageDriveway` sit on the right side and `Lightpole` sits on the top row just right of `Porch`.
- Grouped the Temperature Graph device selector into `Inside`, `Outside`, and `Separate` sections. `Outside` is intentionally limited to `Porch`, `Lightpole`, and `GarageDriveway`; `Separate` contains `Garage`, `WaterHeater`, `WallBehindWH`, `LaundryroomAC`, and `UnderAC`; all remaining reporting locations are grouped as `Inside`.
- Confirmed after the 2026-06-25 evening reboot that normal port `8000` serves the grouped Temperature Graph code.
- Completed the first OTA failure-path test: a bad firmware URL against USB-recoverable `Sunroom Test` produced `downloading` then `failed` OTA statuses without changing firmware.
- Completed the bad SHA-256 OTA failure-path test: a valid firmware URL with an intentionally wrong SHA produced `downloading` then `rejected` / `firmware sha256 mismatch` without changing firmware.
- Completed the interrupted-download OTA failure-path test: a temporary server sent only `65536` of `825200` bytes and the device reported `downloading` then `failed` / `firmware length mismatch` without changing firmware.
- Completed the oversized-image OTA failure-path test: a temporary server advertised `2000000` bytes and the device reported `downloading` then `failed` / `ota partition unavailable` without changing firmware.
- Added a dashboard-side suspect humidity flag for outdoor DHT22 locations at or above `99%`; live data currently flags `Porch`.

## Live Dashboard State

Latest SQLite/API check on 2026-06-27 shows 20 mapped devices on `0.1.2-filtered-telemetry`:

- `BunkHouse` / `esp32-9c9c1fc5ce0c`: online, telemetry OK.
- `Den` / `esp32-3c71bf642440`: online, telemetry OK.
- `Entryway` / `esp32-94b97ed54c54`: online, telemetry OK. The device reports `UNMAPPED`, but the dashboard maps it through `config/locations.json`.
- `FrontBedroom` / `esp32-9c9c1fdd632c`: online, telemetry OK.
- `Garage` / `esp32-94b97ec7bcdc`: online, telemetry OK.
- `GarageDriveway` / `esp32-0cb815c288f4`: online, telemetry OK. It briefly appeared stale during testing, then reported again by the final API check.
- `Kitchen` / `esp32-9c9c1fdd67ec`: online, telemetry OK.
- `Laundryroom` / `esp32-240ac4fa383c`: online, telemetry OK.
- `LaundryroomAC` / `esp32-4022d8ee4904`: online, telemetry OK.
- `Lightpole` / `esp32-0cb815c28ac8`: online, telemetry OK.
- `MasterBedroom` / `esp32-240ac4fa4290`: online, telemetry OK.
- `Office` / `esp32-240ac4f8fecc`: online, telemetry OK.
- `Porch` / `esp32-240ac4f8f574`: online, temperature telemetry OK; humidity is suspect because the outdoor DHT22 is pegging near `99.9%`.
- `Sunroom` / `esp32-9c9c1fdd65d0`: online, telemetry OK.
- `Sunroom Test` / `esp32-9c9c1fda3670`: online, telemetry OK.
- `SunroomDoor` / `esp32-240ac4fa393c`: online, telemetry OK.
- `Studio` / `esp32-704bca480220`: online, telemetry OK.
- `UnderAC` / `esp32-a4f00f75f358`: online, telemetry OK.
- `WallBehindWH` / `esp32-240ac4fa418c`: online, telemetry OK.
- `WaterHeater` / `esp32-9c9c1fc5cf1c`: online, telemetry OK.

## Active Blockers

- GitHub CLI `gh` is not installed, so GitHub Actions log inspection and some PR workflows still need the connector or local `git`.

## Next Actions

1. Provision the remaining new ESP32 devices when they arrive: plug in one at a time, flash firmware, record MAC/device ID, publish retained defaults, and map each location. `Studio` and `UnderAC` are done.
2. Confirm the newly recovered devices stay stable across a few 10-minute report intervals: `Laundryroom`, `Lightpole`, `MasterBedroom`, `SunroomDoor`, and `Entryway`.
3. Use `Sunroom Test` (`esp32-9c9c1fda3670`) on `/dev/ttyUSB0` for firmware and feature validation before deploying to other devices.
4. Replace the approximate dashboard house diagram with an uploaded house image and configurable sensor placement overlays.
5. Decide whether to add firmware signing now that OTA failure-path tests are documented.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: current dependency-free Python HTTP server is working; FastAPI/HTMX can still be revisited if routes/forms grow.
- Pi dependency install approach: direct system packages vs isolated app environment.
- OTA signing: current MVP uses SHA-256 validation only.
- Temperature Graph grouping: current grouping is hard-coded in `app/iot_home/dashboard.py`; revisit if group membership needs to become user-configurable.
- Outdoor DHT22 humidity flagging: current suspect threshold is `>=99%` for `Porch`, `Lightpole`, and `GarageDriveway`; revisit if other sensor models or outdoor locations are added.

## Where Details Live

- Accomplishments and dated work history: `docs/progress-log.md`
- Phase plan and task backlog: `docs/implementation-plan.md`
- Architecture decisions: `docs/decision-record.md`
- Hardware findings and checks: `docs/hardware-notes.md`
- MQTT topics and payloads: `docs/mqtt-schema.md`
- Overall architecture: `Local-First-Architecture.md`

## Stop Point

- Local branch: `codex/dashboard-graph-diagram-memory`
- Latest local commit: run `git log -1 --oneline`.
- Public GitHub repo: `luminerdy/IoT`
- Draft PR: `https://github.com/luminerdy/IoT/pull/1`
- GitHub SSH push from the Pi works through `/home/scotty/.ssh/id_ed25519_github`; the working branch is synced to `origin/codex/dashboard-graph-diagram-memory`.
- Local-only ignored files include runtime data, build output, `config/locations.json`, and `firmware/include/secrets.h`.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://piserver.local:8000` or `http://<pi-ip-address>:8000`.
- Dashboard app: summary metrics, approximate house diagram, device cards, latest readings, and `/api/history` trend data are in `app/iot_home/dashboard.py`. The diagram uses two-line room labels with location/temp above humidity/last-seen, no per-room box outline, treats `BunkHouse` as an interior grandkids room, places `Studio` between `FrontBedroom` and `Entryway`, and places `UnderAC` between `FrontBedroom` and `BunkHouse`. The Temperature Graph selector is grouped into `Inside`, `Outside`, and `Separate`, with both group-level `All` checkboxes and individual device checkboxes. Outdoor DHT22 humidity at or above `99%` is flagged as suspect and excluded from average humidity.
- Dashboard verification: normal port `8000` serves the suspect humidity flag plus the `Studio` and `UnderAC` floorplan placements. Latest live check showed 20 mapped devices, no `UNMAPPED` rows, and no retired `esp32-94b97ed52a78` row.
- Telemetry policy memory: ESP32s should read DHT22 frequently, reject impossible values and one-off large jumps, publish median-filtered temp/humidity every 600 seconds, and only publish early when filtered temperature differs by the configured threshold for 3 consecutive valid samples. Humidity is reported but does not trigger early publishes.
- Latest live-tested OTA artifact: `data/firmware/0.1.2-filtered-telemetry/firmware.bin`; ignored by git because runtime/build artifacts stay local.
