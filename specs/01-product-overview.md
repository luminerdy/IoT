# 1. Product Overview

## 1.1 Summary

A **local-first home environment monitoring system**. Battery/USB-powered
ESP32 devices with DHT22 sensors measure temperature and humidity in rooms of
a single home and publish readings over the home LAN via MQTT. A Raspberry Pi
("the hub") runs the MQTT broker, a collector service that persists readings
to SQLite, and a read-only web dashboard. The hub also coordinates signed
over-the-air (OTA) firmware updates and runtime device configuration.

**No cloud dependency.** All data, control, and update paths stay on the LAN.
The only optional external touchpoint is an off-site copy of database backups.

## 1.2 Users and context

| Actor | Description |
| --- | --- |
| Operator | The homeowner/administrator. Provisions devices, runs OTA rollouts, maintains the hub. Technical. |
| Viewer | Anyone in the household viewing the dashboard (wall-mounted display, phone, laptop). Non-technical. |
| Device | An ESP32 sensor node. ~21 today; design ceiling 50. |
| Attacker (in scope) | Anyone on the LAN/WiFi without credentials; a thief with physical access to one sensor node. |

## 1.3 Design principles

1. **Local-first:** the system is fully functional with the internet down.
2. **Boring dependencies:** Python stdlib + one MQTT client library on the
   hub, plus `cryptography` for OTA signing; pinned, minimal libraries on
   the device.
3. **Secure by default:** the default install path is the hardened one
   (TLS, per-device credentials, ACLs, authenticated dashboard). Hardening is
   not an optional appendix. `[CHANGE]`
4. **Everything testable:** UI as static assets, pure logic separated from
   I/O, firmware logic unit-testable off-device.
5. **Reproducible deploys:** no hardcoded usernames or home-directory paths;
   a fresh Pi reaches production state from a documented, parameterized
   install. `[CHANGE]`

---

# 2. MVP Scope

The MVP is the smallest system that provides trustworthy room readings on a
dashboard. It corresponds to rebuild phases R1–R2 (see roadmap).

## In scope (MVP)

- ESP32 firmware: read DHT22, filter implausible/outlier readings, publish
  telemetry and online/offline status over authenticated MQTT (TLS).
- Hub collector: validate, de-duplicate, and persist telemetry to SQLite.
- Dashboard: latest readings per device, 24h history chart, stale/offline
  indication, behind authentication.
- Provisioning: per-device MQTT credentials and broker ACLs.
- Backup script with restore verification.

## Out of scope (MVP) — deferred, already spec'd

- Runtime device configuration over MQTT (Phase R3).
- Signed OTA updates with anti-rollback (Phase R4).
- Floorplan view, rotating operator views, suspect-humidity flagging (R5).
- Simulator (developer tool; any phase).
- Off-site backup upload.

## Explicit non-goals

- Cloud ingestion (AWS IoT was removed deliberately; do not reintroduce).
- Actuation/control of home devices (read-only monitoring).
- Multi-home / multi-tenant support.
- Public internet exposure of any endpoint.

---

# 3. Feature Inventory

Complete inventory of the current system, classified for the rebuild.

| # | Feature | Where it lives today | Rebuild disposition |
| --- | --- | --- | --- |
| F-01 | DHT22 sampling + median filter + outlier confirmation | `firmware/src/main.cpp` | Keep — extract to testable module |
| F-02 | Change-threshold + interval publish policy | `firmware/src/main.cpp` | Keep |
| F-03 | Telemetry JSON payload (schema 2.x) | firmware + `docs/mqtt-schema.md` | Keep — schema formalized in API spec |
| F-04 | Online/offline status with MQTT LWT | firmware | Keep |
| F-05 | Retained-message runtime config (interval, threshold) | firmware + `publish_config.py` | Keep (R3) |
| F-06 | OTA update: HTTP download, SHA-256 + P-256 ECDSA verify | firmware + `publish_ota.py` | Keep (R4) + **add anti-rollback** `[CHANGE]` |
| F-07 | OTA staging/signing/manifest CLI | `publish_ota.py` | Keep — use `cryptography` lib, not openssl binary `[CHANGE]` |
| F-08 | Collector: subscribe, validate, persist | `collector.py`, `db.py` | Keep + **dedupe** `[CHANGE]` |
| F-09 | Device-ID → room-location mapping | `locations.py` | Keep |
| F-10 | Dashboard: device cards, summary stats | `dashboard.py` (inline JS) | Keep — UI extracted to static assets `[CHANGE]` |
| F-11 | Dashboard: history chart, group toggles | `dashboard.py` | Keep |
| F-12 | Dashboard: rotating operator views, pause | `dashboard.py` | Keep (R5) |
| F-13 | Dashboard: configurable floorplan/zones | `floorplan.py`, `dashboard.py` | Keep (R5) |
| F-14 | Stale-device detection | `dashboard.py` | Keep |
| F-15 | Firmware file serving for OTA | `dashboard.py` `/firmware/` | Keep — move behind same auth story `[CHANGE]` |
| F-16 | Broker setup scripts (LAN, TLS+ACL, per-device users) | `scripts/` | Merge: TLS+ACL is the only path `[CHANGE]` |
| F-17 | systemd deployment units | `deploy/systemd/` | Keep — parameterized install `[CHANGE]` |
| F-18 | SQLite backup + integrity check | `scripts/backup_sqlite.sh` | Keep + scheduled retention |
| F-19 | Fleet simulator | `simulator.py` | Keep as dev tool |
| F-20 | Telemetry published with `retain=true` | firmware | **Drop** — causes duplicate ingestion `[CHANGE]` |
| F-21 | IP-allowlist gate on `/firmware/` | `dashboard.py` | **Drop** — replaced by real auth (SEC-007) `[CHANGE]` |
