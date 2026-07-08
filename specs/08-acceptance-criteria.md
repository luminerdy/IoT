# 10. Acceptance Criteria (AC)

Given/When/Then criteria per feature area. Each AC lists the requirements it
verifies. An AC passes only when demonstrated by an automated test or a
recorded bench procedure.

## Telemetry pipeline

**AC-001** (FR-002…FR-006)
Given a bench device at stable room conditions, when it runs for 30 minutes,
then it publishes at the report interval (±5 s), publishes early only on a
confirmed ≥ threshold change, and publishes no reading outside plausible
ranges.

**AC-002** (FR-004)
Given a single spurious DHT22 spike ≥ 8 °F, when it is not confirmed by 3
consecutive similar samples, then it never appears in published telemetry
and `numFilteredReadings` increments.

**AC-003** (FR-007, API-001)
Given a fresh MQTT subscriber connecting after telemetry was published, when
it subscribes to the telemetry topic, then it receives **no** retained
telemetry message.

**AC-004** (FR-020, FR-021, FR-023)
Given the collector running, when a valid telemetry message arrives, then a
`readings` row and updated `devices` row exist within 1 s; when a message
with missing fields, out-of-range values, or malformed JSON arrives, then no
row is written, a rejection is logged with reason, and the collector stays up.

**AC-005** (FR-024, DATA-001)
Given a telemetry message delivered twice (QoS-1 redelivery or replay), when
both copies arrive, then exactly one `readings` row exists.

**AC-006** (FR-022)
Given a message on `home/sensors/esp32-aaaaaaaaaaaa/telemetry` whose payload
says `"deviceId": "esp32-bbbbbbbbbbbb"`, then it is rejected and logged.

**AC-007** (FR-008)
Given a device that loses power, when the broker LWT fires, then the
dashboard shows the device offline within 90 s of keepalive expiry.

**AC-008** (FR-015 amendment, FR-024) *(added 2026-07-02)*
Given a device that publishes `seq=1` with the sentinel timestamp, reboots,
and publishes `seq=1` with the sentinel timestamp again, then both readings
are stored — sentinel rows are exempt from de-duplication.

**AC-009** (FR-021) *(added 2026-07-02)*
Given telemetry lacking `seq`, then it is rejected and logged; no row is
written.

## Dashboard

**AC-010** (FR-030, API-021)
Given 21 devices with recent readings, when `/api/latest` is called, then it
returns one entry per device with correct mapped locations, ordered by
location, in < 200 ms.

**AC-011** (FR-031)
Given a device online but silent for longer than `stale-seconds`, then the
UI shows it as stale (amber), distinct from offline (red) and fresh (green).

**AC-012** (FR-032, API-022, SEC-012)
Given `?hours=9999&limit=999999`, then the server clamps to 168 h / 50000
rows and returns 200 — never an error or unbounded query.

**AC-013** (SEC-011)
Given a device whose location string is `<img src=x onerror=alert(1)>`, when
the dashboard renders it, then the string appears as literal text and no
script executes.

**AC-014** (SEC-009)
Given a client on the LAN without credentials, when it requests any
dashboard or firmware URL, then it receives 401/403 (or connection refused,
per the chosen mechanism) — verified from a second machine.

**AC-015** (SEC-010, TEST-021)
Given requests for `/assets/../../etc/passwd`, `%2e%2e` variants, and a
symlink inside the asset dir pointing outside it, then all return 404 and no
out-of-root file content is ever served.

**AC-016** (SEC-009) *(added 2026-07-02)*
Given `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD` are unset, when the
dashboard is started with a non-loopback bind and without
`--allow-unauthenticated`, then it exits with an error citing SEC-009; a
loopback bind starts normally.

**AC-017** (SEC-016) *(added 2026-07-02)*
Given a configured `FIRMWARE_DOWNLOAD_KEY`, then `/firmware/…?key=<correct>`
and operator Basic auth each return the image; a wrong or missing key
returns 401; the key comparison is constant-time.

## Configuration (R3)

**AC-020** (FR-009, API-012)
Given a retained config `{"reportIntervalSeconds": 60}`, when the device
(re)connects, then it applies 60 s, publishes an `applied` response echoing
the active config, and resumes the default when the retained payload is
cleared.

**AC-021** (FR-009)
Given `{"reportIntervalSeconds": 5}` (out of range), then the device rejects
the whole document, keeps its current config, and publishes `rejected` with
a reason.

## OTA (R4)

**AC-030** (FR-010, FR-011, FR-040)
Given a staged, signed image and an OTA command to the bench device, then
the device downloads, verifies size + SHA-256 + signature, reports
`downloading → rebooting`, boots the new version, and its next telemetry
shows the new `firmwareVersion`/`buildNumber`.

**AC-031** (FR-011)
Each of: wrong URL, truncated download, corrupted image (bad SHA), valid
SHA with invalid signature, oversized image — results in `rejected`/`failed`
status with the correct reason, and the device continues running the old
firmware. (Matches the existing Phase-4 bench validation set.)

**AC-032** (FR-012, SEC-006)
Given a validly signed manifest whose `buildNumber` ≤ the highest booted
build (NVS high-water mark), then the device rejects it without
downloading, with reason indicating rollback protection.
*Validated upstream 2026-07-04:* the bench device on the anti-rollback
firmware rejected a signed lower-build command with
`firmware rollback rejected`; AC-030/AC-031 equivalents were bench-run
before the 21-device batch rollout.

**AC-045** (FR-046, DATA-010) *(added 2026-07-05)*
Given a desired firmware version configured and a device reporting an
older version, then exactly one deployment attempt is recorded per cooldown
window; with `--auto-ota` enabled, the staged signed manifest for the
desired version is published to that device's command topic and the attempt
records `published` (or `failed` with a reason); without `--auto-ota`,
nothing is published.

**AC-033** (SEC-003)
Given a client authenticated with device-A credentials, when it publishes to
device-B's `command` topic, then the broker denies it (verified by ACL test,
TEST-023).

## Operations

**AC-040** (FR-044, DATA-007, TEST-030)
Given the backup script has run, when the newest backup is restored to a
scratch path and queried, then integrity_check returns `ok` and the latest
reading matches production within the backup window.

**AC-040a** (FR-044, DATA-007, TEST-030)
Given the scheduled backup window has passed, when cron logs, the latest
local SQLite archive, and the latest restic snapshot are inspected, then the
local archive predates the restic snapshot, both are current for the day, and
a restored database copy passes `PRAGMA integrity_check`.

**AC-041** (NFR-007, DATA-005)
Given readings older than the retention window, when the retention job runs,
then they are deleted and the dashboard/history APIs still work.

**AC-042** (NFR-008)
Given a clean Raspberry Pi OS image and the install docs, when a new
operator follows them with no other sources, then the full stack is running
under systemd with TLS MQTT, ACLs, and an authenticated dashboard, and a
simulated device's telemetry appears on the dashboard.

**AC-043** (NFR-005)
Given `systemctl kill` of collector and dashboard at random points under
simulated load, when they restart, then no data is corrupted or duplicated
and the dashboard recovers without intervention.

**AC-044** (FR-014, NFR-006)
Given the WiFi AP goes down for 20 minutes and comes back, then every bench
device resumes reporting without manual power-cycling.
