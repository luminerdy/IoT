# Session Handoff

Last updated: 2026-08-10

## Pi3 External Watchdog

- Raspberry Pi 3 monitor: private LAN host reached through the `pi-watchdog`
  SSH alias.
- Connect from PiServer with SSH alias `pi-watchdog`; it uses the dedicated
  dedicated SSH identity.
- Its `pi-watchdog.service` is enabled and active. It watches PiServer through
  its private LAN address, and relay control is enabled on BCM GPIO17.
- The hardware is a Digital Loggers IoT Relay. Its isolated universal input is
  designed for a direct 3.3 V GPIO signal plus ground; no external resistor or
  transistor driver is required.
- The initial-cooldown bug is fixed: the first qualified recovery is immediately
  eligible, while the one-hour cooldown applies only after an actual relay
  cycle. All 34 Python tests passed before deployment, and the installed Pi3
  script matched the tested local checksum.
- A controlled 2026-08-05 shutdown validated the complete recovery path. The
  Pi3 logged five failed checks, activated GPIO17 at 08:04:50 CDT, restored
  target power after 15 seconds, and reported a healthy target at 08:05:44.
  PiServer booted at 08:05:19 with Mosquitto, the collector, and the dashboard
  active and enabled.
- After validation, production was changed from the five-check test threshold
  to 10 consecutive one-minute failures. The watchdog restarted successfully,
  the protected configuration reads `WATCHDOG_FAILURES_BEFORE_RECOVERY=10`,
  and GPIO17 is output-low at idle. The 15-second relay interruption and
  one-hour between-cycle cooldown remain unchanged.
- On 2026-08-08, the Pi3 recorded 10 consecutive failed checks from 21:43:42
  through 21:52:37 CDT, activated GPIO17 at 21:52:37, restored target power
  after 15 seconds at 21:52:52, and reported PiServer healthy at 21:53:31.
  This should be treated as a real recovery event to monitor for recurrence.
- `monitoring_events` now stores post-reboot checks and imported watchdog relay
  events. `python -m iot_home.post_reboot_check --import-watchdog` records core
  service/API/database/backup status and imports recent Pi3 relay entries. The
  dashboard System Health panel reads this through `/api/system`.
- The live database was migrated to schema version 3 and contains fresh
  post-reboot checks plus the two Aug 8 watchdog relay entries.
  `iot-home-post-reboot-check.service` is installed and enabled, and
  `iot-home-dashboard.service` was restarted so `/api/system` exposes the new
  System Health payload.

## Current State

The local-first IoT stack is running on PiServer, but the collector/dashboard
process ownership needs attention. Mosquitto is active through systemd.
`iot-home-collector.service` and `iot-home-dashboard.service` are currently
systemd-inactive because a non-interactive restart/start required
authentication after a clean process stop. Replacement collector and dashboard
processes are running manually from `/home/scotty/IoT` with the same live
database, mapping, floorplan, firmware, and retired-device paths. Restore the
managed units with an interactive `systemctl start iot-home-collector.service
iot-home-dashboard.service` or a reboot when convenient. A parallel production
MQTT TLS listener is active on `8883` alongside the unchanged
shared-credential listener on `1883`.
The SEC-015 firmware rollout is paused after repeated reset evidence on
Kitchen and MasterBedroom. All visible active mapped devices except `Attic`
and `WallBehindWH` are now on `0.1.11-sec015-json` build `2026081002`; those
two remaining devices are still on `0.1.8-arduinojson`. Sunroom
Test's NVS MQTT profile is cleared after bench validation, so it is
intentionally back on compiled shared `1883` fallback.
An explicit attempt to update `Attic` with rollout
`20260812-attic-sec015-watch` did not converge: no OTA lifecycle status was
captured, it remained on `0.1.8-arduinojson`, and it continued rapid `seq=1`
resets. `WallBehindWH` was not attempted after that stop condition.
Final wrapup check after the commit found `Kitchen` currently offline:
last telemetry `2026-08-13T01:28:18Z`, offline status
`2026-08-13T01:37:51Z`, still on `0.1.11-sec015-json` with prior repeated
`seq=1` instability. Treat this as an active device-stability follow-up.
The separate retired `UNMAPPED` AtticChimney record and the suspect
`GarageDriveway` board are listed in ignored local `config/retired_devices.json`.
They are excluded from collector writes and hidden from latest/history/location
dashboard APIs while historical readings remain preserved.

Firmware downloads on live port `8000` now require a constant-time-checked
capability key or dashboard Basic auth. Missing/wrong keys return 401; a keyed
download was verified byte-for-byte against the staged production artifact.
Read-only dashboard access remains explicitly open on the home LAN, while
`POST /api/locations` requires separate dashboard credentials. Mapping updates
are locked against concurrent lost updates, request database connections close
explicitly, and schema initialization runs only at startup. Credentials remain
local in protected environment files and are not tracked.

On 2026-08-09, `Sunroom Test` was recovered over `/dev/ttyUSB0` after reporting
offline. Serial logs showed the NVS TLS profile failing ESP32 DNS resolution for
the hub TLS hostname on `8883`; clearing the NVS profile restored the compiled fallback
profile, and a USB reflash of the exact staged `0.1.9-nvs-tls` artifact
`3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501` restored
fresh fallback MQTT telemetry at 17:38:02. Do not re-provision TLS on Sunroom
Test until the ESP32 broker hostname strategy is fixed or deliberately changed.

On 2026-08-10, schema version 2 profiles fixed that hostname strategy by
separating `mqttConnectHost` from `mqttTlsHostname`. Exact firmware
`0.1.10-tls-host` build `2026081001` was USB-flashed to Sunroom Test; binary
SHA-256 was `afae56195002d97e2b397b51519f1a06df505d08c5ec180b32bbd25a79650ea8`.
An isolated user-owned Mosquitto TLS listener on port `8884` used a temporary
CA and a server certificate for `<hub-tls-hostname>`. Sunroom Test was provisioned
with `mqttConnectHost=<hub-ip>` and `mqttTlsHostname=<hub-tls-hostname>`,
connected from `<device-ip>` as `<device-user>`, subscribed to its own
command/config topics, and published retained status plus non-retained
telemetry. After the fix was committed, production `8883` was checked too:
Mosquitto was reloaded after resetting only the Sunroom Test broker user to a
temporary generated password, Sunroom Test accepted the schema v2 production
profile, `ss` showed an established `<device-ip>` to
`<hub-ip>:8883` socket, retained status showed `0.1.10-tls-host`, and the
dashboard API showed fresh `OK` telemetry. The NVS MQTT profile was then
cleared, fresh production fallback telemetry through shared `1883` was
verified, the Sunroom Test broker user was rotated again to an unstored random
password, and all temporary credential/CA files were deleted.

Also on 2026-08-10, the remaining SEC-015 source work was completed without
fleet deployment. Retained config parsing and device-side status/LWT/config-
response/OTA-status/telemetry JSON construction now use ArduinoJson with typed
field handling and bounded serialization. Exact firmware
`0.1.11-sec015-json` build `2026081002` was USB-flashed to Sunroom Test;
binary SHA-256 was
`91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`, size
977,040 bytes. Bench validation verified fresh target telemetry, valid config
apply, malformed config rejection, wrong-type config rejection, empty retained
config clear back to defaults, safe OTA malformed/unsupported/wrong-type
rejections without download, and the next normal 600-second telemetry interval.

After separate approval, a one-device-at-a-time signed OTA rollout began with a
one-hour burn-in before each next device. Den accepted the OTA with observed
`downloading` and `rebooting`, returned fresh `0.1.11-sec015-json` `OK`
telemetry, and passed the one-hour burn-in with sequence observations from 2
through 9 and no active fleet offline/stale devices. Kitchen then accepted the
OTA with observed `downloading` and `rebooting`, returned fresh target-version
`OK` telemetry, but failed burn-in: raw non-retained telemetry at
`2026-08-10T15:36:33Z` reported `restartReason=Brownout`, `uptimeSeconds=7`,
and `seq=1`. This brownout/sequence behavior was visible around Kitchen before
the OTA too, but it is still a rollout stop condition. After explicit
acceptance to continue one device at a time, Office accepted the OTA with
observed `downloading` and `rebooting`, returned fresh target-version `OK`
telemetry, and passed a one-hour burn-in from `2026-08-10T17:02:07Z` through
`2026-08-10T18:02:07Z`, with sequence observations from 2 through 12 and no
active fleet offline/stale devices. The rollout is paused again before another
device because Kitchen continued showing repeated normalized `seq=1` resets
through `2026-08-10T18:00:52Z`. After explicit acceptance to continue despite
Kitchen, MasterBedroom accepted the OTA with observed `downloading` and
`rebooting`, returned fresh target-version `OK` telemetry at
`2026-08-10T23:30:59Z`, and initially advanced to `seq=2` with
`uptimeSeconds=605` at `2026-08-10T23:51:10Z`. It then failed burn-in when raw
non-retained telemetry at `2026-08-10T23:59:22Z` reported
`restartReason=InterruptWatchdog`, `uptimeSeconds=5`, and `seq=1`. The active
mapped fleet gate remained clear, but no further OTA should be sent until the
Kitchen and MasterBedroom reset pattern is understood or explicitly accepted.

## Recovery Firmware Bench State

Firmware `0.1.6-recovery`, build `2026072401`, passed the USB bench gate and was
deployed to the full fleet. The uploader confirmed `/dev/ttyUSB0` MAC
`<bench-mac>`, which maps to `Sunroom Test` / `esp32-device-id`. It returned
online and non-stale with fresh telemetry on
the new version. The full USB bench gate passed on 2026-07-25.

The firmware now:

- Uses non-blocking WiFi reconnect attempts instead of waiting forever during
  initial connection.
- Reboots after 15 continuous minutes without both WiFi and MQTT.
- Performs a deterministic device-staggered safety reboot after 7–8 days.
- Persists `network_timeout` or `weekly_safety` across the restart and reports
  it once as `recoveryReason` in the next successful telemetry.
- Does not evaluate recovery timers during synchronous OTA application.

Validation completed:

- PlatformIO firmware build passed.
- All 30 Python tests passed.
- PlatformIO static analysis passed with only existing low-level style notices.
- USB flash, boot, MQTT reconnection, dashboard identity, firmware version, and
  fresh DHT22 telemetry were verified on Sunroom Test.

Bench validation completed:

- A user-owned MQTT proxy on port `1884` isolated only `Sunroom Test` while the
  production broker and fleet remained untouched.
- A continuous production-duration outage triggered
  `Recovery restart requested: network_timeout` after 15 minutes.
- The device returned automatically with `restartReason=Software` and
  `recoveryReason=network_timeout`; the next successful telemetry cleared
  `recoveryReason` to `none`.
- A test-only build with a deterministic 60–70 second safety interval triggered
  `weekly_safety`, returned automatically, reported the reason once, and
  cleared it on the next successful telemetry.
- The test-only constants and proxy port were removed. The real 7–8 day
  constants and direct MQTT port `1883` were restored.
- The exact production build was rebuilt and USB-flashed. Its binary SHA-256 is
  `56db51afdd3d3e05c3e2741ea90ee6143046b332de19774f317c634b432b8704`.
- The restored production build reports fresh telemetry with
  `recoveryReason=none`.
- PlatformIO build passed, all 30 Python tests passed, and PlatformIO static
  analysis passed with only the existing five low-level style notices.

## ArduinoJson OTA Bench State

- OTA command parsing uses pinned ArduinoJson `7.4.3`; typed, bounded manifest
  parsing and pure hex/SHA/preflight/download validation live in
  `firmware/lib/ota_manifest/`.
- Nine TEST-012 cases plus the six sensor-core and eight MQTT-profile cases pass
  natively. The ESP32 build and static analysis pass, and 127 Python tests pass
  at 86.76% branch-aware coverage.
- The exact `0.1.8-arduinojson` build `2026080702` was USB-flashed to Sunroom
  Test. The 839,344-byte binary SHA-256 is
  `a58577ffba350b39b209b976b75413b7901b15875c2e5c9e5087cd4b7e0ec855`.
- The device returned online with fresh telemetry and passed three safe,
  download-blocked MQTT probes: nested-command key confusion, string-typed
  size, and current-build rollback. No fleet OTA was sent.
- The requested 30-minute observation passed using a clean 60-minute window
  after the final USB-monitor-induced reset. Six successive intervals were
  600, 600, 600, 601, 600, and 600 seconds; sequence advanced monotonically, every
  status was `OK`, readings remained plausible, and there were no early
  publishes.
- The requested 30-minute observation is complete, but this was task-focused
  parser/preflight validation rather than the complete TEST-030 release
  checklist or a real signed OTA cycle. Run and
  record the full checklist before treating this candidate as fleet-ready.
- Opening PlatformIO's serial monitor toggled the USB control lines and reset
  the bench device; closing it and reading serial directly produced a clean
  boot. Keep the monitor detached during MQTT assertions on this adapter.
- Final committed build `2026080703` is 839,344 bytes with SHA-256
  `76ff6464c2189c029b6bcf57bd660b553b3d8b0fdef90075cdbf8929bd75cf91`.
  It passed signed OTA (`downloading → rebooting → target-build telemetry`), a
  3,601-second six-interval soak, config rejection/apply/default restoration,
  signed same-build rollback rejection, and post-download invalid firmware-
  signature rejection without reboot. This supersedes the preliminary
  `2026080702` candidate for release.
- PR #5 was merged to `main` as `9029754`; a clean post-merge rebuild
  exact-matched the staged and bench-tested artifact. The 21 non-bench active
  devices were updated in five acknowledged batches: Kitchen; Den/Entryway/
  Office; Garage/LaundryroomAC/Studio/Sunroom; Attic/AtticDoor/Laundryroom/
  WaterHeater/UnderAC/WallBehindWH; and BunkHouse/FrontBedroom/GarageDriveway/
  Lightpole/MasterBedroom/Porch/SunroomDoor.
- GarageDriveway's first download reported `firmware stream failed` and stopped
  the coordinator. It remained healthy on the old build. After fresh telemetry,
  one isolated retry downloaded and installed the candidate and produced fresh
  target-build `OK` telemetry; the `rebooting` status acknowledgement was lost,
  consistent with its weak `-82` RSSI. No further command was sent.

## Pick Up Next

1. Before resuming any rollout, run a fresh `/api/latest` fleet gate and confirm
   no active mapped device is offline or stale.
2. Do not continue the SEC-015 firmware rollout until Kitchen's and
   MasterBedroom's reboot behavior and repeated low-sequence resets are
   investigated or explicitly accepted. Check raw telemetry for
   `restartReason`, `uptimeSeconds`, and sequence behavior; inspect device
   power if needed.
3. Continue the incremental production MQTT TLS/per-device credential migration
   one physical USB device at a time. Do not retire the shared `1883` listener
   or shared fleet credential until every active device has been individually
   provisioned and observed.
4. Continue watchdog/fleet/attic monitoring. If another watchdog relay recovery
   occurs within 24 hours or repeated recoveries appear within a week,
   investigate PiServer power/network/system health before relying on the relay.
5. Decide whether to remap or re-retire the returned `UNMAPPED` device.

## Recent Physical Maintenance

- On 2026-08-11, the user replaced power for `GarageDriveway` and
  `Laundryroom`. A read-only `/api/latest` check at 19:43 CDT showed both
  online and non-stale afterward: `GarageDriveway` on `0.1.8-arduinojson`,
  `status=online`, `seq=164`, `ageSeconds=701`, `rssi=-68`; `Laundryroom` on
  `0.1.8-arduinojson`, `status=OK`, `seq=3`, `ageSeconds=213`, `rssi=-53`.
  The low `Laundryroom` sequence is expected immediately after power
  replacement; verify it advances before drawing conclusions about resets.
- The user also reported the `GarageDriveway` ESP32 is not in good shape and
  has ordered a replacement. A follow-up read-only `/api/latest` check at
  19:45 CDT still showed it online/non-stale on `0.1.8-arduinojson`, with
  `status=online`, `seq=164`, `ageSeconds=821`, and `rssi=-68`. Treat this
  board as suspect hardware until replaced.

## Recent Dashboard Maintenance

- On 2026-08-11, the dashboard Latest Readings view was updated to show latest
  `seq` and derived reset stability from persisted telemetry. The API now
  exposes `recentSeqResets`, `stability`, telemetry freshness fields, and
  separate device/status freshness fields.
- Staleness is based on the latest telemetry observation when telemetry exists,
  not a fresh status/device-row update. This keeps stale temperature and
  humidity data from appearing fresh when a retained or live status message
  arrives.
- The dashboard `0s ago` display was fixed by returning explicit UTC ISO-8601
  `Z` timestamp strings from `/api/latest`; JavaScript had been parsing
  SQLite-style UTC strings as local time. `iot-home-dashboard.service` was
  restarted at 21:23 CDT to load the fix. Read-only verification showed 23
  rows, all latest timestamp fields with `Z` suffixes, 21 online/non-stale
  rows, 2 stale rows (`GarageDriveway` and `UNMAPPED`), and 0 offline rows.

## Working Tree

The working tree contains the schema v2 MQTT TLS hostname fix plus the SEC-015
device JSON refactor on top of `main`. Exact firmware `0.1.11-sec015-json`
build `2026081002` is 977,040 bytes when uploaded and has SHA-256
`91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`.
Previous exact firmware `0.1.10-tls-host` build `2026081001` was 972,368 bytes
with SHA-256
`afae56195002d97e2b397b51519f1a06df505d08c5ec180b32bbd25a79650ea8`.
`main` contains the NVS MQTT TLS implementation from PR #7, plus the live
installer/doc fixes for production mDNS hostname support and Mosquitto builds
without `-t`. Previous exact firmware `0.1.9-nvs-tls` build `2026080707` was
970,976 bytes with SHA-256
`3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501`.
TEST-033 passed against an isolated TLS listener and production ACL, then the
NVS profile was cleared and production fallback telemetry recovered. On
2026-08-08, the separately approved incremental production migration activated
listener `8883`, generated a local CA and server certificate with hub hostname
SANs, installed the
tracked per-device ACL, and provisioned only Sunroom Test with a per-device
credential over USB. The first mDNS profile failed on ESP32 DNS
resolution and was replaced with a verified hub TLS hostname profile signed by
the same local CA. Broker logs showed Sunroom Test connecting on `8883` as
its per-device user, and the dashboard API then showed it online, non-stale,
and `OK`. A separately approved hourly OTA rollout then updated Den, Kitchen,
Office, and MasterBedroom to the same TLS-capable firmware on the compiled
`1883` fallback. The controller stopped before LaundryroomAC because
SunroomDoor was offline; no further OTA command was sent.

The capability-key and authenticated-write batch was published in commit
`6c4f8fd`. The database-maintenance, migration/dedupe, CI safeguards, coverage
expansion, firmware native-test, ACL matrix, operator-only OTA authority, spec,
and documentation batch was published in `789c308`; concurrent migration
startup was fixed and pushed in `cacfceb`. PR #4 was merged to `main` as
`e67fa2e`. ArduinoJson release commit `37d6ba5` and bench-evidence commit
`9a8ce9d` were merged through PR #5 as `9029754`; all PR and post-merge `main`
checks passed. The fleet rollout then converged on the exact merged artifact.

`AGENTS.md` remains local/untracked because it identifies the local machine and
workspace. `IoT-code-review.md` remains local/untracked because it contains
review context and identifiers that should not be added to the sanitized public
repository. Its accepted actions are captured in tracked specs/status docs.

The lossless database milestone is implemented with focused tests and a live
systemd run. `iot-home-db-maintenance.timer` is enabled and waiting; its first
oneshot passed and its next run is scheduled for 2026-08-08 at 03:09:59 CDT.
Historical rows must not be pruned; any future archival still requires explicit
approval and restore verification. Continue with the ordered `Pick Up Next`
list above.

The Python suite and its enforced 80% CI floor remain green. Twenty-four
PlatformIO native tests cover sensor filtering, publish policy, ArduinoJson OTA
manifest validation, and MQTT profile validation. SEC-015 source work now uses
ArduinoJson for retained config parsing and device-side JSON construction, and
the exact candidate passed the USB bench gate on Sunroom Test. Firmware
`0.1.8-arduinojson` build `2026080703` remains deployed to `Attic` and
`WallBehindWH`; the other 19 visible active mapped devices are on
`0.1.11-sec015-json`. The retired `UNMAPPED` record and suspect
`GarageDriveway` board are hidden through
`config/retired_devices.json` while historical readings remain preserved.

DR-022 resolves the collector/ACL conflict: desired-version mismatches are
recorded, but the collector has no OTA publish option or command authority.
`iot_home.publish_ota` remains the explicit admin-authenticated path after the
bench gate. TEST-023 passes against an isolated broker using the same tracked
per-device ACL installed by the TLS setup script. That isolated ACL test did
not change the live Mosquitto listener, credentials, or services.

Numbered migrations `001` and `002` now replace ad hoc schema initialization
and record version 2 in `PRAGMA user_version`. The live database is at version
2 with integrity `ok`, 503 preserved legacy exemptions, and no indexed
duplicate groups. All rows from the pre-migration backup remain present and
unchanged. Fresh backup `data/backups/iot-20260807T193918Z.sqlite.gz` was
restore-verified after migration.

Simultaneous dashboard and collector starts at 12:46 CDT exposed a migration
race: one collector attempt saw the column created by the other process and
failed, then systemd restarted it successfully five seconds later. Commit
`cacfceb` re-checks `PRAGMA user_version` under the migration write lock, and a
deterministic concurrent-start test passes. The collector was restarted at
15:14 CDT to load the fix; it reconnected and subscribed immediately without a
warning, traceback, or migration error. Post-restart schema, integrity, row
preservation, and fresh telemetry checks all passed.

The final 2026-08-08 read-only API check showed 22 active mapped devices, with
SunroomDoor offline and 0 active stale devices. Seventeen active mapped devices
are on deployed `0.1.8-arduinojson`; five are on `0.1.9-nvs-tls`. Sunroom Test
uses production TLS listener `8883`; Den, Kitchen, Office, and MasterBedroom
use the compiled `1883` fallback. The separate
`UNMAPPED` record associated with retired `AtticChimney` is online/non-stale on
`0.1.6-recovery` but still excluded from the active mapped fleet. All three
core services remain active and enabled.

## Verification

```bash
cd /home/scotty/IoT
.venv/bin/python -m pytest -q
.venv/bin/pio test -d firmware -e native
.venv/bin/pio run -d firmware
curl -fsS http://127.0.0.1:8000/api/latest
systemctl is-active mosquitto.service iot-home-collector.service iot-home-dashboard.service
git status --short
```
