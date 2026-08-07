# 7. Technical Requirements (TECH)

## 7.1 Hub stack

**TECH-001 — Language & runtime** `MUST`
Python ≥ 3.11 on Raspberry Pi OS (64-bit). Package layout installable via
`pip install -e .` with `pyproject.toml`.

**TECH-002 — Dependency budget** `MUST`
Hub runtime dependencies: `paho-mqtt` (>=2,<3) and `cryptography` (for OTA
signing) only. Everything else is stdlib. Adding a runtime dependency
requires a recorded decision. Dev dependencies: `pytest`, `ruff`.

**TECH-003 — Storage** `MUST`
SQLite in WAL mode, single writer (collector), readers open read-only
connections. Schema managed by versioned migrations (DATA-006).

**TECH-004 — Web server** `MUST`
The dashboard may use stdlib `http.server` given SEC-009 places auth/TLS in
front of it, or a single lightweight framework may be adopted via recorded
decision. UI is static HTML/CSS/JS files served from disk — never inline
Python string literals (NFR-009).

**TECH-005 — Service management** `MUST`
Collector and dashboard run as systemd units generated from templates
(user, paths, ports parameterized) with `Restart=on-failure`,
`NoNewPrivileges`, `ProtectSystem=full`, and write access limited to the
data directory.

**TECH-006 — Broker** `MUST`
Mosquitto ≥ 2.0 from OS packages, configured per SEC-001…004 by an
idempotent setup script.

## 7.2 Firmware stack

**TECH-010 — Platform pinning** `MUST` `[CHANGE]`
PlatformIO with `platform = espressif32` pinned to an exact version in
`platformio.ini`. Upgrades are deliberate PRs that pass CI build + bench
validation. (Current repo pins `espressif32@6.10.0`; preserve this
discipline.)

**TECH-011 — Libraries** `MUST`
DHT sensor library and Adafruit Unified Sensor pinned by version.
JSON handling via ArduinoJson (SEC-015). MQTT client: PubSubClient pinned,
with a recorded decision noting its unmaintained status and the candidate
replacement (e.g., espMqttClient) if MQTT 5 or larger payloads are needed.

**TECH-012 — Crypto APIs** `MUST` `[CHANGE]`
Use version-portable mbedTLS calls for SHA-256 and ECDSA so the code
survives the mbedTLS 3.x transition bundled with newer ESP-IDF releases
(implemented as `MBEDTLS_VERSION_MAJOR` wrappers; ECDSA verification uses
only public, version-stable APIs — ASN.1 parse plus `mbedtls_ecdsa_verify`).
*Note (2026-07-02):* the task-watchdog API is equally version-coupled —
`esp_task_wdt_init(timeout, panic)` is the IDF 4.x form and becomes a
config-struct call in IDF 5. Both belong on the platform-upgrade checklist
when the TECH-010 pin moves.

**TECH-013 — Testable firmware layout** `SHOULD`
Pure logic (filtering, publish policy, manifest validation, hex/JSON
helpers) lives in a `lib/` module with no Arduino dependencies, unit-tested
natively on the CI host (TEST-012).

**TECH-014 — Build metadata** `MUST`
`FIRMWARE_VERSION` (semver-ish label) and `OTA_BUILD_NUMBER` (monotonic
integer, FR-012) injected at build time via build flags.

## 7.3 CI/CD

**TECH-020 — CI pipeline** `MUST` `[CHANGE]`
On every push/PR: (1) ruff lint + format check, (2) pytest with coverage
gate (TEST-040), (3) **firmware compile** via `platformio run` (not just
`check`), (4) firmware native unit tests, (5) secret/identifier scan
(SEC-014).
*Implementation status (2026-08-07):* Ruff lint/format, pytest coverage
reporting, gitleaks, and a hash-only current-tree identifier baseline are now
configured. The 113-test Python suite measures 92.1% with branch coverage and
enforces TEST-040's normative 80% floor. PlatformIO native tests cover the
extracted sensor filter and publish policy (TEST-010/011); TEST-012 remains
paired with the ArduinoJson manifest-validation milestone.

**TECH-021 — Reproducible firmware builds** `SHOULD`
CI archives the built `firmware.bin` + its SHA-256 per commit so a staged
OTA image can be traced to a commit.

**TECH-022 — No deploy from laptops** `SHOULD`
OTA staging happens on the hub from CI-built (or hub-built, documented)
artifacts; the signing step is the only hub-local, human-triggered action.
