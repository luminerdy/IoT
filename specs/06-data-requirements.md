# 8. Data Requirements (DATA)

**DATA-001 — Readings store** `MUST`
Table `readings`: append-only telemetry.

| Column | Type | Notes |
| --- | --- | --- |
| id | INTEGER PK | autoincrement |
| device_id | TEXT NOT NULL | `esp32-…`, validated (SEC-012) |
| location | TEXT | mapped location at ingest time |
| sensor_type | TEXT | e.g. `DHT22` |
| temperature | REAL NOT NULL | °F |
| humidity | REAL NOT NULL | %RH |
| datetime | TEXT NOT NULL | device-reported UTC ISO-8601 |
| rssi | INTEGER | dBm |
| status | TEXT | device-reported status |
| seq | INTEGER | device publish sequence |
| created_at | TEXT NOT NULL | hub receive time, UTC |

Indexes: `(device_id, created_at DESC)`, `(created_at DESC)`, and a
**partial UNIQUE index on `(device_id, seq, datetime)` excluding rows where
`datetime` is the pre-NTP sentinel** to enforce FR-024 dedupe with the
FR-015 exemption. `[CHANGE]` `seq` is required at ingest (FR-021); SQLite
treats NULLs as distinct in unique indexes, so a NULL `seq` would silently
disable de-duplication — validation prevents such rows from ever arriving.

**DATA-002 — Device registry** `MUST`
Table `devices`: one row per device — location, firmware_version,
build_number `[CHANGE]`, last_seen, online flag, last_rssi, last_status,
last_seq, last_ip *(added 2026-07-05; diagnostic only, DATA-009
sensitivity applies)*, updated_at. Upserted from telemetry and status
(FR-023).

**DATA-003 — Operator config files** `MUST`
- `locations.json` — `{device_id: display_location}`, strings only.
- `floorplan.json` — optional `backgroundImage` + `zones[]` with
  `location, x, y, w, h` numeric and optional `type`. Validation per FR-035.
Both are git-ignored with committed `.sample.json` templates; invalid files
produce clear errors, never crashes.

**DATA-004 — Timestamp semantics** `MUST`
`created_at` (hub receive time) is authoritative for ordering, staleness,
and history queries. Device `datetime` is informational and may be the
epoch sentinel before NTP sync (FR-015). All timestamps UTC ISO-8601 `Z`.

**DATA-005 — Retention** `MUST` `[CHANGE]`
A scheduled job (systemd timer) deletes `readings` older than the configured
retention (default 90 days) and runs periodic `PRAGMA optimize`/incremental
vacuum. `devices` rows persist until explicitly removed by the operator.

**DATA-006 — Migrations** `MUST` `[CHANGE]`
Schema changes ship as numbered, forward-only migration scripts applied
automatically at collector startup, with the schema version stored in the
database (`PRAGMA user_version` or a `schema_version` table). `CREATE TABLE
IF NOT EXISTS` on every request is not schema management.

**DATA-007 — Backups** `MUST`
Daily online backup (FR-044): `sqlite3 .backup` → integrity check → gzip →
retain last N (default 14) locally; optional off-site copy is opt-in and
excludes the OTA signing key (SEC-007). Restore is documented and rehearsed
quarterly (TEST-030).
*Upstream status (2026-07-08):* a daily 02:05 local SQLite export is
installed before the 02:15 restic/S3 job, and the latest archive
`data/backups/iot-20260708T183106Z.sqlite.gz` was restore-verified. A
restic repository (encrypted, with a forget/prune policy) is live as the
off-site implementation; snapshot `a2980899` and `restic check` were
verified on 2026-07-08. Because restic backs up the whole checkout and
config tree, the exclude list MUST be verified to omit `data/keys/` (the
OTA signing key) — or the encrypted-repo risk explicitly accepted in a
recorded decision. Restic's own repo password and env file are themselves
key material under SEC-007 handling. Local SQLite backup retention pruning
remains part of the rebuild target if it is not handled by an external
cleanup job.

**DATA-008 — OTA artifacts** `SHOULD` (R4)
Staged firmware lives under `data/firmware/<version>/` containing
`firmware.bin` and `manifest.json` (API-014). Staging is idempotent;
re-staging a version overwrites it atomically.

**DATA-009 — Data privacy** `SHOULD`
The database and backups contain room-level occupancy-inferable data; they
are treated as sensitive: file mode 0640, owned by the service user, and
never committed or published (SEC-014). As of 2026-07-05 this includes
device IP addresses (`devices.last_ip`, `deployment_attempts.observed_ip`).

**DATA-010 — Deployment attempts** `MAY` *(added 2026-07-05, implemented
upstream)*
Table `deployment_attempts` records fleet reconciliation history (FR-046):
`device_id`, `from_version`, `to_version` (NOT NULL), `observed_ip`
(validated as an IP at ingest, else NULL), `status`
(`detected` | `published` | `failed`), `rollout_id`, `message`,
`created_at`/`updated_at`; indexed on `(device_id, created_at DESC)`. The
cooldown check (FR-046) queries this table. Rows are subject to a retention
window like readings (DATA-005) so the table does not grow unbounded —
currently unbounded upstream; open item.

**DATA-011 — Hub system metrics** `SHOULD` *(added 2026-08-04)*
Table `system_metrics` stores append-only hub measurements with `metric`,
numeric `value`, and authoritative UTC `created_at`. The initial metric is
`pi_cpu_temperature_f`, sampled every 600 seconds by the collector.
