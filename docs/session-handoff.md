# Session Handoff

Last updated: 2026-08-07

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

## Current State

The local-first IoT stack is running on PiServer. Mosquitto, the collector, and
the dashboard are active and enabled. Twenty-one active mapped devices remain
on `0.1.6-recovery`; the USB-connected `Sunroom Test` bench device is on
`0.1.8-arduinojson` and reporting over Wi-Fi from `/dev/ttyUSB0`. No fleet OTA
was sent for the ArduinoJson candidate.

Firmware downloads on live port `8000` now require a constant-time-checked
capability key or dashboard Basic auth. Missing/wrong keys return 401; a keyed
download was verified byte-for-byte against the staged production artifact.
Read-only dashboard access remains explicitly open on the home LAN, while
`POST /api/locations` requires separate dashboard credentials. Mapping updates
are locked against concurrent lost updates, request database connections close
explicitly, and schema initialization runs only at startup. Credentials remain
local in protected environment files and are not tracked.

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
- Nine TEST-012 cases plus the six sensor-core cases pass natively. The ESP32
  build and static analysis pass, and 114 Python tests pass at 91.93% coverage.
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

## Pick Up Next

1. Continue with NVS-provisioned per-device credentials/TLS, then complete the
   remaining SEC-015 config parsing and device-side JSON construction work.
   Dashboard static-asset extraction follows those security milestones.
2. Continue watchdog/fleet/attic monitoring and decide whether to remap or
   re-retire the returned `UNMAPPED` device.

## Working Tree

The capability-key and authenticated-write batch was published in commit
`6c4f8fd`. The database-maintenance, migration/dedupe, CI safeguards, coverage
expansion, firmware native-test, ACL matrix, operator-only OTA authority, spec,
and documentation batch was published in `789c308`; concurrent migration
startup was fixed and pushed in `cacfceb`. PR #4 was merged to `main` as
`e67fa2e`. The ArduinoJson work is currently uncommitted on local branch
`agent/arduinojson-manifest-tests`; no fleet OTA was performed.

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

The Python suite now has 114 passing tests at 91.9% branch-aware coverage, with
an enforced 80% CI floor. Fifteen PlatformIO native tests cover sensor filtering,
publish policy, and ArduinoJson OTA manifest validation. Local firmware
candidate `0.1.8-arduinojson` build `2026080702` passed task-focused USB
parser/preflight validation on Sunroom Test but has not been staged or deployed
to the fleet. The source now selects final candidate build `2026080703`; it is
pending committed-artifact signed OTA and a fresh bench soak. Complete TEST-030
still gates any rollout.

DR-022 resolves the collector/ACL conflict: desired-version mismatches are
recorded, but the collector has no OTA publish option or command authority.
`iot_home.publish_ota` remains the explicit admin-authenticated path after the
bench gate. TEST-023 passes against an isolated broker using the same tracked
per-device ACL installed by the TLS setup script. The live Mosquitto listener,
credentials, services, and fleet were not changed.

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

The final 2026-08-07 read-only API check showed all 22 active mapped devices
online and non-stale on deployed `0.1.6-recovery`. The separate `UNMAPPED`
record associated with retired `AtticChimney` is also online and currently
non-stale. All three core services remain active and enabled.

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
