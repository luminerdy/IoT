# Current Status

Last updated: 2026-07-05

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is a local-first Raspberry Pi IoT system with MQTT, SQLite, a boot-enabled web dashboard, runtime MQTT config, filtered ESP32 telemetry, and local OTA.

## Current Phase

Phase 5: Fleet operations plus daily dashboard improvements

Status: Phases 0 through 4 are complete for the current local-first system. Signed OTA hardening and signed build-number anti-rollback are validated on the USB-recoverable bench device, and all 21 mapped devices are on `0.1.4-antirollback`. The active work is Phase 5: fleet operations, dashboard maintenance workflows, backups, tests/CI, and staged security hardening.

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
- Grouped the Temperature Graph device selector into `Inside`, `Outside`, and `Separate` sections. The graph now derives group membership from floorplan zone metadata where available: `outdoor` zones go to `Outside`, `utility` zones go to `Separate`, and all remaining reporting locations go to `Inside`; one laundry-room utility location is intentionally overridden into `Inside`.
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
- Installed and authenticated GitHub CLI locally for terminal-based PR/check workflows.
- Sanitized the tracked public branch tip to remove local private IPs, MAC-shaped addresses, real ESP32 IDs, Pi hostname references, and real room/location labels. Older public git history still contains local identifiers but no passwords or private key material were found by the scan.
- Updated the dashboard to rotate through four full-screen-style views every 5 seconds: House Diagram, Device List Grid, Temperature Graph, and Latest Readings. The summary/header remain visible, while the main content switches views.
- Hardened dashboard stale detection so the API can use collector receipt time when a device publishes telemetry with a bad startup/NTP timestamp.
- Continued the signed OTA rollout with three additional indoor devices; the signed OTA count is now 7 devices.
- Tightened the 1080p rotating dashboard views: the 20-device grid and Latest Readings table now fit at 1920x1080, the readings table hides the device-ID column, and firmware labels are shortened.
- Added a `Pause Views` / `Resume Views` dashboard control so the current rotated view can be held for deeper inspection while live data refresh continues.
- Provisioned the first attic ESP32 as `AtticDoor`: flashed `0.1.3-signed-ota` over USB, added ignored local location/floorplan mappings, grouped it with `Separate` through a `utility` floorplan zone, replaced a bad DHT22 sensor, and verified valid attic telemetry.
- Added Python project metadata, focused pytest coverage, and a GitHub Actions CI workflow for Python compile/tests plus PlatformIO firmware checking.
- Added a SQLite backup script with integrity checking and an S3-ready backup runbook for later AWS S3 copy.
- Cleared the medium firmware static-analysis warning by guarding the median helper against invalid counts.
- Investigated `Sunroom` after it went offline; replacing the wire brought it back, and it is now reporting steadily again with increasing sequence numbers.
- Continued the signed OTA rollout on 2026-07-01 with two three-device batches; all six came back online/non-stale on `0.1.3-signed-ota`.
- Completed the signed OTA rollout on 2026-07-01 with one two-device batch and one final five-device batch; all seven remaining devices came back online/non-stale on `0.1.3-signed-ota`.
- Checked backups on 2026-07-02: created and restore-verified a fresh local SQLite backup, fixed the cron restic PATH issue, created restic snapshot `d5802848`, restored the latest S3 backup into a scratch directory, and verified the restic repository with no errors.
- Reviewed an architecture/security assessment on 2026-07-02 and accepted the main follow-up priorities: stop retained telemetry pollution, pin/compile firmware in CI, add MQTT ACL protection, add dashboard access control, and add OTA anti-rollback.
- Checked the unattended restic cron backup on 2026-07-03; the 02:15 run succeeded and saved snapshot `0043918c`.
- Added code-side retained telemetry protection: firmware no longer retains telemetry publishes, and the collector/database path dedupes repeated `(device_id, seq, datetime)` readings.
- Tested the non-retained telemetry firmware change on the USB bench ESP32 only: USB flash succeeded, MQTT/dashboard telemetry returned, fresh config-triggered and periodic telemetry publishes had MQTT retain flag `0`, and the bench config was restored to `reportIntervalSeconds=600`.
- Smoke-tested collector dedupe against the real local broker with a temporary SQLite database; repeated retained delivery did not duplicate reading rows.
- Added collector handling for empty MQTT payloads so retained-message deletes are ignored cleanly.
- Pinned PlatformIO `espressif32` to `6.10.0` and added a real firmware build to CI.
- Activated current-listener MQTT ACL protection on port `1883`: the shared `iot` user keeps telemetry/status flow while `iot-admin` owns config and OTA command publishing.
- Verified live MQTT ACL rules: fleet-user command delivery was blocked, admin command delivery worked, and fleet-user telemetry delivery still worked.
- Enabled dashboard Basic auth through `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`, then removed it later on 2026-07-04 by local preference so anyone already on the home network can view the dashboard. Private-network `/firmware/...` restrictions still protect OTA downloads from non-local clients.
- Recorded the standing release gate that no firmware build goes to fleet devices until the exact build is fully tested on the local USB-connected bench ESP32.
- Fixed the CI firmware build failure on PR #3 by making `firmware/include/secrets.sample.h` valid for clean-runner compilation; both Python and firmware checks now pass on the PR.
- Deployed the Pi-side collector/database changes on 2026-07-04: created backup `data/backups/iot-20260704T180617Z.sqlite.gz`, restarted `iot-home-collector.service`, verified collector logs, verified 21 devices online / 0 stale / 0 unmapped, and confirmed retained-message replay created 0 restart-window duplicate readings.
- Added signed OTA anti-rollback with monotonic build number `2026070401` in firmware `0.1.4-antirollback`; the bench device accepted the upgrade, rejected a signed lower-build rollback test as `firmware rollback rejected`, and the 21 mapped devices were rolled out in small batches.
- Completed a post-hardening reboot resilience check on 2026-07-04: created backup `data/backups/iot-20260704T210906Z.sqlite.gz`, rebooted the Pi, verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` came back active/enabled, verified dashboard/API access, verified MQTT ACL behavior, and confirmed 21 devices online / 0 stale / 0 unmapped.
- Checked the unattended restic cron backup on 2026-07-05; the 02:15 run succeeded and saved snapshot `2ba924d0`. Restored the latest snapshot into a scratch directory, verified the expected roots, removed the scratch restore tree, and ran `restic check --read-data-subset=1/100` with no repository errors.
- Added `docs/operations-runbook.md` with daily health checks, backup verification, runtime config publishing, OTA rollout guardrails, common service recovery, and an add/replace sensor checklist.

## Live Dashboard State

Latest dashboard API check on 2026-07-05 at about 06:48 CDT shows 21 mapped devices online, 0 stale, and 0 unmapped after the `0.1.4-antirollback` rollout, MQTT ACL activation, dashboard auth removal, Pi reboot, and scheduled backup verification. All 21 mapped devices are on `0.1.4-antirollback`; 0 devices remain on `0.1.3-signed-ota`. The live dashboard also has the 1080p-fit rotation views, floorplan-derived graph groups, the laundry-room Inside override, and the rotation pause/resume control loaded.

- Live fleet count: 21 online, 0 offline.
- Anti-rollback firmware count: 21 devices on `0.1.4-antirollback`.
- Remaining old firmware count: 0 devices on `0.1.3-signed-ota`.
- `Sunroom` / `esp32-device-id`: online again after wire replacement; current sequence is increasing normally.
- Current suspect humidity flag: `Porch` at `99.9%`.
- `UNMAPPED` count: 0.

## Active Blockers

- The actual house image has not been uploaded yet. The dashboard is ready for it through `data/dashboard-assets/` plus `config/floorplan.json`.
- The four-view rotating dashboard is active on normal port `8000`, including the pause/resume control, floorplan-derived Temperature Graph groups, 1080p-fit Device List Grid and Latest Readings views, and collector-receipt-time stale calculation.
- Live operator credentials for `iot-admin` are stored locally in `/home/scotty/.config/iot-home/operator-credentials.env` with mode `0600`. Dashboard Basic auth was removed on 2026-07-04; dashboard access is intentionally open to clients on the home network.

## Next Actions

1. Keep watching the `0.1.4-antirollback` fleet through normal telemetry intervals and recheck `/api/latest` plus collector logs if device status looks odd.
2. Keep `Bench Device` (`esp32-device-id`) on `/dev/ttyUSB0` for firmware and feature validation before deploying to other devices; never push firmware to the fleet until the exact build has passed bench ESP32 testing.
3. Use collector desired-version mismatch detection for deployment records; only enable `--auto-ota` after the exact staged firmware build has passed bench ESP32 validation.
4. Provision the second attic ESP32 when available and place it in the intended graph group.
5. Upload the actual house image under `data/dashboard-assets/`, set `backgroundImage` in local `config/floorplan.json`, and tune the existing sensor placement overlay.
6. Add a dashboard admin view for device/location mapping when source-editing local JSON becomes too tedious.

## Decisions To Revisit Soon

- MQTT authentication: anonymous local-only vs username/password.
- Location mapping storage: SQLite table vs `locations.json`.
- Dashboard stack: current dependency-free Python HTTP server is working; FastAPI/HTMX can still be revisited if routes/forms grow.
- Pi dependency install approach: direct system packages vs isolated app environment.
- MQTT TLS and per-device ACL migration: signed OTA is validated, but broker TLS/ACLs are still staged and not enabled fleet-wide.
- Temperature Graph grouping: current grouping follows floorplan zone metadata with a small in-code Inside override; revisit if group membership overrides need to become user-configurable.
- Outdoor DHT22 humidity flagging: current rule catches high pegged readings, but `OutdoorA` also produced an implausibly low reading; revisit the rule to flag both high and low outdoor humidity failures.

## Where Details Live

- Accomplishments and dated work history: `docs/progress-log.md`
- Phase plan and task backlog: `docs/implementation-plan.md`
- Architecture decisions: `docs/decision-record.md`
- Hardware findings and checks: `docs/hardware-notes.md`
- MQTT topics and payloads: `docs/mqtt-schema.md`
- Daily operations, backup checks, OTA guardrails, and sensor replacement: `docs/operations-runbook.md`
- Overall architecture: `Local-First-Architecture.md`

## Stop Point

- Morning 2026-07-05: scheduled restic snapshot `2ba924d0` is verified, restore check passed, repository check found no errors, services are active/enabled, dashboard API reports 21 online / 0 stale / 0 unmapped, and the USB bench device is present on `/dev/ttyUSB0`.
- Local branch: `main`
- Latest local commit: run `git log -1 --oneline`.
- Public GitHub repo: `luminerdy/IoT`
- Merged PR: `https://github.com/luminerdy/IoT/pull/3`
- GitHub CLI is authenticated for PR/check workflows; push future changes from a new branch or directly to `main` only when intentional.
- Local-only ignored files include runtime data, build output, `config/locations.json`, `config/floorplan.json`, and `firmware/include/secrets.h`.
- New ESP32 provisioning is complete for the current batch: `RoomB` / `esp32-device-id`, `UtilityE` / `esp32-device-id`, and `AtticDoor` / `esp32-device-id`.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://iot-pi.local:8000` or `http://<pi-ip-address>:8000`.
- Dashboard app: summary metrics, configurable house diagram, device cards, latest readings, and `/api/history` trend data are in `app/iot_home/dashboard.py`. The diagram supports fallback built-in placements plus local `config/floorplan.json`; actual image assets should live under `data/dashboard-assets/` and be referenced as `/dashboard-assets/<file>`. The Temperature Graph selector is grouped into `Inside`, `Outside`, and `Separate`, with both group-level `All` checkboxes and individual device checkboxes. Grouping follows floorplan zone metadata where available, with a small Inside override for the laundry-room utility location. Outdoor DHT22 humidity at or above `99%` is flagged as suspect and excluded from average humidity.
- Dashboard rotation: the main dashboard content now rotates every 5 seconds through House Diagram, Device List Grid, Temperature Graph, and Latest Readings. Normal port `8000` serves this rotating view. Use the `Pause Views` button to hold the current view for inspection; data refresh continues while rotation is paused.
- Dashboard verification: normal port `8000` serves `/api/floorplan`, the suspect humidity flag, and the current floorplan placements. Latest live check on 2026-07-01 showed 21 mapped devices online, 0 stale, no `UNMAPPED` rows, and 21 devices on signed OTA. The stale-calculation fix for bad startup/NTP timestamps, 1080p-fit rotated views, floorplan-derived graph groups, laundry-room Inside override, AtticDoor Separate grouping, and pause/resume control are loaded on normal port `8000`.
- Telemetry policy memory: ESP32s should read DHT22 frequently, reject impossible values and one-off large jumps, publish median-filtered temp/humidity every 600 seconds, and only publish early when filtered temperature differs by the configured threshold for 3 consecutive valid samples. Humidity is reported but does not trigger early publishes.
- Latest live-tested OTA artifact: `data/firmware/0.1.4-antirollback/firmware.bin`; ignored by git because runtime/build artifacts stay local.
- Current hardening state: MQTT ACLs, collector/database dedupe, non-retained telemetry firmware, signed OTA, and signed anti-rollback are live. Dashboard password auth is intentionally disabled; home-network clients may view the dashboard without credentials.
