# 12. Rebuild Roadmap

Phased so the live fleet (currently 23 devices) keeps reporting throughout. Each phase
ends with its listed acceptance criteria green. Old and new components may
run side by side (different systemd units / DB file) during migration.

> **Status (2026-07-02):** the rebuild tree implements the hub scope of
> R0–R2 plus the firmware code for R3/R4 (97 passing tests, 83 % coverage,
> lint clean; dashboard smoke-tested live). Still open: TEST-020/TEST-023
> broker-in-CI integration tests, the first CI firmware compile, all
> hardware bench criteria (TEST-030: AC-001/002, AC-020/021, AC-030…032,
> AC-044), and fleet migration. FR-045 (device retirement) is spec'd but
> not implemented.
>
> **Status (2026-07-05, reviewed at commit `4d0e5cc` plus local
> working-tree changes):** the live system has landed several R0/R2/R4
> outcomes: platform pinned (`espressif32@6.10.0`) with CI firmware compile;
> telemetry publish now uses `retain=false`; collector/database dedupe exists
> for repeated `(device_id, seq, datetime)` messages; ACLs protect the 1883
> listener with a separate `iot-admin` publisher; Basic auth was added and
> then locally removed by preference; **anti-rollback OTA validated on the
> bench and rolled to all 21 devices** (build-number NVS high-water mark +
> metadata signature, DR-019); restic off-site backups; and a new
> fleet-reconciliation feature (FR-046/DATA-010/AC-045).
> **Consequence for the rebuild:** preserve the deployed OTA signature
> contract v2 (API-013); do not regress to the superseded 2026-07-02 draft.
> Items still open against this spec: TLS + per-device MQTT credentials
> (SEC-001/002), seq-mandatory collector
> validation and topic/payload identity checks (FR-021/FR-022), database
> migrations and partial unique index (DATA-001/DATA-006), preservation and
> capacity monitoring (DATA-005), and restic exclude verification for the
> signing key (DATA-007).
>
> **Status (2026-08-06):** SEC-016 capability-key firmware downloads and the
> chosen SEC-009 policy are implemented and live. Read-only dashboard routes
> are explicitly open on the home LAN; location writes require Basic auth;
> firmware downloads require Basic auth or a capability key. Location updates
> are serialized, per-request SQLite connections close explicitly, and schema
> initialization runs only at startup. The next prioritized
> milestones are lossless data preservation/capacity monitoring, CI
> lint/coverage/secret scanning, the OTA publisher/ACL decision and ACL matrix
> tests, migrations, ArduinoJson plus
> native firmware tests, then NVS-provisioned per-device credentials and TLS.

## R0 — Foundations (no behavior change)

- Adopt this spec package into the repo as `specs/`; spec-first workflow
  (NFR-014).
- Repo scaffolding: target folder structure (below), `pyproject.toml`,
  ruff config, migration framework skeleton.
- CI per TECH-020: lint, tests, **firmware compile**, native firmware tests,
  secret scan (TEST-041/042).
- Pin `espressif32` platform (TECH-010); migrate mbedTLS calls (TECH-012)
  while behavior is otherwise frozen.
- Decide and record: git-history identifier scrub vs. acceptance (SEC-014).

**Exit:** CI green including firmware build; no fleet change.

## R1 — Core pipeline (MVP part 1)

- Rebuild collector against FR-020…FR-025 with migrations (DATA-006),
  dedupe index (DATA-001), preservation/capacity job (DATA-005).
- Shared MQTT client helper (NFR-009); CLI contracts API-030/031.
- Simulator updated (no retained telemetry).
- Tests: TEST-001/002/003/005/006/020.

**Exit:** AC-004…AC-007, AC-041, AC-043.

## R2 — Dashboard + secure access (MVP part 2)

- Dashboard rebuilt: static assets (TECH-004), APIs per API-020…026,
  staleness FR-031, history FR-032.
- Authentication in front of the dashboard (SEC-009); traversal tests
  pinned (TEST-021); contract tests (TEST-022).
- Broker hardening becomes the default: TLS-only listener, ACLs on every
  listener, per-device provisioning CLI (SEC-001…004, FR-042).
- Parameterized install (NFR-008, TECH-005) replacing hardcoded-path units.

**Exit — MVP done:** AC-010…AC-015, AC-033, AC-042.

## R3 — Firmware v2 + runtime config

- Firmware restructured per TECH-013 (testable core), ArduinoJson
  (SEC-015), bounded reconnect + watchdog (FR-014), build metadata
  (TECH-014), telemetry retain=false (FR-007), TLS + per-device creds
  baked in.
- Runtime config path (FR-009, FR-041, API-012).
- Flash bench device by USB; migrate fleet in small batches using the
  existing (old) OTA path as the bridge.

**Exit:** AC-001…AC-003, AC-020/021, AC-044 on bench; fleet ≥ 50 % migrated.

## R4 — Signed OTA v2 with anti-rollback

- Staging/signing CLI on `cryptography` (FR-040, TECH-002), manifest with
  signed `buildNumber` (API-013/014, SEC-006), device-side gate order
  FR-011/FR-012, firmware serving behind auth (FR-037, F-21 removal).
- Bench-validate the full failure matrix (AC-031) plus rollback rejection
  (AC-032); then batch rollout per TEST-043.

**Exit:** AC-030…AC-032; whole fleet on v2 firmware; old OTA path deleted.

## R5 — Operator experience

- Rotating views, floorplan, suspect-reading flags (FR-034…FR-036) on the
  static-asset UI.
- Summary stats (FR-033), device mapping admin, ops polish, backup schedule
  and preservation/capacity automation.

**Exit:** AC-011 extended views verified on the 1080p wall display; AC-040.

## Decommissioning rule

A legacy module is deleted (not commented out) in the same PR that lands its
replacement's passing acceptance criteria. No parallel dead code beyond one
phase.

## Target repository structure

```
specs/                      # this package
app/iot_home/
  db.py  migrations/  locations.py  floorplan.py  mqtt_schema.py
  mqtt_client.py            # shared paho helper
  collector.py
  dashboard/
    server.py
    static/ (index.html, app.js, style.css)
  ota/ (stage.py, publish.py, config.py)
  simulator.py
firmware/
  platformio.ini            # pinned
  lib/sensor_core/          # pure logic, natively tested
  src/main.cpp
  test/                     # native unit tests
scripts/ (install_systemd_services.sh, add_mqtt_device_user.sh,
          configure_mosquitto_tls_acl.sh, backup_sqlite.sh,
          preservation/capacity hooks)
deploy/systemd/ (*.service.template + generator)
tests/
docs/                       # see §13
```

---

# 13. Suggested Documentation Files

Replace the current eleven overlapping docs with eight purposeful ones:

| File | Purpose | Replaces |
| --- | --- | --- |
| `README.md` | What it is, status badge, quickstart pointer, layout | current README (trimmed) |
| `docs/architecture.md` | Components, data flow diagram, design principles, trust boundaries | `Local-First-Architecture.md` + parts of decision-record |
| `docs/decisions/` (ADR-NNN files) | One file per accepted decision, immutable | `decision-record.md` |
| `docs/install.md` | Parameterized fresh-Pi install, provisioning a device end-to-end (AC-042 script) | phase-1/2 runbooks |
| `docs/operations.md` | Day-2 runbook: OTA rollout procedure (TEST-043), config changes, backup/restore drill, adding/retiring a device, troubleshooting | phase-4 runbook, backup-runbook, security-hardening (ops parts) |
| `docs/security.md` | Threat model, security requirements summary, key rotation, incident response (lost device → revoke credential) | `security-hardening.md` |
| `docs/api.md` | Generated/maintained from API-xxx: MQTT contract + HTTP endpoints | `mqtt-schema.md` |
| `CHANGELOG.md` | Dated, human-readable changes | `progress-log.md`, `current-status.md` |

Rules:
- Specs (`specs/`) say *what must be true*; `docs/` say *how to operate it*.
  Don't duplicate requirement text into docs — link to IDs.
- `current-status.md`-style session journaling moves out of the repo (or
  into a git-ignored `notes/`); the public repo carries only durable docs
  (supports SEC-014).
- Every PR that changes observable behavior touches: the relevant spec file,
  the relevant doc, and `CHANGELOG.md`.
