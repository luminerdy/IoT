# Current Status

Last updated: 2026-06-28

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is a local-first Raspberry Pi IoT system with MQTT, SQLite, a boot-enabled web dashboard, runtime MQTT config, filtered ESP32 telemetry, and local OTA.

## Current Phase

Phase 5: Fleet operations plus daily dashboard improvements

Status: Phases 0 through 4 are complete for the current local-first system. Signed OTA hardening is validated on the USB-recoverable bench device and the first three-device indoor soak batch remains healthy. The active work is Phase 5: fleet operations, dashboard maintenance workflows, backups, and staged security hardening.

## Accomplished

- Chose and documented the local-first architecture with the Raspberry Pi as MQTT broker, collector, SQLite host, dashboard host, and OTA coordinator.
- Removed AWS IoT and OLED/display requirements from the core ESP32 sensor-node architecture.
- Built the local MQTT/SQLite collector, dashboard, Pi-side location mapping, runtime retained MQTT config, and local OTA path.
- Installed and enabled `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service`.
- Built and deployed firmware version `0.1.2-filtered-telemetry`.
- Migrated the ESP32 fleet from the old ElegantOTA firmware to the local MQTT firmware where OTA was accepted.
- Published retained default runtime config for migrated devices: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Removed stale local placeholders for `UtilityA` duplicate `esp32-device-id` and `RetiredLocation` `esp32-device-id`.
- Added `RoomC` from `<private-ip>` as expected device ID `esp32-device-id`; it is now reporting telemetry.
- Replaced `OutdoorB` with the USB-flashed ESP32 `esp32-device-id`; after replacing the DHT22 sensor it reports valid telemetry.
- Restored `Bench Device` (`esp32-device-id`) as the USB-connected bench device for firmware changes and feature testing before fleet deployment.
- Added a first-pass dashboard house diagram using approximate zones from the known sensor locations; the diagram was tested on temporary port `8002`.
- Updated the dashboard graph to support selectable 6h, 12h, 24h, 48h, and 7-day temperature ranges with grouped and per-device toggles.
- Adjusted the house diagram placements so `UtilityA` and `OutdoorC` sit on the right side and `OutdoorB` sits on the top row just right of `OutdoorA`.
- Grouped the Temperature Graph device selector into `Inside`, `Outside`, and `Separate` sections. `Outside` is intentionally limited to `OutdoorA`, `OutdoorB`, and `OutdoorC`; `Separate` contains `UtilityA`, `UtilityB`, `UtilityC`, `UtilityD`, and `UtilityE`; all remaining reporting locations are grouped as `Inside`.
- Confirmed after the 2026-06-25 evening reboot that normal port `8000` serves the grouped Temperature Graph code.
- Completed the first OTA failure-path test: a bad firmware URL against USB-recoverable `Bench Device` produced `downloading` then `failed` OTA statuses without changing firmware.
- Completed the bad SHA-256 OTA failure-path test: a valid firmware URL with an intentionally wrong SHA produced `downloading` then `rejected` / `firmware sha256 mismatch` without changing firmware.
- Completed the interrupted-download OTA failure-path test: a temporary server sent only `65536` of `825200` bytes and the device reported `downloading` then `failed` / `firmware length mismatch` without changing firmware.
- Completed the oversized-image OTA failure-path test: a temporary server advertised `2000000` bytes and the device reported `downloading` then `failed` / `ota partition unavailable` without changing firmware.
- Added a dashboard-side suspect humidity flag for outdoor DHT22 locations at or above `99%`; live data currently flags `OutdoorA`.
- Confirmed on 2026-06-27 that Git SSH fetch works from the Pi and the local checkout is synced with `origin/main`.
- Confirmed on 2026-06-27 that `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are active and enabled.
- Confirmed on 2026-06-27 that `Bench Device` is visible as the USB bench device on `/dev/ttyUSB0`.
- Added configurable dashboard floorplan support with `/api/floorplan`, ignored local `config/floorplan.json`, tracked `config/floorplan.sample.json`, and optional image assets served from `/dashboard-assets/...`.
- Restarted the boot-enabled dashboard service on 2026-06-27 with the new floorplan config and asset directory arguments.
- Added signed OTA verification and tested it on `Bench Device` only. The device reports `0.1.3-signed-ota`; a signed OTA was accepted, and an intentionally bad signature was rejected.
- Added optional MQTT TLS and ACL scripts for staged migration. They are not yet enabled across the installed fleet.
- Started the first small indoor signed-OTA soak batch on 2026-06-27: `RoomE`, `RoomF`, and `RoomA` updated to `0.1.3-signed-ota` and came back online/non-stale immediately after OTA.
- Installed GitHub CLI locally under `/home/scotty/.local/bin/gh`; GitHub CLI API auth still requires `gh auth login` if terminal-based PR/check workflows are needed.
- Sanitized the tracked public branch tip to remove local private IPs, MAC-shaped addresses, real ESP32 IDs, Pi hostname references, and real room/location labels. Older public git history still contains local identifiers but no passwords or private key material were found by the scan.
- Updated the dashboard to rotate through four full-screen-style views every 5 seconds: House Diagram, Device List Grid, Temperature Graph, and Latest Readings. The summary/header remain visible, while the main content switches views.
- Hardened dashboard stale detection so the API can use collector receipt time when a device publishes telemetry with a bad startup/NTP timestamp.
- Continued the signed OTA rollout with three additional indoor devices; the signed OTA count is now 7 devices.

## Live Dashboard State

Latest SQLite/API check on 2026-06-28 shows 20 mapped devices online and 0 stale on normal dashboard port `8000`. Seven devices are now on `0.1.3-signed-ota`; the remaining installed fleet is on `0.1.2-filtered-telemetry` unless listed otherwise. One signed-OTA device briefly reported telemetry with `1970-01-01T00:00:00Z` after startup/NTP delay; the dashboard stale calculation now uses collector receipt time when available and was verified live on port `8000` after the Pi reboot.

- `RoomG` / `esp32-device-id`: online, telemetry OK.
- `RoomE` / `esp32-device-id`: online, telemetry OK on signed OTA.
- `RoomC` / `esp32-device-id`: online, telemetry OK. The device reports `UNMAPPED`, but the dashboard maps it through `config/locations.json`.
- `RoomA` / `esp32-device-id`: online, telemetry OK on signed OTA.
- `UtilityA` / `esp32-device-id`: online, telemetry OK.
- `OutdoorC` / `esp32-device-id`: online, telemetry OK. It briefly appeared stale during testing, then reported again by the final API check.
- `RoomF` / `esp32-device-id`: online, telemetry OK on signed OTA.
- `UtilityF` / `esp32-device-id`: online, telemetry OK.
- `UtilityD` / `esp32-device-id`: online, telemetry OK.
- `OutdoorB` / `esp32-device-id`: online, telemetry OK.
- `RoomH` / `esp32-device-id`: online, telemetry OK.
- `RoomD` / `esp32-device-id`: online, telemetry OK.
- `OutdoorA` / `esp32-device-id`: online, temperature telemetry OK; humidity is suspect because the outdoor DHT22 is now reporting implausibly low humidity after previously pegging high.
- `RoomI` / `esp32-device-id`: online, telemetry OK.
- `Bench Device` / `esp32-device-id`: online, telemetry OK on signed OTA.
- `RoomJ` / `esp32-device-id`: online, telemetry OK.
- `RoomB` / `esp32-device-id`: online, telemetry OK.
- `UtilityE` / `esp32-device-id`: online, telemetry OK.
- `UtilityC` / `esp32-device-id`: online, telemetry OK.
- `UtilityB` / `esp32-device-id`: online, telemetry OK.

## Active Blockers

- The actual house image has not been uploaded yet. The dashboard is ready for it through `data/dashboard-assets/` plus `config/floorplan.json`.
- GitHub CLI is installed but not authenticated. Run `gh auth login` before terminal-based PR/check workflows.
- The four-view rotating dashboard is active on normal port `8000`, and the collector-receipt-time stale calculation is loaded after the Pi reboot.

## Next Actions

1. Watch the seven signed-OTA devices through the next normal telemetry intervals, then continue rollout in small batches.
2. Keep `Bench Device` (`esp32-device-id`) on `/dev/ttyUSB0` for firmware and feature validation before deploying to other devices.
3. Upload the actual house image under `data/dashboard-assets/`, set `backgroundImage` in local `config/floorplan.json`, and tune the existing sensor placement overlay.
4. Add the Phase 5 operations basics: SQLite backup/export, a sensor replacement checklist, and a compact service/OTA runbook.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: current dependency-free Python HTTP server is working; FastAPI/HTMX can still be revisited if routes/forms grow.
- Pi dependency install approach: direct system packages vs isolated app environment.
- MQTT TLS and per-device ACL migration: signed OTA is validated, but broker TLS/ACLs are still staged and not enabled fleet-wide.
- Temperature Graph grouping: current grouping is hard-coded in `app/iot_home/dashboard.py`; revisit if group membership needs to become user-configurable.
- Outdoor DHT22 humidity flagging: current rule catches high pegged readings, but `OutdoorA` also produced an implausibly low reading; revisit the rule to flag both high and low outdoor humidity failures.

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
- New ESP32 provisioning is complete for the current batch: `RoomB` / `esp32-device-id` and `UtilityE` / `esp32-device-id`.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://iot-pi.local:8000` or `http://<pi-ip-address>:8000`.
- Dashboard app: summary metrics, configurable house diagram, device cards, latest readings, and `/api/history` trend data are in `app/iot_home/dashboard.py`. The diagram supports fallback built-in placements plus local `config/floorplan.json`; actual image assets should live under `data/dashboard-assets/` and be referenced as `/dashboard-assets/<file>`. The Temperature Graph selector is grouped into `Inside`, `Outside`, and `Separate`, with both group-level `All` checkboxes and individual device checkboxes. Outdoor DHT22 humidity at or above `99%` is flagged as suspect and excluded from average humidity.
- Dashboard rotation: the main dashboard content now rotates every 5 seconds through House Diagram, Device List Grid, Temperature Graph, and Latest Readings. Normal port `8000` serves this rotating view.
- Dashboard verification: normal port `8000` serves `/api/floorplan`, the suspect humidity flag, and the `RoomB` and `UtilityE` floorplan placements. Latest live check showed 20 mapped devices online, 0 stale, no `UNMAPPED` rows, and 7 devices on signed OTA. The stale-calculation fix for bad startup/NTP timestamps is loaded on normal port `8000` after the Pi reboot.
- Telemetry policy memory: ESP32s should read DHT22 frequently, reject impossible values and one-off large jumps, publish median-filtered temp/humidity every 600 seconds, and only publish early when filtered temperature differs by the configured threshold for 3 consecutive valid samples. Humidity is reported but does not trigger early publishes.
- Latest live-tested OTA artifact: `data/firmware/0.1.3-signed-ota/firmware.bin`; ignored by git because runtime/build artifacts stay local.
