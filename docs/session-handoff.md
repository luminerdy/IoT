# Session Handoff

Last updated: 2026-08-05

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
the dashboard are active and enabled. The 2026-08-05 dashboard check reports
23 online, non-stale records on `0.1.6-recovery`: 22 active mapped devices and
one online `UNMAPPED` device, consistent with the temporarily retired
`AtticChimney` reporting again.

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

## Pick Up Next

1. Monitor the Pi3 watchdog at its production 10-minute failure threshold and
   investigate any repeated relay recoveries.
2. Decide whether to remap or re-retire the returned `UNMAPPED` device.
3. Continue normal fleet monitoring and replace retired `AtticChimney` when
   attic access is safe.

## Working Tree

The recovery firmware, deployment tracking, and external watchdog work are
being prepared for publication on the existing GitHub branch and PR.

## Verification

```bash
cd /home/scotty/IoT
.venv/bin/pio run -d firmware
.venv/bin/python -m pytest -q
.venv/bin/pio check -d firmware
curl -fsS http://127.0.0.1:8000/api/latest
git status --short
```
