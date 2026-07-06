# 6. Security Requirements (SEC)

## 6.1 Threat model (summary)

Assets: home occupancy data (telemetry history), the device fleet (OTA is
code execution on 21+ devices), WiFi credentials stored on devices, the OTA
signing key.

Adversaries in scope:
- **LAN guest/intruder** — on the WiFi or wired LAN, no credentials.
- **Compromised device** — attacker extracts flash from one stolen sensor.
- **Replay attacker** — has captured past legitimate MQTT traffic.

Out of scope: nation-state, physical attack on the hub itself, WPA2 cracking
(mitigated but not owned by this project).

## 6.2 Transport & broker

**SEC-001 — TLS-only MQTT** `MUST` `[CHANGE]`
The broker exposes a single TLS listener (8883) with a local CA. The
plaintext 1883 listener exists only bound to localhost for hub-internal
clients. Devices ship with `MQTT_USE_TLS=1` and the CA pinned.
(Old system defaulted to plaintext 1883 fleet-wide.)
*Decision (2026-07-02):* the hub runs the localhost 1883 listener; the
collector and operator CLIs connect to `127.0.0.1:1883` with `--no-tls`.
ACLs and the password file apply to both listeners
(`per_listener_settings false`), configured by
`scripts/configure_mosquitto_tls_acl.sh` and
`scripts/add_mqtt_device_user.sh`.

**SEC-002 — Per-device credentials** `MUST` `[CHANGE]`
Every device authenticates with its own username (= device ID) and unique
password. The shared `iot` credential is retired. Compromise of one device
is revocable by deleting one broker user.

**SEC-003 — Topic ACLs on every listener** `MUST` `[CHANGE]`
ACLs restrict each device user to its own topic subtree: write telemetry/
status/response/ota-status, read config/command. The collector user is
read-only on telemetry/status. Only the operator/admin user may write to
`command` and `config` topics. No listener runs without an ACL file.
*Interim state (live upstream since 2026-07-04):* the shared-credential
fleet's 1883 listener now enforces an ACL — the shared `iot` user can flow
telemetry/status but cannot publish `config`/`command`; a separate
`iot-admin` user holds publish rights. This closes the fleet-wide
OTA-command hole while per-device credentials and TLS remain the target
end-state. Residual gap in the interim model: the shared user's `+`
wildcard write means any device can still publish telemetry *as* another
device (mitigated hub-side by FR-022 only after per-device users land).

**SEC-004 — Broker hygiene** `SHOULD`
`allow_anonymous false` everywhere; password file and key material owned
root:mosquitto, mode 0640/0600; TLS ≥ 1.2.

## 6.3 Firmware & OTA

**SEC-005 — Signed firmware only** `MUST` (R4)
Devices apply only images whose SHA-256 digest verifies against a P-256
ECDSA signature made by the local signing key (FR-011). Plain-HTTP download
is acceptable *because* of this verification.

**SEC-006 — Anti-rollback** `MUST` (R4) `[CHANGE]` *(updated 2026-07-05)*
Signed manifests carry a monotonic `buildNumber` inside signed material;
devices reject non-greater build numbers against an NVS-persisted
high-water mark (FR-012). This defeats replay of old signed manifests by
anyone who gains command-topic access, including replay across re-flashes.
The deployed contract uses a dedicated metadata signature over the
checksum/build/version/size tuple (normative bytes in API-013), alongside
the legacy image signature kept for upgrade compatibility.

**SEC-007 — Signing key custody** `MUST`
The OTA private key exists only on the hub at a documented path, mode 0600,
excluded from git and from backups that leave the machine. Key rotation
procedure is documented: generate → flash new public key via signed OTA →
retire old key.

**SEC-008 — Device secret hygiene** `MUST`
`secrets.h` is git-ignored with a committed `.sample` template. Documentation
never contains real credentials. Accepted residual risk: ESP32 flash is
readable with physical access; per-device credentials (SEC-002) bound the
blast radius to one revocable identity plus the WiFi PSK (documented).

## 6.4 Dashboard / HTTP

**SEC-009 — Dashboard authentication** `MUST` `[CHANGE]`
The dashboard is not reachable unauthenticated beyond localhost. The old
"private-IP allowlist" gate is removed as security theater on a home LAN.
*Decision (2026-07-02):* built-in HTTP Basic auth, credentials from
`DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD`, compared in constant time. The
server **refuses to start** on a non-loopback bind without credentials
(AC-016); `--allow-unauthenticated` overrides only when a network-level
control (VLAN/firewall) is in place and recorded. Device firmware downloads
use the capability key defined in SEC-016.
*Residual risk:* Basic auth over plain LAN HTTP is sniffable — the
dashboard credential MUST be unique to this system and low-value. A
TLS-terminating reverse proxy in front is the documented upgrade path.
*Current implementation note (reviewed 2026-07-05 at commit `4d0e5cc` plus
local working-tree changes):* Basic auth was added, then intentionally
removed by local preference so the dashboard is open to home-network
clients. This spec keeps authentication as the rebuild target; local
unauthenticated operation must be an explicit `--allow-unauthenticated`
choice backed by a recorded network-control decision. `/firmware/` still
uses the private-IP allowlist rather than SEC-016's capability key.

**SEC-010 — Path traversal defense** `MUST`
Static file serving (firmware, dashboard assets) resolves paths and rejects
any request escaping the configured root, including encoded traversal and
symlink escape. (Current implementation is correct — preserve it and pin it
with tests, TEST-021.)

**SEC-011 — Output encoding** `MUST`
All device-influenced strings (device IDs, locations, status text) are
rendered via DOM text APIs or server-side escaping — never string-built
HTML. (Current UI does this correctly; keep it under test.)

**SEC-012 — Input bounds** `MUST`
HTTP query parameters are clamped server-side (history hours 1–168, limit
1–50000). Device IDs accepted by the collector match
`^esp32-[0-9a-f]{12}$` and locations are length-capped (≤ 64 chars).
`[CHANGE]` (currently unvalidated free text).

## 6.5 Data & repository

**SEC-013 — SQL safety** `MUST`
All SQL uses parameterized statements. String interpolation into SQL is
prohibited. (Currently true; keep it a stated requirement.)

**SEC-014 — Public-repo privacy** `MUST`
No private IPs, MACs, real device IDs, hostnames, room labels tied to a real
address, or credentials in tracked files. A CI secret/identifier scan runs
on every push. The existing identifier residue in old git history is either
rewritten or explicitly accepted in a recorded decision — decide once,
document it.

**SEC-015 — JSON construction on device** `SHOULD` `[CHANGE]`
Firmware builds and parses JSON with a real JSON library (ArduinoJson), not
substring scanning and unescaped `snprintf`, eliminating malformed-output
and key-confusion bugs in config/OTA parsing.

**SEC-016 — Firmware download capability key** `MUST` *(added 2026-07-02)*
`/firmware/` responses require either operator Basic auth (SEC-009) or a
capability key supplied as a `?key=` query parameter, compared in constant
time. The key comes from the hub's `FIRMWARE_DOWNLOAD_KEY` environment
value; the OTA staging CLI embeds it in manifest URLs, and devices carry it
in `secrets.h`. Rotation: set a new key, restage active releases, restart
the dashboard, roll device secrets at next flash. Accepted residual risk:
the key appears in staged manifests on hub disk and in device flash — it
guards firmware *distribution* only; firmware *authenticity* rests entirely
on SEC-005/SEC-006.
*Why this is a MUST, not polish (noted 2026-07-05):* staged firmware images
have `secrets.h` compiled in — a downloadable `firmware.bin` leaks the WiFi
password and MQTT credentials to anyone who can fetch it and run `strings`.
The current implementation gates `/firmware/` by private-IP allowlist only,
which does not stop a LAN guest. Open hardening item there; the rebuild
implements this key.
