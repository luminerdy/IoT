# 11. Testing Strategy (TEST)

Principle: everything that can run on a CI host does; the physical bench
device is reserved for what only hardware can prove (radio, flash, sensor).

## 11.1 Unit tests (CI, every commit)

**TEST-001 — Collector validation** `MUST`
Table-driven tests for telemetry/status validation (FR-021): missing fields,
range edges (−40/185 °F, 0/100 %), non-numeric values, malformed JSON,
device-ID pattern (SEC-012), topic/payload identity mismatch (FR-022).

**TEST-002 — Persistence & dedupe** `MUST`
`record_telemetry`/`record_status` upsert behavior, last-seen preservation,
unique-index dedupe, sentinel exemption, preserved legacy-duplicate handling
(FR-024), and history clamping.

**TEST-003 — Location & floorplan config** `MUST`
Valid/invalid `locations.json` and `floorplan.json` parsing (DATA-003),
mapping precedence (FR-025). (Exists today; carry forward.)

**TEST-004 — OTA staging** `MUST` (R4)
Manifest generation, SHA-256 correctness, signature verifiable with the
public key via `cryptography`, path-safe version labels, `buildNumber`
inclusion in signed material (SEC-006), stage-only mode.

**TEST-005 — Preservation maintenance** `MUST`
Maintenance preserves every historical row, reports database/storage capacity,
and is idempotent. Any future archive test must prove copied row counts and
integrity before an explicitly approved live-table removal step.

**TEST-006 — Migrations** `MUST`
Fresh DB and each prior schema version migrate to current; version recorded.
Migration tests also prove idempotence, transaction rollback on incompatible
legacy schemas, rejection of newer unknown versions, and value preservation for
pre-existing telemetry columns.

**TEST-007 — Dashboard presentation contract** `SHOULD` (R5)
Inspect the generated dashboard page for the location sort, hottest-first
Latest Readings sort, distinct Attic history group, and fixed 75 F / 100 F
graph references (FR-030, FR-032, AC-018). Exercise the rendered behavior in
a browser after material JavaScript changes.

## 11.2 Firmware native tests (CI host, no hardware)

**TEST-010 — Filter logic** `MUST`
Median window, plausibility bounds, outlier candidate/confirmation state
machine (FR-003…FR-005) as pure-C++ tests (PlatformIO `test` on `native`).

**TEST-011 — Publish policy** `MUST`
Interval vs. confirmed-change publishing decisions (FR-006) with simulated
clocks.

**TEST-012 — Manifest validation** `MUST` (R4)
Field parsing, hex decoding, size/sha/signature/buildNumber gate ordering
(FR-010…FR-012) with the download and flash layers faked.

## 11.3 Integration tests (CI, real broker)

**TEST-020 — End-to-end ingest** `MUST`
Spin up Mosquitto in CI; run the simulator and collector; assert rows,
device state, offline-via-LWT, and duplicate-delivery idempotence
(AC-004…AC-007).

**TEST-021 — HTTP handler security** `MUST`
Requests against a live dashboard process: path traversal corpus (encoded,
doubled, symlink) → 404 (AC-015); parameter clamping (AC-012); auth
required (AC-014); error responses leak no paths (API-027).

**TEST-022 — API contract** `MUST`
Golden-file JSON shape tests for `/api/latest`, `/api/history`,
`/api/floorplan` (API-021…023) so UI and firmware can rely on the contract.

**TEST-023 — Broker ACL matrix** `SHOULD`
Scripted matrix using two device users + collector + admin: each identity
attempts each topic verb; assert allow/deny per SEC-003 (AC-033).
*Implemented 2026-08-07:* pytest launches a temporary authenticated Mosquitto
broker with `deploy/mosquitto/iot-home-per-device.acl`, verifies actual message
delivery for reads and broker forwarding for writes, then shuts it down. CI
installs Mosquitto solely for this isolated test.

## 11.4 Hardware bench validation (manual, gated)

**TEST-030 — Release bench checklist** `MUST`
A written checklist executed on the USB-recoverable bench device before any
fleet rollout: AC-001, AC-020/021, AC-030…AC-032, AC-044. Results recorded
(date, firmware build, outcome) in the ops log.

**TEST-031 — Restore drill** `MUST`
Quarterly, and after backup schedule changes: restore the latest local
SQLite backup to a scratch DB, verify integrity and recency, then verify the
latest restic/S3 snapshot includes the DB and critical config files
(AC-040, AC-040a).

**TEST-032 — Fresh-install drill** `SHOULD`
Once per major release: AC-042 on a clean SD image (or container
approximation of the install script).

## 11.5 Gates and tooling

**TEST-040 — Coverage gate** `MUST`
`pytest --cov` ≥ 80 % line coverage over hub packages, enforced in CI
(`--cov-fail-under=80`). *Amended 2026-07-02:* the original per-module 90 %
gate for the HTTP handler and validation modules is not natively enforceable
by coverage tooling; those modules are instead reviewed at report level with
a ≥ 85 % target. Network-bound service loops (`main()` connect loops,
simulator) are covered by TEST-020 integration tests, not unit coverage.
*Implementation note (2026-08-07):* the 114-test suite measures 91.9% with
branch coverage enabled, and CI enforces the required 80% floor. Collector,
dashboard HTTP/security, config-publisher, and OTA staging/publishing paths are
included in the expanded coverage.

**TEST-041 — Static analysis** `MUST`
ruff (lint + format) for Python; `platformio check` retained for firmware
static analysis **in addition to** a real `platformio run` compile
(TECH-020).

**TEST-042 — Secret/identifier scan** `MUST`
CI scan (e.g., gitleaks + a custom pattern list for local IPs/MACs/real
device IDs) on every push (SEC-014).

**TEST-043 — Rollout safety rule** `MUST`
OTA rollouts proceed bench → 1 device → small batch → fleet, with telemetry
observed at each step; the rule lives in the ops runbook and the rollout
CLI prints it. For each device, observe `downloading → rebooting` and confirm
fresh dashboard telemetry on the target version. A missing terminal status or
failure to converge pauses expansion of the rollout. Firmware-download URLs
must be verified from the sensor network; use a reachable LAN address when
`.local` name resolution is not available to ESP32 clients.
