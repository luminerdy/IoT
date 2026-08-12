# 9. API / Interface Requirements (API)

## 9.1 MQTT topic contract

**API-001 — Topic scheme** `MUST`
All topics live under `home/sensors/<device_id>/…`:

| Topic suffix | Direction | Retained | QoS | Purpose |
| --- | --- | --- | --- | --- |
| `telemetry` | device → hub | **no** `[CHANGE]` | 1 | sensor readings |
| `status` | device → hub | yes | 1 | online/offline (+LWT) |
| `config` | hub → device | yes | 1 | runtime configuration |
| `command` | hub → device | no | 1 | operator commands (OTA) |
| `response` | device → hub | no | 1 | config ack/nack |
| `ota/status` | device → hub | no | 1 | OTA lifecycle events |

Authorization per topic is defined by SEC-003.

**API-010 — Telemetry payload** `MUST`
JSON object; unknown fields ignored by consumers (forward compatible):

```json
{
  "schemaVersion": "3.0",
  "seq": 123,
  "deviceId": "esp32-a1b2c3d4e5f6",
  "location": "UNMAPPED",
  "firmwareVersion": "0.2.0",
  "buildNumber": 42,
  "sensorType": "DHT22",
  "datetime": "2026-07-02T12:00:00Z",
  "temperature": 72.4,
  "humidity": 45.2,
  "units": {"temperature": "F"},
  "rssi": -55,
  "localIp": "203.0.113.25",
  "uptimeSeconds": 3600,
  "numReadErrors": 0,
  "numFilteredReadings": 2,
  "restartReason": "PowerOn",
  "activeConfig": {"reportIntervalSeconds": 600, "changeThresholdF": 1.0},
  "status": "OK"
}
```

Required for acceptance by the collector: `deviceId`, `datetime`,
`temperature`, `humidity`, and `seq` (FR-021; `seq` is mandatory in schema
3.0 because it forms the dedupe key, FR-024). The serialized payload MUST
fit within 1024 bytes — the device MQTT buffer size (TECH-011).
`schemaVersion` bumps on breaking change.

**API-011 — Status payload** `MUST`
`{"deviceId", "status": "online"|"offline", "firmwareVersion"?,
"buildNumber"?, "datetime"?, "reason"?, "localIp"?}`.
`localIp` (also optional in telemetry, added upstream 2026-07-04) is
diagnostic metadata for fleet operations — it is validated as an IP
address at ingest and MUST never be used as device identity (FR-046).

**API-012 — Config document & response** `SHOULD` (R3)
Config (retained): `{"reportIntervalSeconds"?: 10–3600,
"changeThresholdF"?: 0.1–10.0}`. Empty retained payload = reset to defaults.
Response: `{"deviceId", "type": "config", "status": "applied"|"rejected",
"message", "datetime", "activeConfig": {…}}`.

**API-013 — OTA command** `SHOULD` (R4)
```json
{
  "command": "ota_update",
  "rolloutId": "20260702T120000Z-0.2.0",
  "version": "0.2.0",
  "url": "http://<hub>/firmware/0.2.0/firmware.bin?key=<capability>",
  "sha256": "<64 hex>",
  "signature": "<hex DER ECDSA over the image digest>",
  "buildNumber": 2026070401,
  "metadataSignature": "<hex DER ECDSA, see signature contract below>",
  "size": 1048576
}
```
`buildNumber` MUST be inside signed material (SEC-006). `url` may use
plain HTTP because firmware authenticity is enforced by SEC-005/SEC-006;
for the rebuild it includes the SEC-016 firmware download capability key.
Devices reject commands missing/failing any field validation (FR-010…FR-012),
including a missing or non-positive `size`.

**Signature contract v2 (normative; updated 2026-07-05 to match the
fleet-deployed implementation, upstream DR-019).** Two ECDSA P-256
(secp256r1) signatures, both made with the OTA signing key, DER-encoded,
transmitted as lowercase hex, verified on-device with the baked-in public
key:

- `signature` — over the SHA-256 digest of the firmware image. Legacy
  field: it is what pre-anti-rollback firmware verifies, so it MUST remain
  present and unchanged for devices taking their first upgrade onto the
  anti-rollback firmware.
- `metadataSignature` — over the SHA-256 of the canonical metadata payload,
  exact bytes (UTF-8, one trailing newline after each line):

  ```text
  iot-home-ota-v2
  {sha256}
  {buildNumber}
  {version}
  {size}
  ```

- `buildNumber` — unsigned 32-bit monotonic integer; deployed convention is
  date-serial (e.g. `2026070401`), max `4294967295`.
- Anti-rollback state: the device persists its highest booted build number
  in NVS and rejects `buildNumber <= max(stored, compiled-in)` (FR-012).
- *Device public key* = uncompressed X9.62 point `04 ‖ X ‖ Y`, 130 hex
  chars, baked into `firmware/include/ota_public_key.h`.

*Supersedes the 2026-07-02 draft contract (single signature over
`digest ‖ buildNumber`), which was never deployed. The current repo's
`publish_ota.py`, firmware verifier, and tests implement v2; a fresh
rebuild MUST keep that contract for interop with the deployed fleet.*
Upstream reference: `publish_ota.py`
(`metadata_payload`/`sign_metadata`) and `otaMetadataSignatureValid()` in
`firmware/src/main.cpp`.

**API-014 — OTA manifest file** `SHOULD` (R4)
`manifest.json` staged next to the binary mirrors API-013 plus `deviceId`
(initial target) and `createdAt`.

**API-015 — OTA status payload** `SHOULD` (R4)
`{"deviceId", "type": "ota", "status": "downloading"|"rejected"|"failed"|
"rebooting", "message", "version", "rolloutId", "firmwareVersion",
"datetime"}`.

## 9.2 HTTP interface (dashboard)

Endpoints are JSON unless noted, and sit behind SEC-009 auth in the rebuild
target. Local-network admin writes are allowed only from private, loopback,
or link-local clients unless stronger auth is enabled.

**API-020 — `GET /`** `MUST`
Serves the dashboard HTML shell (static asset).

**API-021 — `GET /api/latest`** `MUST`
Array of per-device objects: `deviceId, location, firmwareVersion,
buildNumber, lastSeen, online, stale, ageSeconds, rssi, status, temperature,
humidity, sensorType, seq, observedAt, telemetryObservedAt,
telemetryAgeSeconds, deviceObservedAt, deviceAgeSeconds, stability,
recentSeqResets`. When a telemetry row exists, `observedAt` and `ageSeconds`
refer to that telemetry row; `deviceObservedAt` and `deviceAgeSeconds` expose
the latest status/device-row freshness separately. Staleness computed per
FR-031. Timestamp fields MUST be explicit UTC ISO-8601 strings with a `Z`
suffix so browser relative-time rendering does not interpret hub UTC values as
local wall time.

**API-022 — `GET /api/history?hours=&limit=`** `MUST`
Array of readings within the window, newest first. `hours` clamped 1–168
(default 24), `limit` clamped 1–50000 (default 500) (SEC-012). Fields:
`deviceId, location, temperature, humidity, rssi, status, seq, datetime,
createdAt`.

**API-023 — `GET /api/floorplan`** `MAY` (R5)
Validated floorplan document `{backgroundImage, zones[]}`; 500 with a clear
message on invalid config; empty document when absent.

**API-024 — `GET /api/locations` and `POST /api/locations`** `MAY` (R5)
`GET` returns `{locations, devices}` where `locations` is the current
`deviceId → displayLocation` mapping and `devices` contains the latest
dashboard rows plus `reportedLocation` and `configuredLocation`.
`POST` accepts `{deviceId, location}`; a non-empty location saves the
mapping, and an empty location clears it. Invalid JSON, invalid device IDs,
and overlong locations are rejected with 400. Writes from non-local clients
are rejected with 403 unless authenticated by a stronger deployment policy.

**API-024A — `GET /api/system`** `SHOULD` (R5)
Returns hub and monitoring status for the dashboard:
`temperatureF, sampledAt, ageSeconds, monitoring`. `monitoring` contains
`latestEvents[]`, `latestPostReboot`, and `latestWatchdogRelay`; monitoring
events include `source, eventType, severity, status, message, details,
createdAt`. Secrets and raw OTA URLs MUST NOT be included in monitoring event
messages or details.

**API-025 — `GET /firmware/<version>/firmware.bin?key=…`** `SHOULD` (R4)
Serves staged firmware with correct `Content-Length`. Requires the SEC-016
capability key (`?key=` query parameter) or operator Basic auth; anything
else receives 401. Traversal-safe per SEC-010.

**API-026 — Static file roots** `MUST`
Two roots, both traversal-safe (SEC-010), served with cache headers:
- `GET /assets/…` — the packaged dashboard UI (HTML/CSS/JS shipped with
  the hub package).
- `GET /media/…` — operator-supplied images (e.g., the floorplan
  background) from the configured `--media-dir`. (Current code calls this
  route `/dashboard-assets/` and the flag `--asset-dir`; the rebuild should
  standardize on the shorter `/media/` contract.)

**API-027 — Errors** `MUST`
Unknown paths → 404; malformed input → 400 with a plain message; handler
exceptions → 500 without stack traces or path disclosure in the body.

## 9.3 CLI interfaces

**API-030 — `iot-home-collector`** `MUST`
Flags: `--broker --port --db --client-id --username --password/--password-env
--tls --ca-cert --locations`. Secrets prefer env vars over argv.

**API-031 — `iot-home-dashboard`** `MUST`
Flags: `--host --port --db --locations --floorplan --stale-seconds
--firmware-dir --media-dir`.

**API-032 — `iot-home-ota`** `SHOULD` (R4)
`stage|publish` subcommands per FR-040 with `--stage-only` equivalent.

**API-033 — `iot-home-config`** `SHOULD` (R3)
Per FR-041, including `--clear`.

**API-034 — USB MQTT provisioning** `MUST`
At 115200 baud, firmware accepts newline-terminated commands from the physical
USB serial port:

- `IOT_MQTT_STATUS` returns only profile source (`compiled` or `nvs`), TLS
  state, stored-profile and parsed/active CA byte counts, and non-secret FNV-1a
  CA diagnostic fingerprints; it returns no endpoint, username, password, or
  certificate content.
- `IOT_MQTT_PROVISION <json>` accepts bounded schema-versioned profiles. Schema
  version 2 accepts exactly eight top-level fields: `schemaVersion=2`,
  `mqttConnectHost`, `mqttTlsHostname`, `mqttPort`, `mqttUsername`,
  `mqttPassword`, `mqttUseTls=true`, and one PEM `mqttCaCert`.
  `mqttConnectHost` is the TCP endpoint and may be a resolvable hostname or IP
  address; `mqttTlsHostname` MUST be a DNS hostname present in the broker
  certificate SAN and is used for SNI/certificate verification. Firmware also
  reads legacy schema version 1 with exactly seven fields, where `mqttHost` is
  used for both TCP connection and TLS hostname. The username MUST equal the
  hardware-derived device ID. String, port, password, certificate, and total
  NVS-profile lengths are bounded. Unknown, nested, missing, incorrectly typed,
  plaintext, or oversized profiles are rejected without changing NVS.
- `IOT_MQTT_CLEAR` removes only the MQTT profile and restarts into the compiled
  migration fallback. It MUST NOT erase the OTA build high-water mark.

Responses are fixed, secret-free status lines. The host CLI prompts with hidden
input or reads a mode-0600 password file; no password flag exists.
