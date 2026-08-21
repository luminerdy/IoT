# Current Status

Last updated: 2026-08-16

This is the first file to read after a reboot, context switch, or long pause.

## One-Line Summary

The project is a local-first Raspberry Pi IoT system with MQTT, SQLite, a boot-enabled web dashboard, runtime MQTT config, filtered ESP32 telemetry, and local OTA.

## Current Phase

Phase 5: Fleet operations plus daily dashboard improvements

Status: Phases 0 through 4 are complete for the current local-first system. Signed OTA hardening and signed build-number anti-rollback are live. The latest bench-validated SEC-015 firmware is `0.1.11-sec015-json` build `2026081002`, which keeps the MQTT TLS hostname fix and completes SEC-015 device JSON parsing/construction. The replacement GarageDriveway board is `esp32-device-id` on `0.1.11-sec015-json`; the replacement WallBehindWH board is `esp32-device-id` on `0.1.11-sec015-json`; the replacement WaterHeater board is `esp32-device-id` on `0.1.11-sec015-json`. The old suspect GarageDriveway, WallBehindWH, and WaterHeater IDs remain retired while historical readings stay preserved. `Attic` remains on `0.1.8-arduinojson` after it failed to converge during a final rollout attempt. The instability evidence is now treated as a device/power/sensor issue to investigate rather than a SEC-015-specific blocker. The separate retired `UNMAPPED`/`AtticChimney` record is hidden from collection/dashboard current views through `config/retired_devices.json` while historical readings remain preserved. Watchdog/post-reboot events are stored in `monitoring_events` and surfaced in the dashboard System Health panel. The dashboard Latest Readings/API separates telemetry freshness from status freshness, shows sequence/reset stability and Sensor health, and returns explicit UTC `Z` timestamps to avoid browser `0s ago` rendering errors. The live database is schema version 4. The managed collector, dashboard, and Mosquitto services are active. After the 2026-08-16 power outage/router DHCP conflict was resolved, PiServer `wlan0` is locally pinned to static/manual `<private-ip>`; ESP32 MQTT connections and `/api/latest` freshness recovered, and the Pi3 watchdog is again watching `<private-ip>` with relay control enabled. A router DHCP reservation or pool exclusion is still the remaining guard against some other device taking <pi-static-host> first during a future outage. The active work is Phase 5: fleet operations, hardware replacement, dashboard maintenance workflows, backups, tests/CI, and staged security hardening.

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
- Added NVS-provisioned, per-device TLS profiles and passed the isolated USB
  bench gate on Sunroom Test. After separate approval, activated a parallel
  production TLS listener on `8883` and migrated only Sunroom Test to its
  per-device credential. The shared `1883` listener remains active for the
  rest of the fleet.
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
- Kept read-only dashboard access open on the home network by explicit policy,
  while requiring Basic auth for location-mapping writes and a capability key
  or Basic auth for firmware downloads.
- Recorded the standing release gate that no firmware build goes to fleet devices until the exact build is fully tested on the local USB-connected bench ESP32.
- Fixed the CI firmware build failure on PR #3 by making `firmware/include/secrets.sample.h` valid for clean-runner compilation; both Python and firmware checks now pass on the PR.
- Deployed the Pi-side collector/database changes on 2026-07-04: created backup `data/backups/iot-20260704T180617Z.sqlite.gz`, restarted `iot-home-collector.service`, verified collector logs, verified 21 devices online / 0 stale / 0 unmapped, and confirmed retained-message replay created 0 restart-window duplicate readings.
- Added signed OTA anti-rollback with monotonic build number `2026070401` in firmware `0.1.4-antirollback`; the bench device accepted the upgrade, rejected a signed lower-build rollback test as `firmware rollback rejected`, and the 21 mapped devices were rolled out in small batches.
- Completed a post-hardening reboot resilience check on 2026-07-04: created backup `data/backups/iot-20260704T210906Z.sqlite.gz`, rebooted the Pi, verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` came back active/enabled, verified dashboard/API access, verified MQTT ACL behavior, and confirmed 21 devices online / 0 stale / 0 unmapped.
- Checked the unattended restic cron backup on 2026-07-05; the 02:15 run succeeded and saved snapshot `2ba924d0`. Restored the latest snapshot into a scratch directory, verified the expected roots, removed the scratch restore tree, and ran `restic check --read-data-subset=1/100` with no repository errors.
- Added `docs/operations-runbook.md` with daily health checks, backup verification, runtime config publishing, OTA rollout guardrails, common service recovery, and an add/replace sensor checklist.
- Added a dashboard `Manage Devices` admin panel on 2026-07-08 for device/location mapping, with `/api/locations` read/save support and local-network-only writes to `config/locations.json`.
- Checked backups on 2026-07-08: restic snapshot `a2980899` is present from the 02:15 cron run, `restic check` found no repository errors, the latest snapshot contains `data/iot.db`, `config/locations.json`, and `config/floorplan.json`, and the dumped database passed SQLite integrity check.
- Added a daily local SQLite backup cron job at 02:05 CDT so `data/backups/iot-*.sqlite.gz` is refreshed before the 02:15 restic/S3 backup. Manually created and restore-verified `data/backups/iot-20260708T183106Z.sqlite.gz`.
- Provisioned `AtticChimney` on 2026-07-09 and `Attic` on 2026-07-10, bringing the mapped fleet to 23 devices and the attic set to three sensors.
- Added a dedicated Attic graph group, alphabetical device-card sorting, hottest-first Latest Readings, and graph reference lines at 75 F and 100 F.
- Recorded an approximately 3 hour 12 minute `Attic` telemetry gap after a 137.5 F peak. The gap began before the Pi reboot and did not affect the other attic sensors; heat-related power or reboot instability remains a hypothesis to check during the next afternoon heat window.
- Removed firmware-driven onboard LED flashes from telemetry publishes and MQTT connection failures in `0.1.5-led-off` build `2026071201`.
- Built, signed, staged, and USB-validated the exact `0.1.5-led-off` binary on `Sunroom Test`; it remained online and non-stale through a full ten-minute report interval.
- Rolled `0.1.5-led-off` to Den, Kitchen, Office, FrontBedroom, Entryway, and Laundryroom. Together with Sunroom Test, 7 devices are online and non-stale on the new build.
- Paused the rollout after MasterBedroom repeatedly missed OTA commands or stopped after `downloading`. It remains online/non-stale on `0.1.4-antirollback` but continues frequent MQTT disconnect/reconnect cycles. The remaining fleet was intentionally left on the prior firmware.
- Confirmed ESP32 clients could not fetch the artifact through `iot-pi.local` during this rollout. The working OTA base URL used the numeric Pi LAN address `http://<pi-lan-ip>:8000`.
- Fixed and deployed the Pi3 external watchdog's first-recovery cooldown logic,
  then completed a controlled end-to-end relay test on 2026-08-05. GPIO17
  removed PiServer power for 15 seconds after the five-check test threshold,
  PiServer booted successfully, and its core services returned active. The
  production threshold is now 10 consecutive one-minute failures, with a
  one-hour cooldown between actual relay cycles.
- Implemented and activated SEC-016 capability-key protection for firmware
  downloads on 2026-08-06, with the key stored in the protected service environment.
  OTA staging and command reconstruction now include the key in the download
  URL, missing or incorrect keys receive HTTP 401, and query strings are
  omitted from access logs so the key is not logged.
- Added lossless database preservation and capacity monitoring. The daily
  maintenance validates the live database and newest compressed backup, runs
  `PRAGMA optimize`, proves preserved-table row counts are unchanged, and
  alerts through a failed systemd run on backup freshness or storage limits.
  The timer is installed and enabled; its first live oneshot passed on
  2026-08-07.
- Added persistent monitoring events and a post-reboot health recorder. The
  dashboard System Health panel shows the latest post-reboot verification and
  Pi3 watchdog relay event separately from fleet stale/offline state.
- Added CI safeguards for Ruff lint/format, pytest coverage reporting, gitleaks,
  and hash-only current-tree identifier scanning. The expanded 127-test Python
  suite measures 86.8% with branch coverage enabled, and CI now enforces the
  required 80% floor.
- Extracted firmware sensor filtering and publish policy into an
  Arduino-independent C++ library. Six PlatformIO native tests now cover median
  filtering, plausibility bounds, outlier confirmation, rolling windows,
  interval publishing, and confirmed-change publishing.
- Replaced OTA command substring scanning with ArduinoJson `7.4.3`. Nine native
  TEST-012 cases cover typed and bounded manifest fields, malformed/root/key-
  confusion input, hex/SHA checks, and preflight/download validation order. All
  15 native firmware cases pass; eight MQTT-profile cases bring the current
  native total to 23. The exact `0.1.8-arduinojson` build
  `2026080702` was USB-flashed and validated on Sunroom Test; it returned online
  with fresh telemetry and rejected three safe parser/preflight probes before
  download. A subsequent uninterrupted 60-minute observation passed the
  requested 30-minute cadence/plausibility test with six 600–601 second
  intervals, no early publishes, monotonic sequence numbers, plausible
  readings, and `OK` status throughout. No fleet OTA was sent.
- Finalized committed release candidate `0.1.8-arduinojson` build `2026080703`
  with SHA-256
  `76ff6464c2189c029b6bcf57bd660b553b3d8b0fdef90075cdbf8929bd75cf91`.
  Sunroom Test accepted it through the real signed OTA path, returned on the
  target build, passed a 3,601-second six-interval soak, passed config
  apply/reject/restore and signed rollback checks, and rejected an invalid
  firmware signature after download without rebooting. PR #5 CI is green.
- Completed the remaining SEC-015 source refactor on 2026-08-10: retained
  config parsing and device-side status/LWT/config-response/OTA-status/
  telemetry JSON construction now use ArduinoJson with bounded serialization.
  The exact `0.1.11-sec015-json` build `2026081002` was USB-flashed to Sunroom
  Test, rejected malformed/wrong-type config and OTA probes without download,
  restored default config through an empty retained payload, and passed the next
  600-second interval telemetry check. No fleet OTA was sent.
- Started the separately approved one-device-at-a-time SEC-015 signed OTA
  rollout. Den updated cleanly and passed a one-hour burn-in. Kitchen updated
  and returned `OK` telemetry, but raw telemetry during burn-in reported
  `restartReason=Brownout`, `uptimeSeconds=7`, and `seq=1`; after explicit
  acceptance to continue, Office updated cleanly and passed a one-hour burn-in.
  The rollout is paused again because Kitchen continued showing repeated
  normalized `seq=1` resets afterward.
- Merged PR #5 as `9029754`, rebuilt the merged `main` artifact, and confirmed
  it exact-matched the signed and bench-tested binary. Rolled it to the 21
  remaining active devices in five acknowledged batches. GarageDriveway's
  first download ended with `firmware stream failed`; one isolated retry
  installed the target build and returned fresh `OK` telemetry, although its
  transient `rebooting` status was not observed. All 22 active mapped devices
  are now online, non-stale, and on `0.1.8-arduinojson`.
- Kept OTA command authority operator-only by removing collector `--auto-ota`
  and its MQTT publish path. Desired-version reconciliation still records one
  `detected` attempt per cooldown window. Added TEST-023, which validates the
  tracked per-device ACL with two device users, the read-only collector, and
  admin against an isolated Mosquitto broker. No live ACL was changed.
- Added packaged, numbered SQLite migrations with transactional
  `PRAGMA user_version` tracking. Version 2 replaces the collector's
  check-before-insert dedupe with a partial unique index and correctly exempts
  pre-NTP sentinel readings. It preserves historical duplicate rows through a
  migration-only marker while indexing one canonical row per key.
- Validated the migration against SQLite online-backup copies of production.
  The latest version-0 replay preserved all 242,715 readings and every original
  value, left the other preserved tables unchanged, marked 503 extra legacy
  copies, and left no indexed duplicate groups.
- The live database is now schema version 2 with integrity `ok`. It migrated
  during simultaneous dashboard and collector starts at 12:46 CDT; one
  collector attempt exposed a concurrent-start race, then systemd restarted it
  successfully five seconds later. Commit `cacfceb` fixes the race by checking
  the schema version again after acquiring the migration write lock, with a
  deterministic regression test. The collector was restarted at 15:14 CDT to
  load the fix, reconnected and subscribed immediately, and produced no warning,
  traceback, or migration error.
- Created and restore-verified fresh post-migration backup
  `data/backups/iot-20260807T193918Z.sqlite.gz`. Its snapshot contains 243,328
  readings, 23 devices, 0 deployment attempts, 395 system metrics, 503 preserved
  legacy exemptions, and no indexed duplicate groups.

## Live Dashboard State

The latest documented 2026-08-10 bench checkpoint has Sunroom Test on
`0.1.11-sec015-json` build `2026081002`, SHA-256
`91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`,
977,040 bytes. It keeps schema version 2 MQTT profiles with separate
`mqttConnectHost` and `mqttTlsHostname` fields, allowing the ESP32 to connect to
the hub IP while still validating the broker certificate DNS SAN, and completes
SEC-015 by using ArduinoJson for retained config parsing plus device-side JSON
payload construction. Bench validation on Sunroom Test verified fresh target
telemetry, valid config apply, malformed JSON rejection, wrong-type config
rejection, empty retained config clear back to defaults, safe OTA malformed/
unsupported/wrong-type rejection without download, and the next normal
600-second telemetry interval. No fleet OTA was sent.

The prior `0.1.10-tls-host` build `2026081001` successfully connected to an
isolated TLS Mosquitto listener on port `8884` using `<hub-ip>` as the TCP
endpoint and `<hub-tls-hostname>` as the TLS hostname, then published retained
status and non-retained telemetry as its per-device username. After that,
Sunroom Test was provisioned against the real production `8883` listener with
the same schema v2 endpoint split. `ss` showed an established `<device-ip>` to
`<hub-ip>:8883` socket owned by Mosquitto, retained status showed
`0.1.10-tls-host`, and the dashboard API showed fresh `OK` telemetry. The NVS
MQTT profile was then cleared and fresh production fallback telemetry through
shared `1883` was verified. The Sunroom Test broker user password was rotated
after the check and the temporary plaintext credential file was deleted. The
active TLS-capable firmware set includes Sunroom Test, Den, Kitchen, Office,
MasterBedroom, and LaundryroomAC, but only Sunroom Test has bench-tested the
schema v2 profile on production TLS.
The additional `UNMAPPED` record associated with the temporarily retired
`AtticChimney` remains on `0.1.6-recovery`; it remains excluded from the active
mapped fleet until it is intentionally remapped or re-retired. The dashboard
code includes the dedicated Attic graph group,
alphabetical device cards, hottest-first Latest Readings, and 75 F / 100 F
graph references.

Firmware `0.1.6-recovery` build `2026072401` passed the USB bench gate on
2026-07-25. It replaces the blocking initial WiFi loop with bounded reconnect
attempts, reboots after 15 minutes without full WiFi/MQTT connectivity, and
adds a device-staggered 7–8 day safety reboot with a persisted one-shot
`recoveryReason`. A bench-only MQTT proxy outage triggered the production
15-minute `network_timeout` restart. A temporary 60–70 second safety interval
triggered `weekly_safety`. Both tests returned automatically with
`restartReason=Software`, reported the expected recovery reason once, and
cleared it to `none` on the next successful telemetry. The real 7–8 day
constants and direct production MQTT port were then restored and the exact
production build was reflashed and reverified on `Sunroom Test`.

- Live fleet count: re-check `/api/latest` before acting. After the
  2026-08-12 retirement of suspect `GarageDriveway` and the separate retired
  `UNMAPPED` device, the live dashboard APIs hide both retired IDs and show 21
  latest rows, 0 offline, and 0 stale.
- Recovery firmware count: 0 active devices; the excluded retired `UNMAPPED`
  record remains on `0.1.6-recovery` build `2026072401` in preserved history
  but is hidden from current dashboard APIs.
- Firmware count at the latest 2026-08-12 check: 2 active mapped devices on
  `0.1.8-arduinojson` (`Attic` and `WallBehindWH`); all other 19 visible
  active mapped devices are on `0.1.11-sec015-json` build `2026081002`.
  Sunroom Test's NVS TLS profile is
  cleared; it uses compiled shared `1883` fallback after USB reflash, isolated
  TLS validation, and a production `8883` TLS validation.
- Deployed signed-OTA release: build `2026080703` passed the committed-artifact
  signed OTA and release soak gates. Its staged, served, clean-rebuilt, and
  merged-main binaries exact-match the recorded SHA-256.
- Previous firmware count: 0 devices.
- Remaining old firmware count: 0 devices on `0.1.3-signed-ota`.
- `Sunroom` / `esp32-device-id`: online again after wire replacement; current sequence is increasing normally.
- Current suspect humidity flag: `Porch` at `99.9%`.
- `UNMAPPED` count: 0 in current dashboard APIs after the 2026-08-12 retired
  device filter. Historical `UNMAPPED` readings remain preserved.

## Active Blockers

- `AtticChimney` stopped reporting and was temporarily retired from the
  dashboard fleet on 2026-08-04 until it is safe to enter the attic and replace
  it. Historical readings were preserved. Its returned `UNMAPPED` row is now
  hidden through `config/retired_devices.json`.
- Replaced GarageDriveway, WallBehindWH, and WaterHeater boards are installed
  and reporting, while their old suspect IDs remain retired with historical
  readings preserved.
- The SEC-015 firmware rollout is paused for device-stability observation, not
  for a confirmed firmware-wide regression. Current watch items include
  `Attic`, `GarageDriveway`, `MasterBedroom`, `WallBehindWH`, and the newly
  replaced `WaterHeater`; `Sunroom Test` also shows resets but is ignored as a
  production rollout stability gate because it is powered from PiServer USB.
- The actual house image has not been uploaded yet. The dashboard is ready for it through `data/dashboard-assets/` plus `config/floorplan.json`.
- The four-view rotating dashboard is active on normal port `8000`, including the pause/resume control, floorplan-derived Temperature Graph groups, 1080p-fit Device List Grid and Latest Readings views, collector-receipt-time stale calculation, and `Manage Devices` panel.
- Live operator credentials for `iot-admin` are stored locally in `/home/scotty/.config/iot-home/operator-credentials.env` with mode `0600`. Dashboard read access is intentionally open to clients on the home network; separate dashboard credentials in `/home/scotty/.config/iot-home/dashboard-credentials.env`, also mode `0600`, protect location-mapping writes.

## Next Actions

1. Continue observing device stability after the GarageDriveway, WallBehindWH,
   and WaterHeater board replacements. Re-check
   `/api/latest`, raw telemetry `restartReason`/`uptimeSeconds`, and sequence
   behavior before resuming any firmware rollout.
2. Plan a separately approved, incremental production MQTT TLS/per-device
   credential migration, starting from a fresh fleet gate and one accessible
   non-attic device at a time. Do not retire the shared fallback until every
   active device has passed its migration check.
3. Extract dashboard HTML/CSS/JavaScript into static assets after the security
   and data milestones above.
4. Monitor the Pi3 watchdog with its production threshold of 10 consecutive
   one-minute failures; repeated recovery cycles should be recorded through
   `iot_home.post_reboot_check --import-watchdog` and investigated rather than
   treated as normal. Watch the next 24 hours after the 2026-08-16 outage
   recovery for renewed fleet stale/offline behavior, IP conflict symptoms, or
   watchdog relay events.
5. Keep `Sunroom Test` as the USB bench/test device on `/dev/ttyUSB0` for
   firmware validation, serial recovery, and first-pass feature checks. Because
   it is powered directly from PiServer USB and may not have production-quality
   power, ignore its sequence/reset stability when deciding whether a firmware
   rollout is safe to expand to deployed devices.
6. Replace retired `AtticChimney` only when attic access is safe, continue
   attic heat monitoring, upload the house image, and keep periodic backup
   restore checks.

The `0.1.8-arduinojson` release gate and fleet rollout are complete. Continue
to use the same USB bench gate, acknowledged small batches, and stop-on-failure
checks for future firmware releases.

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

- Afternoon 2026-08-12: `GarageDriveway` and the retired `UNMAPPED` device are
  hidden from current collection/dashboard views through
  `config/retired_devices.json`, with historical readings preserved. Mosquitto
  is systemd-active, but collector/dashboard are running as manual replacement
  processes because non-interactive `systemctl start` required authentication;
  restore managed units with interactive systemd access or reboot.
- Local branch: `agent/disable-iot-led`
- Published implementation commits: `789c308` and concurrent-migration fix
  `cacfceb`; final documentation may be newer.
- Public GitHub repo: `luminerdy/IoT`
- Draft PR: `https://github.com/luminerdy/IoT/pull/4`
- Merged PR: `https://github.com/luminerdy/IoT/pull/3`
- GitHub CLI is authenticated for PR/check workflows; push future changes from a new branch or directly to `main` only when intentional.
- Local-only ignored files include runtime data, build output, `config/locations.json`, `config/floorplan.json`, and `firmware/include/secrets.h`.
- New ESP32 provisioning is complete for the current batch: `RoomB` / `esp32-device-id`, `UtilityE` / `esp32-device-id`, and `AtticDoor` / `esp32-device-id`.
- Dashboard URL on the Pi: `http://127.0.0.1:8000`; LAN URL: `http://iot-pi.local:8000` or `http://<pi-ip-address>:8000`.
- Dashboard app: summary metrics, configurable house diagram, device cards, latest readings, `/api/history` trend data, and `/api/locations` mapping admin are in `app/iot_home/dashboard.py`. The diagram supports fallback built-in placements plus local `config/floorplan.json`; actual image assets should live under `data/dashboard-assets/` and be referenced as `/dashboard-assets/<file>`. The Temperature Graph selector is grouped into `Inside`, `Outside`, and `Separate`, with both group-level `All` checkboxes and individual device checkboxes. Grouping follows floorplan zone metadata where available, with a small Inside override for the laundry-room utility location. Outdoor DHT22 humidity at or above `99%` is flagged as suspect and excluded from average humidity.
- Dashboard rotation: the main dashboard content now rotates every 5 seconds through House Diagram, Device List Grid, Temperature Graph, and Latest Readings. Normal port `8000` serves this rotating view. Use the `Pause Views` button to hold the current view for inspection; data refresh continues while rotation is paused.
- Dashboard verification: normal port `8000` serves `/api/floorplan`, the suspect humidity flag, and the current floorplan placements. The latest check on 2026-07-10 showed 23 mapped devices online, 0 stale, no `UNMAPPED` rows, and all 23 on signed OTA. The dashboard code includes collector-receipt-time stale calculation, 1080p-fit rotated views, the dedicated Attic graph group, alphabetical device cards, hottest-first Latest Readings, 75 F / 100 F graph references, and pause/resume control.
- Telemetry policy memory: ESP32s should read DHT22 frequently, reject impossible values and one-off large jumps, publish median-filtered temp/humidity every 600 seconds, and only publish early when filtered temperature differs by the configured threshold for 3 consecutive valid samples. Humidity is reported but does not trigger early publishes.
- Latest live-tested OTA artifact: `data/firmware/0.1.5-led-off/firmware.bin`, build `2026071201`; ignored by git because runtime/build artifacts stay local.
- Current hardening state: MQTT ACLs, collector/database dedupe, non-retained telemetry firmware, signed OTA, and signed anti-rollback are live. Dashboard password auth is intentionally disabled; home-network clients may view the dashboard without credentials.
