# 5. Non-Functional Requirements (NFR)

**NFR-001 — Fleet scale** `MUST`
All hub components operate correctly with 50 devices reporting at the
minimum interval (10 s) without message loss. Design target: 21 devices at
600 s today.

**NFR-002 — Hub hardware envelope** `MUST`
The full hub stack (broker, collector, dashboard) runs on a Raspberry Pi
3B+ or newer: steady-state under 300 MB RAM combined and under 10 % average
CPU at design load.

**NFR-003 — Dashboard latency** `SHOULD`
`/api/latest` responds in < 200 ms and `/api/history` (24 h default window)
in < 1 s on target hardware with 90 days of retained data.

**NFR-004 — Offline autonomy** `MUST`
With the internet down, telemetry collection, dashboard, config, and OTA all
function. Only NTP (degrades per FR-015) and off-site backup are affected.

**NFR-005 — Crash-only services** `MUST`
Collector and dashboard are safe to kill at any time: no corruption (SQLite
WAL), no duplicate data on restart (FR-024), automatic systemd restart with
backoff.

**NFR-006 — Device autonomy** `MUST`
A sensor recovers from power loss, WiFi loss, broker restart, and failed OTA
without human intervention (FR-011, FR-014). A power-cycle is never required
except for hardware failure.

**NFR-007 — Data retention** `MUST` `[CHANGE]`
Raw readings are retained 90 days (configurable), pruned by a scheduled job.
The database does not grow unbounded. (Current system has no retention.)

**NFR-008 — Reproducible deployment** `MUST` `[CHANGE]`
A fresh Pi reaches production state via a documented, parameterized install
(target user, paths, ports as inputs). No hardcoded usernames or home
directories in units, scripts, or docs.

**NFR-009 — Maintainability bounds** `MUST` `[CHANGE]`
No inline multi-hundred-line HTML/JS blobs inside Python source; UI ships as
static assets. No hub source file exceeds ~400 lines without a recorded
justification. Shared MQTT client setup lives in one helper module.

**NFR-010 — Code quality gates** `MUST`
Lint (ruff) and format checks pass in CI for Python; clang-format for
firmware. CI is red on violations.

**NFR-011 — Observability** `SHOULD`
Hub services log structured, timestamped events for: connect/disconnect,
validation rejections (with reason and topic), OTA lifecycle, and DB errors.
Logs go to journald via stdout. No secrets in logs.

**NFR-012 — Firmware footprint** `SHOULD`
Firmware fits the standard ESP32 OTA partition scheme (two app slots), i.e.
app image ≤ ~1.9 MB, leaving OTA viable.

**NFR-013 — Time and units** `MUST`
All persisted and transmitted timestamps are UTC ISO-8601 with `Z` suffix.
Temperatures are Fahrenheit end-to-end, declared in the payload `units`
field (API-010).

**NFR-014 — Documentation currency** `SHOULD`
Every externally observable behavior change updates the relevant spec file
in the same PR (spec-first workflow, see roadmap R0).
