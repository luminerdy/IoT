# 4. Functional Requirements (FR)

Grouped by component. Priority: MUST = MVP-blocking, SHOULD = target release,
MAY = backlog.

## 4.1 Device / Firmware

**FR-001 — Device identity** `MUST`
Each device derives a stable device ID from its WiFi MAC address in the form
`esp32-<12 lowercase hex chars>`. The ID is used as the MQTT client ID, MQTT
username, and topic segment.

**FR-002 — Sensor sampling** `MUST`
The device samples the DHT22 approximately every 2 seconds. Failed reads are
counted (`numReadErrors`) and never published.

**FR-003 — Plausibility filtering** `MUST`
Readings outside −40…140 °F or 0…100 %RH are discarded and counted
(`numFilteredReadings`).

**FR-004 — Outlier rejection** `MUST`
A reading deviating more than 8 °F from the median of the recent sample
window (size 5) is held as a candidate outlier; it is only accepted after 3
consecutive samples within 2 °F of the candidate value (a real step change),
otherwise it is discarded and counted.

**FR-005 — Median smoothing** `MUST`
Published temperature and humidity are the median of the current sample
window, not raw values.

**FR-006 — Publish policy** `MUST`
The device publishes telemetry when either: (a) the report interval has
elapsed (default 600 s), or (b) the filtered temperature differs from the
last published temperature by at least the change threshold (default 1.0 °F)
for 3 consecutive samples. First reading after boot always publishes.

**FR-007 — Telemetry payload** `MUST`
Telemetry is published to the device's telemetry topic (API-001) with the
JSON schema defined in API-010, QoS 1, **retain=false**. `[CHANGE]` (current
firmware retains telemetry, causing duplicate ingestion on collector restart).

**FR-008 — Status and last-will** `MUST`
On connect the device publishes a retained `online` status (API-011) and
registers an MQTT last-will publishing retained `offline` on the same topic.

**FR-009 — Runtime configuration** `SHOULD` (R3)
The device subscribes to its retained config topic. It accepts
`reportIntervalSeconds` (10–3600) and `changeThresholdF` (0.1–10.0), applies
valid values, resets its filter state, and publishes an applied/rejected
response (API-012). An empty retained payload resets defaults. Out-of-range
or unparseable config is rejected in full (no partial application).

**FR-010 — OTA command handling** `SHOULD` (R4)
The device subscribes to its command topic and accepts only the `ota_update`
command with fields per API-013. Any other command is rejected with a status
message.

**FR-011 — OTA verification** `SHOULD` (R4)
Before applying an update the device MUST verify, in order: exact content
length (when size is provided), SHA-256 of the downloaded image against the
manifest, and a P-256 ECDSA signature of that digest against the baked-in
public key. Any failure aborts the update, publishes a status, and leaves
the running firmware untouched.

**FR-012 — OTA anti-rollback** `MUST` (R4) `[CHANGE]` *(updated 2026-07-05)*
The signed manifest MUST include a monotonically increasing unsigned 32-bit
`buildNumber` covered by a signature (contract in API-013). The device
persists the highest build number it has ever booted in NVS and rejects any
update whose `buildNumber` is not strictly greater than
max(stored, compiled-in). Commands without a positive `size` are rejected
before download. *Status: implemented and fleet-validated upstream on
2026-07-04 (DR-019): a signed lower-build command was rejected with
`firmware rollback rejected` on the bench device before batch rollout.*

**FR-013 — OTA progress reporting** `SHOULD` (R4)
The device publishes OTA lifecycle states (`downloading`, `rejected`,
`failed`, `rebooting`) with human-readable reasons to its OTA status topic.

**FR-014 — Network resilience** `MUST` `[CHANGE]`
WiFi and MQTT reconnects use bounded retries with backoff. The device
enables a hardware/task watchdog such that no network outage state can wedge
the device; if connectivity cannot be restored within 15 minutes, the device
reboots itself. (Current firmware spins forever in `connectWifi()`.)

**FR-015 — Time handling** `MUST`
The device syncs time via NTP. Until sync succeeds, telemetry carries the
sentinel timestamp `1970-01-01T00:00:00Z`; consumers treat received-time as
authoritative (see DATA-004).
*Amendment (2026-07-02):* readings carrying the sentinel timestamp are
exempt from de-duplication (FR-024, DATA-001). Device `seq` resets on boot,
so sentinel rows from successive quick reboots would otherwise collide on
the dedupe key and be wrongly dropped. Accepted trade-off: a rare QoS-1
redelivery of a pre-sync reading may store a duplicate row.

## 4.2 Hub — Collector

**FR-020 — Subscription** `MUST`
The collector subscribes (QoS 1) to all device telemetry and status topics
(`home/sensors/+/telemetry`, `home/sensors/+/status`).

**FR-021 — Validation** `MUST`
Telemetry lacking `deviceId`, `datetime`, `temperature`, `humidity`, or
`seq`, or with temperature outside −40…185 °F or humidity outside 0…100 %,
is rejected and logged; it is never persisted. `seq` is mandatory as of
schema 3.0 because it forms the dedupe key (FR-024) — without it,
de-duplication is silently inert. Status messages require `deviceId` and a
`status` of `online`/`offline`. Malformed JSON never crashes the collector.

**FR-022 — Identity cross-check** `SHOULD` `[CHANGE]`
The collector verifies that the payload `deviceId` matches the device-ID
segment of the topic the message arrived on; mismatches are rejected and
logged (defends against a credentialed client impersonating another device
in the payload while ACLs constrain only the topic).

**FR-023 — Persistence** `MUST`
Valid telemetry is inserted into `readings` and upserts the `devices` row
(last seen, firmware version, RSSI, online). Status messages upsert `devices`
only.

**FR-024 — De-duplication** `MUST` `[CHANGE]`
A reading with the same (`device_id`, `seq`, `datetime`) as an existing row
is ignored. This makes ingestion idempotent under QoS-1 redelivery and any
retained-message replay. Readings whose `datetime` is the pre-NTP sentinel
are exempt (FR-015 amendment; enforced by a partial unique index, DATA-001).

**FR-025 — Location mapping** `MUST`
An operator-maintained `locations.json` maps device IDs to display locations
and overrides the device-reported location. Unmapped devices display as
`UNMAPPED`. The dashboard MAY expose a local-network-only admin workflow to
view, save, and clear these mappings without hand-editing the JSON file.

## 4.3 Hub — Dashboard

**FR-030 — Latest view** `MUST`
The dashboard shows, per device: location, temperature, humidity, RSSI,
firmware version, online/offline/stale state, and last-seen age. Devices are
ordered by location in the device-card view. The Latest Readings table is
ordered by temperature descending (hottest first), with location as the
tie-breaker, so thermal hotspots are immediately visible.

**FR-031 — Stale detection** `MUST`
A device marked online whose last observation is older than a configurable
threshold (default 1200 s) is displayed as **stale**, distinct from offline.

**FR-032 — History view** `MUST`
The dashboard charts temperature history for a selectable window (1–168 h,
default 24 h), grouped by location groups, with per-group show/hide toggles.
The standard groups are Inside, Outside, Attic, and Separate. A floorplan
zone with type `attic`, or a location whose name begins with `Attic`, belongs
to Attic and MUST NOT also appear in Inside or Separate.

**FR-033 — Summary stats** `SHOULD`
Aggregate tiles: devices online/total, stale count, min/max temperature.

**FR-034 — Rotating operator views** `MAY` (R5)
The dashboard auto-rotates between configured views on a timer with a
pause/resume control, sized for a 1080p wall display.

**FR-035 — Floorplan view** `MAY` (R5)
An optional floorplan config (background image + positioned zones) renders
per-room current readings. Invalid config is rejected with a clear error;
absent config renders an empty state, never a crash.

**FR-036 — Suspect-reading flag** `MAY` (R5)
Readings matching operator-defined suspicion rules (e.g., outdoor humidity
pegged at 99–100 %) are visually flagged, not hidden.

**FR-037 — Firmware distribution** `SHOULD` (R4)
The hub serves staged firmware images at stable URLs for device download,
subject to SEC-007/SEC-008. Path traversal MUST be impossible (SEC-010).

## 4.4 Hub — Operator tools

**FR-040 — OTA staging CLI** `SHOULD` (R4)
A CLI stages a built firmware binary into a per-version directory, computes
size and SHA-256, signs the digest with the local P-256 key, writes a
manifest (API-014), and publishes the OTA command to one target device.
Version labels MUST be path-safe. A `--stage-only` mode skips publishing.

**FR-041 — Config CLI** `SHOULD` (R3)
A CLI publishes (or clears) the retained config document for a device with
client-side validation of ranges.

**FR-042 — Provisioning CLI** `MUST`
A documented, scripted flow creates per-device broker credentials and ACL
entries (SEC-002/SEC-003) and emits the values needed for the device's
`secrets.h`.

**FR-043 — Simulator** `MAY`
A simulator publishes realistic multi-device telemetry/status for local
development against a test broker. The simulator MUST NOT use
`retain=true` for telemetry.

**FR-044 — Backup** `MUST`
A script produces an online SQLite backup, verifies it with
`PRAGMA integrity_check`, compresses it, and prunes local backups beyond a
retention count. Restore procedure is documented and rehearsed (TEST-030).
The operational schedule SHOULD run the local SQLite export before the
off-site repository backup so the fresh database-only archive is included in
the off-site snapshot.

**FR-045 — Device retirement** `SHOULD` *(gap found in implementation review)*
A documented, scripted flow retires a device: delete its broker credential
(the revocation path for a lost or stolen unit), remove or archive its
`devices` row, and remove its location mapping. Until the script exists,
the manual procedure lives in the operations doc.

**FR-046 — Fleet version reconciliation** `MAY` *(added 2026-07-05,
implemented upstream)*
The collector MAY compare each device's reported `firmwareVersion` against
an operator-configured desired version. On mismatch it records a deployment
attempt (DATA-010) with device ID, from/to versions, and the optional
observed IP. Automatic OTA publishing is strictly opt-in (`--auto-ota`) and
constrained: it publishes only a previously staged, signed manifest for the
desired version; it respects a per-device/per-version cooldown (default
24 h); and the target version MUST already have passed the bench gate
(TEST-030/TEST-043) — auto-OTA automates distribution, never validation.
Observed IP addresses are diagnostic metadata only, never device identity.
