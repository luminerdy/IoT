# IoT Home Monitoring — Specification Package

Spec-driven development package for rebuilding the local-first ESP32 home
monitoring system (github.com/luminerdy/IoT). The goal is that a competent
developer (or agent) can rebuild the system from these documents alone,
without reverse-engineering behavior from the current code.

## Documents

| File | Contents |
| --- | --- |
| [01-product-overview.md](01-product-overview.md) | Product overview, MVP scope, feature inventory |
| [02-functional-requirements.md](02-functional-requirements.md) | FR-xxx — what the system does |
| [03-non-functional-requirements.md](03-non-functional-requirements.md) | NFR-xxx — reliability, performance, maintainability |
| [04-security-requirements.md](04-security-requirements.md) | SEC-xxx — security requirements and threat notes |
| [05-technical-requirements.md](05-technical-requirements.md) | TECH-xxx — stack, tooling, CI constraints |
| [06-data-requirements.md](06-data-requirements.md) | DATA-xxx — schema, retention, backup |
| [07-api-interface-requirements.md](07-api-interface-requirements.md) | API-xxx — MQTT topics, payloads, HTTP endpoints |
| [08-acceptance-criteria.md](08-acceptance-criteria.md) | AC-xxx — verifiable done-ness per feature |
| [09-testing-strategy.md](09-testing-strategy.md) | TEST-xxx — test levels, tooling, coverage gates |
| [10-rebuild-roadmap.md](10-rebuild-roadmap.md) | Phased rebuild plan + documentation plan |

## Conventions

- **Requirement IDs** are permanent. Never renumber; deprecate with a
  `(DEPRECATED)` marker instead.
- **Priority** uses MoSCoW: `MUST` (MVP-blocking), `SHOULD` (target release),
  `MAY` (optional/backlog).
- **Traceability:** every FR/SEC requirement maps to at least one AC and one
  TEST entry. Acceptance criteria reference the requirements they verify.
- Keywords MUST / MUST NOT / SHOULD / MAY are used per RFC 2119.

## Amendment log

- **2026-07-10** — attic/dashboard operations update: specified the distinct
  Attic history group, alphabetical device-card ordering, hottest-first Latest
  Readings ordering, and 75 F / 100 F graph references; added AC-018 and
  TEST-007 for traceability.

- **2026-07-08** — operations/admin update: recorded the deployed
  dashboard device mapping admin workflow (`GET/POST /api/locations`),
  the daily 02:05 local SQLite backup schedule, the 02:15 restic/S3
  schedule, verified snapshot `a2980899`, and the restore-verified local
  archive `data/backups/iot-20260708T183106Z.sqlite.gz`.

- **2026-07-05** — upstream repo review (commits through `4d0e5cc`):
  adopted the fleet-deployed **OTA signature contract v2** (dual signature
  with canonical metadata payload + NVS build high-water mark) as normative
  in API-013/SEC-006/FR-012, superseding the 2026-07-02 draft; recorded
  upstream's interim shared-user ACL model (SEC-003), Basic-auth add/remove
  history (SEC-009), non-retained telemetry, and collector dedupe;
  strengthened SEC-016
  rationale (firmware images embed device secrets); added FR-046/DATA-010/
  AC-045 (fleet version reconciliation, upstream feature); added `localIp`
  to API-010/011 and `last_ip` to DATA-002; noted restic as the DATA-007
  off-site implementation with a signing-key-exclusion check; updated the
  roadmap status with upstream progress and remaining gaps.

- **2026-07-02** — post-implementation review: recorded the SEC-009 Basic
  auth decision and startup-refusal rule (AC-016); added SEC-016 (firmware
  capability key, AC-017); made `seq` mandatory in telemetry (FR-021,
  API-010, AC-009); exempted pre-NTP sentinel rows from dedupe via partial
  index (FR-015/FR-024/DATA-001, AC-008); added the normative OTA signature
  contract to API-013; added FR-045 (device retirement); documented the
  localhost 1883 listener decision (SEC-001), the 1024-byte telemetry
  budget (API-010), `/media/` root (API-026), `buildNumber` in status
  (API-011); amended TEST-040's per-module gate; flagged the IDF-5
  watchdog API change (TECH-012).

## Source of truth

Where the current implementation and this spec disagree, **this spec wins**.
Known deliberate departures from the current code are marked `[CHANGE]` —
these are fixes for defects or risks identified in the 2026-07 architecture
and security review. Some `[CHANGE]` items are already implemented upstream
(for example non-retained telemetry and OTA anti-rollback); others remain
open rebuild targets, including authenticated dashboard defaults and
TLS/per-device MQTT credentials.
