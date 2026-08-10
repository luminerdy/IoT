# Session Handoff

Last updated: 2026-08-08

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

The local-first IoT stack is running on PiServer. Mosquitto, the collector, and
the dashboard are active and enabled. A parallel production MQTT TLS listener is
active on `8883` alongside the unchanged shared-credential listener on `1883`.
The fleet rollout remains paused; no fleet OTA was sent for the TLS hostname
fix. Sunroom Test is now USB-flashed with bench-only `0.1.10-tls-host` build
`2026081001`; Den, Kitchen, Office, MasterBedroom, and LaundryroomAC remain on
`0.1.9-nvs-tls`, and the rest of the active mapped fleet remains on
`0.1.8-arduinojson`. Sunroom Test's NVS MQTT profile is cleared after bench
validation, so it is intentionally back on compiled shared `1883` fallback.
The separate retired `UNMAPPED` AtticChimney record remains on
`0.1.6-recovery`; it is currently online/non-stale but was intentionally
excluded from active fleet operations.

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
`PiServer.local:8883`; clearing the NVS profile restored the compiled fallback
profile, and a USB reflash of the exact staged `0.1.9-nvs-tls` artifact
`3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501` restored
fresh fallback MQTT telemetry at 17:38:02. Do not re-provision TLS on Sunroom
Test until the ESP32 broker hostname strategy is fixed or deliberately changed.

On 2026-08-10, schema version 2 profiles fixed that hostname strategy by
separating `mqttConnectHost` from `mqttTlsHostname`. Exact firmware
`0.1.10-tls-host` build `2026081001` was USB-flashed to Sunroom Test; binary
SHA-256 was `afae56195002d97e2b397b51519f1a06df505d08c5ec180b32bbd25a79650ea8`.
An isolated user-owned Mosquitto TLS listener on port `8884` used a temporary
CA and a server certificate for `PiServer.local`. Sunroom Test was provisioned
with `mqttConnectHost=10.10.10.123` and `mqttTlsHostname=PiServer.local`,
connected from `10.10.10.124` as `esp32-9c9c1fda3670`, subscribed to its own
command/config topics, and published retained status plus non-retained
telemetry. The temporary broker was stopped, the NVS MQTT profile was cleared,
and fresh production fallback telemetry through shared `1883` was verified.
Production Mosquitto and listener `8883` were not changed because sudo access
was unavailable in this session.

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
2. Decide whether to run a production `8883` schema v2 per-device TLS check on
   Sunroom Test. Use `--connect-host 10.10.10.123 --tls-hostname PiServer.local`;
   keep the NVS profile cleared afterward unless deliberately continuing the
   production migration.
3. Continue the incremental production MQTT TLS/per-device credential migration
   one physical USB device at a time, or continue the remaining SEC-015 config
   parsing and device-side JSON construction work. Do not retire the shared
   `1883` listener or shared fleet credential until every active device has
   been individually provisioned and observed.
4. Continue watchdog/fleet/attic monitoring. If another watchdog relay recovery
   occurs within 24 hours or repeated recoveries appear within a week,
   investigate PiServer power/network/system health before relying on the relay.
5. Decide whether to remap or re-retire the returned `UNMAPPED` device.

## Working Tree

The working tree contains the schema v2 MQTT TLS hostname fix on top of `main`.
Exact firmware `0.1.10-tls-host` build `2026081001` is 972,368 bytes when
uploaded and has SHA-256
`afae56195002d97e2b397b51519f1a06df505d08c5ec180b32bbd25a79650ea8`.
`main` contains the NVS MQTT TLS implementation from PR #7, plus the live
installer/doc fixes for production mDNS hostname support and Mosquitto builds
without `-t`. Previous exact firmware `0.1.9-nvs-tls` build `2026080707` was
970,976 bytes with SHA-256
`3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501`.
TEST-033 passed against an isolated TLS listener and production ACL, then the
NVS profile was cleared and production fallback telemetry recovered. On
2026-08-08, the separately approved incremental production migration activated
listener `8883`, generated a local CA and server certificate with `PiServer`,
`PiServer.local`, `piserver.local`, and `iot-pi.local` SANs, installed the
tracked per-device ACL, and provisioned only Sunroom Test with a per-device
credential over USB. The first `iot-pi.local` profile failed on ESP32 DNS
resolution and was replaced with a verified `PiServer.local` profile signed by
the same local CA. Broker logs showed Sunroom Test connecting on `8883` as
`esp32-9c9c1fda3670`, and the dashboard API then showed it online, non-stale,
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

The Python suite and its enforced 80% CI floor remain green. Twenty-three
PlatformIO native tests cover sensor filtering, publish policy, ArduinoJson OTA
manifest validation, and MQTT profile validation. Firmware
`0.1.8-arduinojson` build `2026080703` remains deployed to 21 active mapped
devices; only Sunroom Test is on the newer bench candidate. The retired
`UNMAPPED` record was not changed.

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
