# Progress Log

## 2026-08-15

### WaterHeater Replacement

- Replaced the removed WaterHeater board `esp32-9c9c1fc5cf1c` with the new
  USB-connected board on `/dev/ttyUSB1`, identified by MAC
  `20:50:0d:1b:bb:a8` and stable ID `esp32-20500d1bbba8`. `/dev/ttyUSB0`
  remained Sunroom Test (`esp32-9c9c1fda3670`) and was not flashed.
- USB-flashed only `/dev/ttyUSB1` with current bench-validated firmware
  `0.1.11-sec015-json` build `2026081002`; the local binary exact-matched
  SHA-256 `91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`
  before upload, and esptool wrote and verified the 977,040-byte image.
- Created pre-retirement backup
  `data/backups/iot-20260815T114136Z.sqlite.gz`, mapped
  `esp32-20500d1bbba8 -> WaterHeater`, added old ID
  `esp32-9c9c1fc5cf1c` to `config/retired_devices.json`, removed only the old
  current `devices` row, and preserved 15,954 historical readings for the old
  ID.
- Published retained default runtime config for `esp32-20500d1bbba8`
  (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) using operator
  credentials.
- Restarted the managed collector/dashboard through systemd recovery after
  interactive `systemctl restart` was blocked. The collector loaded 22 mappings
  and 4 retired IDs, explicitly ignored the old WaterHeater ID, and live
  `/api/latest` returned 22 rows, 0 offline, 0 stale, 0 `UNMAPPED`, with
  WaterHeater online/non-stale on `0.1.11-sec015-json`, valid DHT22 telemetry,
  and Sensor health `OK`.

## 2026-08-13

### Sunroom Test Bench Policy

- Recorded the Sunroom Test operating policy: it remains the USB-connected
  bench/test ESP32 on `/dev/ttyUSB0` for firmware validation, serial recovery,
  MQTT/config/OTA assertions, and first-pass feature checks. Because it is
  powered directly from PiServer USB and may not represent production device
  power stability, its sequence/reset stability should be ignored when deciding
  whether a firmware rollout can expand to deployed devices.

### GarageDriveway Replacement

- Identified the two USB-connected ESP32s without relying on their generic
  CP2102 serial labels. `/dev/ttyUSB0` is Sunroom Test
  (`esp32-9c9c1fda3670`); `/dev/ttyUSB1` is the new GarageDriveway board
  (`esp32-20500d1b72e8`).
- Added local ignored mapping `esp32-20500d1b72e8 -> GarageDriveway` and added
  a GarageDriveway outdoor zone back to the local floorplan. Kept the old
  suspect GarageDriveway board ID in `config/retired_devices.json` so
  historical readings remain preserved and the old board stays hidden.
- USB-flashed only `/dev/ttyUSB1` with current bench-validated firmware
  `0.1.11-sec015-json` build `2026081002`; upload wrote and verified the
  977,040-byte firmware image.
- Serial verification showed firmware `0.1.11-sec015-json`, stable device ID
  `esp32-20500d1b72e8`, Wi-Fi IP `10.10.10.164`, MQTT connection, and valid
  DHT22 telemetry (`88.2 F`, `41.7%`, `numReadErrors=0`,
  `numFilteredReadings=0`) at `2026-08-13T20:06:14Z`.
- Published retained default runtime config for `esp32-20500d1b72e8`
  (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) using operator
  credentials.
- Restarted the managed collector and dashboard through systemd recovery so
  local mapping/floorplan changes loaded. Live verification returned 22 latest
  rows, 0 offline, 0 stale, 0 `UNMAPPED`, and GarageDriveway online/non-stale
  on `0.1.11-sec015-json` with fresh valid telemetry.

### WallBehindWH Replacement

- After the original WallBehindWH board continued reset behavior even when
  moved close to PiServer, identified the USB devices before touching firmware:
  `/dev/ttyUSB0` remained Sunroom Test (`esp32-9c9c1fda3670`), while
  `/dev/ttyUSB1` was the new WallBehindWH replacement
  (`esp32-582abd70a404`).
- Added local ignored mapping `esp32-582abd70a404 -> WallBehindWH`, removed the
  old `esp32-240ac4fa418c` WallBehindWH mapping, and added the old unstable ID
  to `config/retired_devices.json` so current views hide it while historical
  readings remain preserved.
- Created and integrity-verified pre-replacement backup
  `data/backups/iot-20260813T221108Z-pre-wallbehindwh-replace.sqlite.gz`, then
  removed only the old current `devices` row for `esp32-240ac4fa418c`.
- USB-flashed only `/dev/ttyUSB1` with current bench-validated firmware
  `0.1.11-sec015-json` build `2026081002`; upload wrote and verified the
  977,040-byte firmware image.
- Serial verification showed firmware `0.1.11-sec015-json`, stable device ID
  `esp32-582abd70a404`, Wi-Fi IP `10.10.10.165`, MQTT connection, and valid
  DHT22 telemetry with `numReadErrors=0` and `numFilteredReadings=0`.
- Published retained default runtime config for `esp32-582abd70a404`
  (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) using operator
  credentials.
- Restarted the managed collector/dashboard so the mapping loaded. Live
  verification returned 22 latest rows, 0 offline, 0 stale, 0 `UNMAPPED`, and
  WallBehindWH online/non-stale on `0.1.11-sec015-json` with fresh valid
  telemetry. The old WallBehindWH ID is ignored as retired.

### Sensor Health Status

- Added database schema version 4 with DHT22 diagnostic counters on telemetry
  rows (`num_read_errors`, `num_filtered_readings`) and latest device rows
  (`last_num_read_errors`, `last_num_filtered_readings`).
- The collector now persists firmware `numReadErrors` and
  `numFilteredReadings`; `/api/latest` exposes the raw counters, per-device
  deltas from the previous telemetry row, and a derived `sensorHealth` status.
- Added a compact Sensor column to the dashboard Latest Readings table.
  Classification is conservative: offline/stale take precedence, missing
  counters are `Unknown`, zero new DHT errors is `OK`, small increases are
  `Watch`, and at least 10 new read failures or 3 new filtered readings in the
  latest interval is `Fault`.
- Updated functional/API/data specs and MQTT schema notes. Validation passed:
  focused DB/dashboard/migration tests (`46 passed`), full Python suite
  (`138 passed`, 83.88% coverage), Ruff lint/format checks on touched Python
  files, and `git diff --check`.
- After authorization to restart the dashboard if needed, created and
  integrity-verified pre-migration backup
  `data/backups/iot-20260813T120516Z-pre-sensor-health.sqlite.gz`.
- Migrated the live database to schema version 4 with
  `PRAGMA integrity_check=ok`. After the user completed the managed service
  restart, `iot-home-collector.service` and `iot-home-dashboard.service` were
  active under systemd and `/api/latest` exposed live `sensorHealth`.

### End-Of-Day Live Check

- At the 2026-08-13 wrapup, `mosquitto.service`,
  `iot-home-collector.service`, and `iot-home-dashboard.service` were active;
  the live database reported schema version 4 and `PRAGMA integrity_check=ok`.
- `/api/latest` returned 22 mapped devices, 0 offline, 0 stale, and 0
  `UNMAPPED`. Current stability watch items included `Attic`,
  `GarageDriveway`, `MasterBedroom`, `Sunroom Test`, `WallBehindWH`, and
  especially `WaterHeater`; `Sunroom Test` is excluded from production rollout
  stability decisions because it is the USB bench/test device.
- DHT sensor health was live in the API. Most devices reported `OK`; current
  `Watch` examples were `FrontBedroom` (`+2 read`) and `WaterHeater`
  (`+1 read`).

## 2026-08-12

### SEC-015 Watch Rollout

- After explicit approval to continue the SEC-015 rollout while watching reset
  behavior, verified the staged and local build artifacts exact-matched the
  bench-tested `0.1.11-sec015-json` build `2026081002` binary:
  SHA-256 `91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`,
  977,040 bytes.
- Live pre-check showed 22 active mapped devices, 0 offline, and
  `GarageDriveway` stale on suspect hardware. Reset-heavy non-SEC-015 devices
  included `Attic`, `WaterHeater`, `Laundryroom`, and `WallBehindWH`.
- Published rollout `20260812-waterheater-sec015-watch` to `WaterHeater`
  (`esp32-9c9c1fc5cf1c`). Observed OTA `downloading` at
  `2026-08-12T11:32:18Z`, `rebooting` at `2026-08-12T11:32:28Z`, and fresh
  `0.1.11-sec015-json` `OK` telemetry at `2026-08-12T11:32:50Z` with `seq=2`.
- Published rollout `20260812-wallbehindwh-sec015-watch` to `WallBehindWH`
  (`esp32-240ac4fa418c`), but no OTA status was observed and the device
  remained online/non-stale on `0.1.8-arduinojson`. The rollout was stopped
  without retrying or expanding further.

### GarageDriveway And UNMAPPED Retirement

- Added a local ignored `config/retired_devices.json` retirement list and wired
  the collector and dashboard to load it. Retired devices are ignored before
  collector database writes and hidden from `/api/latest`, `/api/history`, and
  `/api/locations`.
- Retired `GarageDriveway` (`esp32-0cb815c288f4`) pending replacement this
  weekend and the separate retired `UNMAPPED` device (`esp32-240ac4f9019c`).
  Removed the `GarageDriveway` active location mapping and floorplan zone.
- Created fresh pre-change backup `data/backups/iot-20260812T153514Z.sqlite.gz`.
  Removed only the current `devices` rows for the two retired IDs. Historical
  readings were preserved; verification found 9,464 readings retained and 0
  current `devices` rows for those IDs.
- Direct `systemctl restart/start` required interactive authentication. Plain
  process termination left the units inactive, so replacement collector and
  dashboard processes were started manually from `/home/scotty/IoT` with the
  same database, mapping, floorplan, firmware, and retired-device paths. MQTT
  and dashboard read APIs are live, but `iot-home-collector.service` and
  `iot-home-dashboard.service` remain systemd-inactive until an interactive
  service start or reboot restores the managed units.
- Live verification after retirement returned 21 latest rows, 0 offline, 0
  stale, and no `GarageDriveway` or `UNMAPPED` rows in latest/history/location
  API payloads.

### SEC-015 Continued Rollout

- Confirmed `0.1.11-sec015-json` build `2026081002` is the latest
  bench-validated firmware artifact staged in this checkout. The local build
  output and staged OTA binary still exact-matched SHA-256
  `91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`, size
  977,040 bytes.
- Published rollout `20260812-laundryroom-sec015-watch` to `Laundryroom`
  (`esp32-240ac4fa383c`). Observed OTA `downloading` at
  `2026-08-12T15:53:11Z`, `rebooting` at `2026-08-12T15:53:26Z`, and fresh
  `0.1.11-sec015-json` `OK` telemetry at `2026-08-12T15:53:37Z` with `seq=2`.
- Published rollout `20260812-frontbedroom-sec015-watch` to `FrontBedroom`
  (`esp32-9c9c1fdd632c`). Observed OTA `downloading` at
  `2026-08-12T15:54:18Z`, `rebooting` at `2026-08-12T15:54:41Z`, and fresh
  `0.1.11-sec015-json` `OK` telemetry at `2026-08-12T15:54:54Z` with `seq=2`.
- Stopped expansion after those two successful updates. Final live check at
  `2026-08-12T15:55:12Z` showed 21 visible rows, 0 offline, 0 stale, and 9
  visible active devices on SEC-015: Den, Entryway, FrontBedroom, Kitchen,
  Laundryroom, MasterBedroom, Office, Sunroom Test, and WaterHeater.
- After explicit approval, published rollout
  `20260812-laundryroomac-sec015-watch` to `LaundryroomAC`
  (`esp32-4022d8ee4904`). Observed OTA `downloading` at
  `2026-08-12T19:20:29Z`, `rebooting` at `2026-08-12T19:20:42Z`, and fresh
  `0.1.11-sec015-json` `OK` telemetry at `2026-08-12T19:20:54Z` with `seq=2`.
  Final live check at `2026-08-12T19:21:20Z` showed 21 visible rows, 0
  offline, 0 stale, and 10 visible active devices on SEC-015.
- After explicit approval, updated `UnderAC`, `BunkHouse`, and `Studio`.
  `UnderAC` rollout `20260812-underac-sec015-watch` reported `downloading` at
  `2026-08-12T20:08:19Z`; `rebooting` was not captured, but the device returned
  with fresh `0.1.11-sec015-json` `OK` telemetry at `2026-08-12T20:09:17Z`
  with `seq=2`. `BunkHouse` rollout `20260812-bunkhouse-sec015-watch` reported
  `downloading` at `2026-08-12T20:09:58Z`, `rebooting` at
  `2026-08-12T20:10:13Z`, and fresh target telemetry at
  `2026-08-12T20:10:23Z` with `seq=2`. `Studio` rollout
  `20260812-studio-sec015-watch` reported `downloading` at
  `2026-08-12T20:10:56Z`, `rebooting` at `2026-08-12T20:11:22Z`, and fresh
  target telemetry at `2026-08-12T20:11:35Z` with `seq=2`.
- Final live check at `2026-08-12T20:11:51Z` showed 21 visible rows, 0
  offline, 0 stale, 13 visible active devices on SEC-015, and 8 still on
  `0.1.8-arduinojson`.
- After explicit approval, updated `AtticDoor`, `Porch`, `Lightpole`,
  `Garage`, `SunroomDoor`, and `Sunroom` in that order. All six reported both
  OTA `downloading` and `rebooting`, then returned with fresh
  `0.1.11-sec015-json` `OK` telemetry.
- Rollout timestamps: `AtticDoor` downloaded at `2026-08-12T22:28:48Z`,
  rebooted at `2026-08-12T22:29:03Z`, and returned at
  `2026-08-12T22:29:09Z`; `Porch` downloaded at `2026-08-12T22:29:16Z`,
  rebooted at `2026-08-12T22:29:28Z`, and returned at
  `2026-08-12T22:29:41Z`; `Lightpole` downloaded at
  `2026-08-12T22:29:41Z`, rebooted at `2026-08-12T22:29:54Z`, and returned at
  `2026-08-12T22:30:07Z`; `Garage` downloaded at `2026-08-12T22:30:07Z`,
  rebooted at `2026-08-12T22:30:25Z`, and returned at
  `2026-08-12T22:30:38Z`; `SunroomDoor` downloaded at
  `2026-08-12T22:30:39Z`, rebooted at `2026-08-12T22:30:54Z`, and returned at
  `2026-08-12T22:31:07Z`; `Sunroom` downloaded at `2026-08-12T22:31:06Z`,
  rebooted at `2026-08-12T22:31:21Z`, and returned at
  `2026-08-12T22:31:33Z`.
- Final live check at `2026-08-12T22:31:56Z` showed 21 visible rows, 0
  offline, 0 stale, 19 visible active devices on SEC-015, and only `Attic` and
  `WallBehindWH` still on `0.1.8-arduinojson`.
- After explicit approval to update the final two devices, published rollout
  `20260812-attic-sec015-watch` to `Attic` (`esp32-240ac4ec25b4`). No OTA
  lifecycle status was captured, and the device did not converge to SEC-015.
  It remained online/non-stale on `0.1.8-arduinojson` while repeatedly
  reporting `seq=1`; observed reset count rose through 730 by
  `2026-08-13T01:04:05Z`. Stopped without retrying and did not attempt
  `WallBehindWH` because the active target failed to converge.
- Final live check at `2026-08-13T01:04:06Z` showed 21 visible rows, 0
  offline, 0 stale, 19 visible active devices on SEC-015, and `Attic` plus
  `WallBehindWH` still on `0.1.8-arduinojson`.

## 2026-08-11

### Dashboard Latest Readings

- Added dashboard/API support for persisted reset visibility: `/api/latest`
  now exposes `recentSeqResets` and a derived `stability` object, and the
  Latest Readings table shows `seq` plus stability so repeated low-sequence
  resets are visible without raw MQTT capture.
- Fixed stale/latest-age semantics so `observedAt` and `ageSeconds` follow the
  latest telemetry row when one exists, while `deviceObservedAt` and
  `deviceAgeSeconds` separately expose status/device-row freshness. A fresh
  retained or live status update no longer makes old temperature/humidity data
  appear fresh.
- Fixed the dashboard `0s ago` display by serializing latest-reading timestamp
  fields as explicit UTC ISO-8601 `Z` strings. The old API response used
  SQLite `YYYY-MM-DD HH:MM:SS` UTC strings, which browser JavaScript parsed as
  local time and then clamped as a future timestamp.
- Restarted only `iot-home-dashboard.service` at 21:23 CDT so the timestamp
  fix was live. A read-only `/api/latest` verification returned 23 rows, all
  latest timestamp fields with `Z` suffixes, 21 online/non-stale rows, 2 stale
  rows (`GarageDriveway` and `UNMAPPED`), and 0 offline rows.

### Device Power Maintenance

- User replaced power for `GarageDriveway` and `Laundryroom`.
- Read-only `/api/latest` check at 19:43 CDT showed both devices online and
  non-stale after the power replacement. `GarageDriveway` reported
  `0.1.8-arduinojson`, `status=online`, `seq=164`, `ageSeconds=701`, and
  `rssi=-68`. `Laundryroom` reported `0.1.8-arduinojson`, `status=OK`,
  `seq=3`, `ageSeconds=213`, and `rssi=-53`.
- Treat `Laundryroom`'s low sequence number as consistent with the recent power
  replacement; keep watching for repeated low-sequence resets before attributing
  it to firmware.
- User reported the `GarageDriveway` ESP32 itself is not in good shape and has
  ordered a replacement. A follow-up read-only `/api/latest` check at 19:45 CDT
  still showed `GarageDriveway` online/non-stale on `0.1.8-arduinojson`, with
  `status=online`, `seq=164`, `ageSeconds=821`, and `rssi=-68`. Treat the
  current hardware as suspect pending replacement; avoid drawing firmware
  conclusions from intermittent behavior on this board without corroboration.

## 2026-08-10

### SEC-015 One-at-a-Time OTA Rollout

- Staged exact firmware `0.1.11-sec015-json` build `2026081002` for signed OTA
  from the bench-tested binary. Served artifact verification matched SHA-256
  `91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22` and size
  977,040 bytes.
- Started an explicitly approved one-device-at-a-time rollout with a one-hour
  burn-in before any next device. A fresh fleet gate showed 22 active mapped
  devices, 0 offline, and 0 stale; the retired `UNMAPPED` record remained
  excluded.
- Den accepted the signed OTA: observed `downloading`, `rebooting`, and fresh
  `0.1.11-sec015-json` telemetry. Its one-hour burn-in passed with active fleet
  health clean throughout; Den stayed online, non-stale, and `OK`, with sequence
  observations from 2 through 9.
- Kitchen accepted the signed OTA: observed `downloading`, `rebooting`, and
  fresh `0.1.11-sec015-json` `OK` telemetry. During burn-in, raw non-retained
  telemetry at `2026-08-10T15:36:33Z` reported `restartReason=Brownout`,
  `uptimeSeconds=7`, and `seq=1`. The rollout was stopped immediately after
  that burn-in failure.
- After explicit acceptance to continue one device at a time, Office accepted
  the signed OTA: observed `downloading`, `rebooting`, and fresh
  `0.1.11-sec015-json` `OK` telemetry. Its one-hour burn-in passed from
  `2026-08-10T17:02:07Z` through `2026-08-10T18:02:07Z`; Office stayed online,
  non-stale, and `OK`, with sequence observations from 2 through 12 and active
  fleet offline/stale gates clear throughout.
- The rollout is paused again before another device because Kitchen continued
  showing repeated normalized `seq=1` resets after the earlier brownout, with
  samples at `2026-08-10T16:43:40Z`, `16:50:32Z`, `16:59:43Z`, `17:02:58Z`,
  `17:06:13Z`, `17:10:45Z`, `17:16:02Z`, `17:19:24Z`, `17:21:42Z`,
  `17:47:01Z`, `17:57:13Z`, `17:59:41Z`, and `18:00:52Z`.
- After explicit acceptance to continue despite Kitchen, MasterBedroom accepted
  the signed OTA: observed `downloading`, `rebooting`, and fresh
  `0.1.11-sec015-json` telemetry at `2026-08-10T23:30:59Z`. It initially
  advanced to `seq=2` with `uptimeSeconds=605` at `2026-08-10T23:51:10Z`, but
  then failed burn-in when raw non-retained telemetry at
  `2026-08-10T23:59:22Z` reported `seq=1`, `uptimeSeconds=5`, and
  `restartReason=InterruptWatchdog`. The active mapped fleet gate remained
  clear. Stop the rollout again; do not send another OTA until the repeated
  reset pattern on Kitchen and MasterBedroom is understood or explicitly
  accepted.
- Current rollout state after the stop: Den, Kitchen, Office, MasterBedroom,
  and Sunroom Test are on `0.1.11-sec015-json`; LaundryroomAC remains on
  `0.1.9-nvs-tls`; the remaining active mapped fleet remains on
  `0.1.8-arduinojson`.

### SEC-015 Device JSON Refactor

- Ran a fresh read-only fleet gate before continuing work. The 22 active mapped
  devices were online and non-stale; the only stale row was the excluded retired
  `UNMAPPED` record.
- Completed the remaining SEC-015 source refactor. Retained config parsing now
  uses ArduinoJson typed field handling instead of manual substring/number
  extraction.
- Device-side status, LWT, config response, OTA status, and telemetry payloads
  now use ArduinoJson bounded serialization rather than hand-built JSON strings.
- Bumped the bench candidate identity to `0.1.11-sec015-json` build
  `2026081002`, then built and USB-flashed it to Sunroom Test on `/dev/ttyUSB0`.
  Binary SHA-256:
  `91440aa1077ea305d0b8c672b856e16119b14f6156cac1051cfea34a45da6c22`; size:
  977,040 bytes.
- Bench config validation passed: valid retained config applied
  (`reportIntervalSeconds=60`, `changeThresholdF=1.5`), malformed JSON was
  rejected without changing active config, wrong-type `reportIntervalSeconds`
  was rejected without changing active config, and an empty retained payload
  cleared the device back to defaults (`600`, `1.0`).
- Safe OTA rejection probes passed without download: malformed command rejected
  as `invalid json`, unsupported command rejected as `unsupported command`, and
  string-typed OTA `size` rejected as `invalid ota size`.
- The default-cadence soak passed: after retained config was cleared, Sunroom
  Test published the next normal telemetry exactly ten minutes later at
  `2026-08-10 13:21:39`, advanced `seq` from 4 to 5, and remained online,
  non-stale, and `OK` on `0.1.11-sec015-json`.
- Verification passed: ESP32 firmware build, all 24 PlatformIO native firmware
  cases, the full Python suite with enforced coverage, firmware static analysis,
  and `git diff --check`. A focused Python subset also passed functionally but
  tripped the global coverage gate because it intentionally ran only part of the
  suite.

### ESP32 TLS Hostname/Profile Bench Fix

- Implemented schema version 2 for USB MQTT TLS provisioning profiles with
  separate `mqttConnectHost` and `mqttTlsHostname` fields. The ESP32 now
  connects to the TCP endpoint while passing the TLS hostname into
  `WiFiClientSecure` for SNI and certificate verification.
- Kept legacy schema version 1 readable, where `mqttHost` is used for both
  roles. The host provisioning CLI now emits schema v2 and keeps the old
  `--host` argument as a compatibility alias.
- Built and USB-flashed exact bench firmware `0.1.10-tls-host` build
  `2026081001` to Sunroom Test. Binary SHA-256:
  `afae56195002d97e2b397b51519f1a06df505d08c5ec180b32bbd25a79650ea8`.
- Because sudo was unavailable for production cert/password files, ran an
  isolated user-owned Mosquitto TLS listener on port `8884` with a temporary CA
  and a server certificate for `<hub-tls-hostname>`. Provisioned Sunroom Test with
  `mqttConnectHost=<hub-ip>` and `mqttTlsHostname=<hub-tls-hostname>`.
- Bench evidence: broker logs showed Sunroom Test connecting from
  `<device-ip>` as `<device-user>`, subscribing to its own
  command/config topics, and publishing retained status plus non-retained
  telemetry over TLS. The NVS MQTT profile was then cleared, the temporary
  broker stopped, and fresh production fallback telemetry through shared
  `1883` was verified.
- Production `8883` check: after committing the fix, reset only the Sunroom
  Test broker user to a generated temporary password, reloaded Mosquitto, and
  verified local TLS auth against `<hub-tls-hostname>:8883`. Provisioned Sunroom
  Test with `mqttConnectHost=<hub-ip>` and
  `mqttTlsHostname=<hub-tls-hostname>`; `ss` showed an established
  `<device-ip>` to `<hub-ip>:8883` Mosquitto socket, retained status
  showed `0.1.10-tls-host`, and the dashboard API showed fresh `OK` telemetry.
  Cleared the NVS profile afterward, verified fresh fallback telemetry through
  shared `1883`, rotated the broker user again to an unstored random password,
  and deleted temporary credential/CA files.
- Verification passed: full Python suite, all PlatformIO native tests, ESP32
  firmware build, and firmware static analysis.

## 2026-08-09

### Sunroom Test USB Recovery

- Investigated `Sunroom Test` / `<device-user>` after it appeared
  offline while physically connected on `/dev/ttyUSB0`. USB enumeration was
  present and readable/writable by the `dialout` user.
- Captured direct serial logs. Firmware `0.1.9-nvs-tls` build `2026080707`
  booted, connected to Wi-Fi at `<device-ip>`, and synchronized time. Its NVS
  TLS profile attempted `<hub-tls-hostname>:8883` but failed ESP32 DNS resolution.
- Cleared only the NVS MQTT profile over USB. The device rebooted into the
  compiled fallback profile and attempted `<hub-ip>:1883`, but initially
  still reported `MQTT connect failed, state=-2`.
- Reflashed the exact staged `0.1.9-nvs-tls` build over USB. The flashed app
  binary exact-matched staged SHA-256
  `3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501`; the
  upload succeeded and verified all written segments.
- The collector then recorded fresh `Sunroom Test` telemetry at
  `2026-08-09 17:38:02`, confirming the device recovered on the compiled
  fallback MQTT path. Do not re-provision TLS on this device until the ESP32
  hostname-resolution issue is understood or a stable broker hostname strategy
  is chosen.

### Watchdog and Post-Reboot Monitoring

- Added persistent `monitoring_events` storage for local health events. The
  dashboard `/api/system` response now includes recent monitoring events, the
  latest post-reboot check, and the latest Pi3 watchdog relay event.
- Added a System Health dashboard panel showing post-reboot and watchdog status
  separately from fleet stale/offline device state.
- Added `python -m iot_home.post_reboot_check` to record core service,
  dashboard API, SQLite integrity/schema, latest backup, and database
  maintenance status. With `--import-watchdog`, it imports recent Pi3
  `pi-watchdog.service` relay entries over SSH into SQLite.
- Added `deploy/iot-home-post-reboot-check.service` plus
  `scripts/install_post_reboot_monitoring.sh` so the post-reboot recorder can
  run automatically after boot.
- Ran the recorder once against the live database and imported the 2026-08-08
  Pi3 relay activation/restoration entries. Live SQLite is now schema version
  3 with integrity `ok`.
- Installed and enabled `iot-home-post-reboot-check.service`; it ran once and
  recorded a fresh successful post-reboot check. Restarted
  `iot-home-dashboard.service` so `/api/system` exposes the monitoring payload.

## 2026-08-08

### Incremental Production MQTT TLS Migration

- Activated a parallel production Mosquitto TLS listener on `8883` with
  per-listener settings and the tracked per-device ACL, leaving the existing
  shared-credential `1883` listener active for the fleet.
- Fixed the TLS installer for this Pi's Mosquitto package by skipping the
  unsupported `mosquitto -t` check, using `sudo find` for protected certificate
  ownership updates, adding hub hostname SANs, and
  regenerating the server certificate whenever it does not verify against the
  active local CA.
- Created and loaded a unique broker password for only the USB-connected
  Sunroom Test device, then provisioned its NVS MQTT TLS profile over
  `/dev/ttyUSB0`.
- The first live profile used a local mDNS name; USB serial showed ESP32 DNS
  failures for that host. Reprovisioning with `<hub-tls-hostname>` succeeded.
- Verified the TLS chain with `openssl`, verified local per-device TLS
  authentication, observed Mosquitto accept Sunroom Test on port `8883` as
  its per-device user, and confirmed the dashboard API returned 22 active
  mapped devices online, 0 offline, 0 stale, with Sunroom Test fresh, `OK`, and
  still on `0.1.9-nvs-tls`.
- Started the approved one-device-per-hour non-attic OTA rollout of
  `0.1.9-nvs-tls` build `2026080707` using the signed, bench-matched
  970,976-byte artifact with SHA-256
  `3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501`.
  Den, Kitchen, Office, and MasterBedroom each returned online/non-stale with
  `OK` telemetry on `0.1.9-nvs-tls`.
- The hourly controller stopped before sending LaundryroomAC because
  SunroomDoor, still on `0.1.8-arduinojson` and not part of the completed
  updates, reported `offline` through the pre-flight and follow-up watch. No
  further OTA command was sent.

## 2026-08-07

- Added USB-provisioned, hardware-bound MQTT profiles in a dedicated NVS
  namespace for `0.1.9-nvs-tls` build `2026080707`. Profiles require TLS, a
  unique device username, a bounded password, and one parse-valid pinned CA;
  the compiled shared profile remains a reversible migration fallback.
- Added a secret-safe host provisioning CLI, status/clear serial commands,
  ArduinoJson profile parsing, device-side mbedTLS certificate parsing, a
  profile-sized 4.4 KiB serial RX buffer, paced 64-byte USB writes for full
  certificate profiles,
  and secret-free CA length/fingerprint diagnostics. Native and Python tests
  cover type, bound, identity, TLS, PEM, NVS-size, and transport behavior.
- USB-flashed the exact 970,976-byte candidate to Sunroom Test; its SHA-256 is
  `3420e492e3d450886326885c65d1b3b6706f97ccab21724f5b58f75f1c61d501`.
  An isolated port-8884 Mosquitto listener with ephemeral RSA credentials,
  pinned CA validation, a matching broker-hostname DNS SAN, and the tracked
  production ACL accepted fresh status and `OK` telemetry from the device's
  unique identity. A mismatched identity could not reuse the credential, an
  authenticated device credential could not publish into another device's
  subtree, and a mismatched profile was rejected without replacing the valid
  NVS profile.
- Cleared the bench NVS profile after TEST-033 and verified Sunroom Test
  returned online with fresh `OK` telemetry through the unchanged compiled
  production listener. The temporary broker, CA, passwords, and test files
  were removed. No production listener, ACL, service, credential, or fleet
  device was changed.

- Replaced OTA command substring scanning with ArduinoJson `7.4.3` and moved
  typed, bounded manifest parsing plus hex, SHA, preflight, and downloaded-image
  validation into a host-testable firmware library. Nine TEST-012 cases cover
  malformed/root/key-confusion input, field types and bounds, hex/SHA checks,
  and size/build/signature gate ordering; all 15 native firmware cases pass.
- Built firmware `0.1.8-arduinojson` build `2026080702`, then USB-flashed the
  exact 839,344-byte artifact to Sunroom Test. The uploader verified the flash,
  and the device returned online with fresh DHT22 telemetry. Its binary SHA-256
  is `a58577ffba350b39b209b976b75413b7901b15875c2e5c9e5087cd4b7e0ec855`.
- Bench-probed the live ArduinoJson path with three download-blocked commands.
  The device rejected nested-command key confusion as `missing command`, a
  string-typed size as `invalid ota size`, and a valid typed current-build
  manifest as `firmware rollback rejected`. No fleet OTA was sent.
- Completed the requested 30-minute Sunroom Test observation on the exact
  `0.1.8-arduinojson` candidate. The final uninterrupted run supplied a
  60-minute window from 23:31:11Z through 00:31:12Z with six successive
  intervals of 600, 600, 600, 601, 600, and 600 seconds. Sequence advanced from
  2 through 8, all statuses were `OK`, temperatures stayed between 92.7 F and
  92.8 F, humidity stayed between 31.0% and 31.6%, and no early telemetry was
  published. The 30-minute timing/plausibility test passed.
- Finalized `0.1.8-arduinojson` build `2026080703` in commit `37d6ba5` and
  opened draft PR #5. Local and GitHub CI gates passed: 15 native firmware
  cases, 114 Python tests at 91.93% coverage, ESP32 build, static analysis,
  Ruff, compile, gitleaks, and the hash-only identifier scan.
- Clean-rebuilt, signed, and staged the committed 839,344-byte artifact. The
  rebuilt and staged SHA-256 values both equal
  `76ff6464c2189c029b6bcf57bd660b553b3d8b0fdef90075cdbf8929bd75cf91`;
  both signatures verified, keyed download returned 200 with exact bytes, and
  an unauthenticated download returned 401.
- Sent the signed command only to USB-connected Sunroom Test. It reported
  `downloading`, then `rebooting`, then fresh `OK` telemetry on build
  `2026080703`. Its final soak lasted 3,601 seconds with intervals of 600, 600,
  600, 600, 601, and 600 seconds, sequence 2 through 8, no early publishes,
  temperatures of 91.8–91.9 F, and humidity of 30.7–32.5%.
- Final bench regressions passed: rejected a 5-second config without changing
  the active 600-second interval; applied a valid 60-second config and restored
  retained defaults; rejected a valid signed same-build manifest before
  download; and downloaded then rejected valid metadata with an intentionally
  invalid firmware signature without rebooting or changing the installed build.
- Created and restore-verified fresh pre-rollout backup
  `data/backups/iot-20260808T013909Z.sqlite.gz`; integrity is `ok`, schema is v2,
  and preserved table counts were verified. Core services were active/enabled.
  Restic's read-only metadata/subset check found no repository errors; an
  84-hour stale lock was observed and intentionally left untouched.
- Merged PR #5 as `9029754` after all checks passed, clean-rebuilt from merged
  `main`, and confirmed the artifact still exact-matched the signed and staged
  839,344-byte binary with SHA-256
  `76ff6464c2189c029b6bcf57bd660b553b3d8b0fdef90075cdbf8929bd75cf91`.
- Rolled the exact artifact to the 21 remaining active devices in five
  acknowledged batches with fresh preflight and postflight checks. Kitchen;
  Den/Entryway/Office; Garage/LaundryroomAC/Studio/Sunroom; Attic/AtticDoor/
  Laundryroom/WaterHeater/UnderAC/WallBehindWH; and BunkHouse/FrontBedroom/
  GarageDriveway/Lightpole/MasterBedroom/Porch/SunroomDoor all returned on the
  target firmware.
- GarageDriveway's first attempt reported `firmware stream failed`; the
  coordinator stopped and the device remained healthy on the prior build. One
  isolated retry after fresh telemetry installed the target and returned fresh
  build `2026080703` `OK` telemetry. Its `rebooting` acknowledgement was not
  observed, so success was established from post-reboot target-build telemetry
  rather than the transient status. No second retry was sent.
- Final read-only API verification found all 22 active mapped devices online,
  non-stale, `OK`, and on `0.1.8-arduinojson`. The separate retired `UNMAPPED`
  AtticChimney record remains stale on `0.1.6-recovery` and was not modified.
- Replaced ad hoc SQLite schema initialization with packaged forward-only
  migrations `001` and `002`, transactionally tracked through
  `PRAGMA user_version`.
- Added DATA-001 database-enforced dedupe. The partial unique index ignores the
  pre-NTP sentinel and migration-only legacy exemptions; collector inserts use
  the index conflict path rather than a check-before-insert query. Telemetry
  validation now requires integer `seq` as specified by FR-021.
- Audited production read-only and found 503 historical extra rows across 486
  non-sentinel duplicate keys. DR-023 preserves all of them: migration marks
  only extra copies, retains the lowest-ID canonical row in the index, and
  gives every future row a non-exempt default.
- Applied the migrations to an online-backup scratch copy. It reached schema
  version 2 with integrity `ok`; exact comparisons found no removed, added, or
  changed original reading values and no changes to devices, deployment
  attempts, or system metrics.
- The live database reached schema version 2 during simultaneous dashboard and
  collector starts at 12:46 CDT. One collector attempt encountered a concurrent
  migration race and restarted successfully five seconds later. The migration
  retained all pre-migration readings and metrics; integrity is `ok`, 503 legacy
  duplicates remain preserved, and no indexed duplicate groups remain.
- Fixed the concurrent-start race by re-reading `PRAGMA user_version` after
  acquiring each migration write lock. A deterministic regression test now
  proves that a second starter skips migrations completed while it waited. The
  full suite has 114 passing tests at 91.9% branch-aware coverage.
- Restarted the collector at 15:14 CDT to load the concurrent-start fix. It
  reconnected and subscribed immediately with no warning, traceback, or
  migration error. Post-restart integrity remained `ok`, schema remained at
  version 2, all 503 legacy exemptions remained preserved, and fresh telemetry
  continued.
- Created and restore-verified fresh backup
  `data/backups/iot-20260807T193918Z.sqlite.gz`. A separate version-0 backup from
  before the live migration was also re-migrated with the fixed code: all
  242,715 readings and all original values were unchanged.
- Added CI Ruff lint and formatting checks, pytest coverage reporting and
  artifact upload, gitleaks, and a custom current-tree identifier scan.
- Removed collector `--auto-ota` and its command-publishing code. Firmware
  mismatches still create cooldown-limited `detected` deployment attempts;
  staged OTA publication remains an explicit admin-authenticated operator
  action under DR-022.
- Added a canonical per-device Mosquitto ACL and TEST-023 integration matrix.
  The test starts an isolated broker and verifies actual read/write behavior
  for two device identities, the read-only collector, and admin. The TLS setup
  script installs this same ACL; no live broker configuration was changed.
- Recorded an initial 52.6% branch-aware Python coverage baseline, then added
  collector, dashboard HTTP/security, config publisher, and OTA staging/
  publishing tests. The 114-test suite now measures 91.9%, and CI enforces the
  normative 80% floor.
- Extracted sensor filtering and publish policy into a pure C++ firmware
  library. Six PlatformIO native tests cover TEST-010/011, and both the native
  suite and ESP32 compile pass. Assigned the changed binary a distinct local
  identity, `0.1.7-testable-core` build `2026080701`, to avoid reusing the
  deployed anti-rollback identity. The candidate has not been USB-bench tested,
  staged, or deployed. OTA manifest-native coverage remains tied to the later
  ArduinoJson refactor.
- Added a hash-only baseline for existing private-IP, MAC, device-ID, `.local`,
  and installed-hostname findings. New findings fail without printing matched
  values, and baseline regeneration is never automatic.
- Accepted DR-021: preserve existing Git history for now, scan new commits with
  gitleaks, and require explicit security review for identifier-baseline changes.
- Added lossless SQLite maintenance that checks live integrity, restore-checks
  the newest compressed local backup, runs `PRAGMA optimize`, and proves that
  row counts in `readings`, `deployment_attempts`, and `system_metrics` do not
  change.
- Added explicit alerts for backup age, database size, filesystem free bytes,
  and filesystem free percentage. The command returns distinct alert and
  critical-failure exit statuses for systemd/journal visibility.
- Added a hardened oneshot service and daily 03:05 America/Chicago timer, plus
  a dedicated installer that does not rewrite application credentials or
  restart the collector/dashboard.
- Installed and enabled the live timer. Its first systemd-triggered oneshot
  completed successfully, and the next randomized run is scheduled for
  2026-08-08 at 03:09:59 CDT.
- Added focused preservation, capacity-alert, and missing-backup tests. A live
  manual check passed with 241,624 readings, 351 system metrics, a restore-valid
  current backup, a roughly 62 MB database, and 90.3% filesystem free space.

## 2026-08-05

- Fixed the Pi3 watchdog's initial-cooldown bug so the first qualified recovery
  is immediately eligible and the one-hour cooldown applies only between actual
  relay cycles. All 34 Python tests passed, and the installed Pi3 script matched
  the tested local checksum.
- Completed a controlled end-to-end PiServer recovery test. After five
  consecutive failed checks, the Pi3 activated BCM GPIO17 at 08:04:50 CDT,
  removed target power for 15 seconds, and restored it. PiServer booted at
  08:05:19; Mosquitto, the collector, and the dashboard returned active and
  enabled, and the Pi3 reported the target healthy at 08:05:44.
- Changed the live production threshold from the five-check test setting to 10
  consecutive one-minute failures. Verified
  `WATCHDOG_FAILURES_BEFORE_RECOVERY=10`, an active and enabled watchdog
  service, and GPIO17 output-low at idle. Retained the 15-second relay-off time
  and one-hour cooldown between actual relay cycles.
- The post-recovery dashboard check reported 23 online, non-stale records on
  `0.1.6-recovery`: 22 active mapped devices and one `UNMAPPED` device,
  consistent with the temporarily retired `AtticChimney` reporting again.

## 2026-08-04

- Temporarily retired `AtticChimney` from the active dashboard fleet until attic access is safe and the device can be replaced. Removed its ignored local location and floorplan entries and its current `devices` row while preserving all 463 historical readings. Created verified pre-change backup `data/backups/iot-20260804T125801Z.sqlite.gz`.
- Recorded that the operator replaced power for `MasterBedroom`. The live 2026-08-04 check shows it online, fresh, and reporting normally on `0.1.6-recovery`; treat the earlier reconnect problem as resolved unless it recurs.
- Recorded that the operator also replaced power for `BunkHouse`. The live 2026-08-04 check shows it online, fresh, and reporting normally on `0.1.6-recovery`; treat the earlier long-offline problem as resolved unless it recurs.
- Set up a Raspberry Pi 3 as the external PiServer watchdog. The local SSH alias
  is `pi-watchdog`, using a dedicated SSH identity. The Pi3 runs an enabled and
  active `pi-watchdog.service`, watches PiServer through its private LAN
  address, and has relay control enabled on BCM GPIO17 for a Digital Loggers
  IoT Relay. That relay accepts a direct 3.3 V GPIO signal plus ground and does
  not require an external resistor or driver.
- Observed a real PiServer-unreachable interval from 21:13 through 21:23. The Pi3 correctly detected 11 failed checks and saw PiServer recover at 21:24, but did not activate the relay. The cause is a watchdog cooldown bug: `last_recovery = 0.0` combined with monotonic uptime prevents the first recovery until the Pi3 has been up for one hour. The Pi3 had booted at 20:33, so the five-failure threshold at 21:17 was still inside that unintended startup block.
- Left the watchdog running overnight so a later test can exercise relay recovery after the one-hour restriction has elapsed. Scheduled the one-time user timer `iot-watchdog-morning-check.timer` for 2026-08-05 07:00 CDT. It runs `tools/morning_watchdog_check.sh` read-only and writes `data/watchdog-morning-check-2026-08-05.txt` with both machines' uptime, service health, GPIO17 state, and watchdog recovery logs.

Use this file for dated accomplishments and important observations. Keep future tasks in `docs/implementation-plan.md` and durable decisions in `docs/decision-record.md`.

## 2026-07-10

### Third Attic Sensor And Dashboard Thermal View

- Provisioned and mapped the third attic device as `Attic`, bringing the live mapped fleet to 23 devices and the attic set to `Attic`, `AtticChimney`, and `AtticDoor`; all three report firmware `0.1.4-antirollback`.
- Added a distinct `Attic` Temperature Graph selector group. Locations in an `attic` floorplan zone or beginning with `Attic` are excluded from `Inside` and `Separate`.
- Sorted Device List Grid cards alphabetically by display location and Latest Readings by temperature descending so the hottest locations appear first.
- Changed the temperature graph to retain 75 F and 100 F reference lines while expanding its range for selected readings outside that span.
- Observed the new `Attic` sensor peak at `137.5 F` around 15:21 CDT, stop reporting after 15:22, and return around 18:34 at `124.3 F`. The approximately 3 hour 12 minute gap began before the Pi reboot at 17:33 and was isolated from `AtticChimney` and `AtticDoor`. Repeated sequence resets before the gap indicate device reboot or power instability; heat is a plausible correlation, not yet a confirmed cause.
- After recovery, the device advanced sequence numbers normally and remained online with good RSSI. Recheck during the 2026-07-11 afternoon heat window for a repeatable temperature/offline threshold.

## 2026-07-09

### AtticChimney ESP32 Provisioned

- Reviewed `AtticDoor` telemetry from the two attic-door opening tests. The first opening around 12:21 CDT dropped the attic-door reading from about `109.9F` to `97.5F`; the second opening around 17:00 CDT dropped it from about `123.8F` to near `100F`.
- Identified the new blank ESP32 on `/dev/ttyUSB0`; the existing flashed USB sensor remained on `/dev/ttyUSB1`.
- USB-flashed firmware `0.1.4-antirollback` to the new ESP32.
- Published retained default config: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Mapped the new device to `AtticChimney` in local `config/locations.json` and added it to the local floorplan as a `utility` zone so it appears with the separate/utility graph group.
- Restarted `iot-home-collector.service` and `iot-home-dashboard.service`.
- Verified `AtticChimney` on `/api/latest`: online, non-stale, firmware `0.1.4-antirollback`, status `OK`, valid DHT22 telemetry, and no `UNMAPPED` devices.

## 2026-07-08

### Dashboard Admin Mapping

- Added the dashboard `Manage Devices` admin panel for device/location mapping.
- Added `GET /api/locations` to return mapped devices and current dashboard mapping state.
- Added `POST /api/locations` to save or clear display locations in local `config/locations.json`; writes are limited to private, loopback, or link-local clients.
- Added `save_locations()` and tests for sorted, normalized location writes.
- Verified normal port `8000` serves the updated dashboard, `/api/locations` returns 21 devices and 21 mappings, and a no-op live mapping save works.
- Ran `python3 -m compileall app scripts` and `.venv/bin/python -m pytest`; 29 tests passed.
- Committed the implementation as `bade1bf add dashboard device mapping admin`.

### Backup Check And Local Schedule

- Confirmed the restic/S3 cron backup succeeded at `2026-07-08T02:15:01-05:00` and saved snapshot `a2980899`.
- Ran `restic check`; it completed with no repository errors.
- Verified the latest restic snapshot includes `data/iot.db`, `config/locations.json`, and `config/floorplan.json`.
- Dumped `data/iot.db` from the latest restic snapshot to `/tmp`, ran `PRAGMA integrity_check`, and got `ok`.
- Added a daily local SQLite backup cron job at `02:05` CDT, before the existing `02:15` restic job:

```cron
5 2 * * * cd /home/scotty/IoT && /home/scotty/IoT/scripts/backup_sqlite.sh data/iot.db >> /home/scotty/logs/iot-sqlite-backup.log 2>&1
```

- Ran the local backup manually; it created `data/backups/iot-20260708T183106Z.sqlite.gz`.
- Restore-checked that archive through `/tmp`; `PRAGMA integrity_check` returned `ok`, and the restored database contained 84,782 readings across 21 devices.

## 2026-07-05

### Scheduled Backup Check

- Confirmed the unattended restic cron backup succeeded at `2026-07-05T02:15:01-05:00` and saved snapshot `2ba924d0`.
- Restore-checked snapshot `2ba924d0` into a temporary `/tmp/iot-restic-restore-check-*` directory. The expected `IoT`, `config`, and `.config/restic` roots were present, and the scratch restore directory was removed after verification.
- Ran `restic check --read-data-subset=1/100`; it completed with no repository errors.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are active and enabled after the previous reboot.
- Verified the dashboard API reports 21 devices, 21 online, 0 stale, 0 unmapped, and all 21 on `0.1.4-antirollback`.
- Confirmed the USB bench ESP32 remains reachable as `/dev/ttyUSB0` and user `scotty` is in the `dialout` group.
- Added `docs/operations-runbook.md` as the compact Phase 5 operations reference, including daily service/API checks, backup verification, runtime config publishing with admin MQTT credentials, OTA rollout guardrails, service recovery commands, and the add/replace sensor checklist.

## 2026-07-04

### CI And GitHub Access

- Confirmed `gh` is authenticated as `luminerdy` with `repo` and `workflow` scopes.
- Investigated the failing PR #3 GitHub Actions `firmware-check` job. Root cause was that the new clean-runner `platformio run -d firmware` step copied `firmware/include/secrets.sample.h` to `secrets.h`, but the sample MQTT CA certificate macro used a multiline raw string inside `#define`, which did not compile.
- Updated `firmware/include/secrets.sample.h` to use an escaped certificate placeholder string.
- Reproduced the clean CI path in a scratch checkout with sample secrets copied to `secrets.h`; both `platformio check -d firmware` and `platformio run -d firmware` passed.
- Verified `.venv/bin/python -m pytest` still passes with 27 tests.
- Pushed commit `2fefa22` to PR #3; both Python and firmware GitHub Actions checks now pass on the branch.

### Collector Deployment

- Created a verified SQLite backup before live deployment: `data/backups/iot-20260704T180617Z.sqlite.gz`.
- Restarted the live `iot-home-collector.service` on 2026-07-04 at 13:06 CDT. Non-interactive `sudo systemctl restart` was unavailable, so the collector process was killed under the service's `Restart=on-failure` policy; systemd restarted it as PID `10202`.
- Verified collector startup logs: 21 location mappings loaded, MQTT connected to `localhost:1883`, and telemetry/status subscriptions restored.
- Verified live dashboard API after restart: 21 devices, 21 online, 0 stale, 0 unmapped, and all 21 on `0.1.3-signed-ota`.
- Verified the retained-message replay did not create new duplicate readings: restart-window duplicate groups were `0`.
- Confirmed `deployment_attempts` remains empty because desired-version/auto-OTA is not enabled in the live service yet.
- Could not activate MQTT ACLs or dashboard Basic auth from this session because the required `/etc/mosquitto` and `/etc/iot-home` changes are root-owned and non-interactive `sudo` is unavailable.

### Anti-Rollback Firmware Rollout

- Added signed OTA anti-rollback: firmware now reports `buildNumber`, stores the highest booted build number in ESP32 NVS, and rejects OTA commands whose signed `buildNumber` is less than or equal to the highest booted build.
- Extended OTA manifests and commands with `buildNumber` and `metadataSignature`. The existing firmware signature remains over the binary digest for compatibility with `0.1.3-signed-ota`; the new metadata signature covers the canonical checksum/build/version/size tuple.
- Bumped firmware to `0.1.4-antirollback` with build number `2026070401`.
- Verified `.venv/bin/python -m pytest` with 30 tests, `.venv/bin/platformio run -d firmware`, and `.venv/bin/platformio check -d firmware`.
- Staged signed artifact `data/firmware/0.1.4-antirollback/firmware.bin`; HTTP checks on loopback and LAN returned `200` and matched SHA-256 `f90de1498aab21b65ace4af7700494b68b88f1f3c58d92a6ed99c1e853c130d3`.
- OTA-updated the USB bench device `Sunroom Test` / `esp32-9c9c1fda3670`; it reported `downloading`, then `rebooting`, then returned online on `0.1.4-antirollback` with build number `2026070401`.
- Published a bench-only lower-build rollback test with signed build number `2026070400`; the device rejected it as `firmware rollback rejected` and stayed on `0.1.4-antirollback`.
- Rolled `0.1.4-antirollback` to the remaining mapped fleet in small batches. Each batch reported `downloading` then `rebooting`, and final live checks showed 21 devices online, 0 stale, 0 unmapped, and all 21 on `0.1.4-antirollback`.
- Retained MQTT status for all 21 devices reports `buildNumber` `2026070401`.

### Live ACL And Dashboard Auth Activation

- Activated Mosquitto ACL protection on the current port `1883` listener with fleet user `iot` and admin publisher user `iot-admin`.
- Stored generated local operator credentials for `iot-admin` and dashboard Basic auth in `/home/scotty/.config/iot-home/operator-credentials.env` with mode `0600`.
- Reinstalled the systemd service units and `/etc/iot-home/iot-home.env`, then explicitly restarted `iot-home-collector.service` and `iot-home-dashboard.service` so both loaded the new environment.
- Verified dashboard auth: unauthenticated `/api/latest` returned `401`, authenticated `/api/latest` returned `200`, and private-network `/firmware/0.1.4-antirollback/firmware.bin` still returned `200` for ESP32 OTA downloads.
- Verified live MQTT ACL behavior: fleet-user command delivery was blocked, admin command delivery worked, and fleet-user telemetry delivery still worked.
- Confirmed after activation that `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are active, and the dashboard API reports 21 devices online, 0 stale, 0 unmapped, all on `0.1.4-antirollback`.
- Updated `scripts/configure_mosquitto_lan.sh` to skip `mosquitto -t` when the installed Mosquitto build does not support config-test mode.

### Dashboard Auth Removal

- Removed dashboard Basic auth from `app/iot_home/dashboard.py` by local preference: anyone already on the home network may view the dashboard without a password.
- Removed dashboard credential handling from `scripts/install_systemd_services.sh` so future service installs do not write unused `DASHBOARD_USERNAME` or `DASHBOARD_PASSWORD` entries.
- Kept `/firmware/...` restricted to private, loopback, and link-local client addresses; ESP32 OTA downloads still use the existing local-network guard plus firmware hash/signature validation.
- Reloaded the live dashboard service through systemd's `Restart=on-failure` path after non-interactive `systemctl restart` required authentication.
- Verified unauthenticated loopback and LAN `/api/latest` access returns `200` after auth removal.

### Reboot Resilience Check

- Created a fresh post-hardening SQLite backup before reboot: `data/backups/iot-20260704T210906Z.sqlite.gz`.
- Rebooted the Pi and verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` came back active and enabled at boot.
- Verified dashboard API access after reboot. `/api/latest` reported 21 devices, 21 online, 0 stale, 0 unmapped, and all 21 on `0.1.4-antirollback`.
- Verified MQTT ACL behavior after reboot with isolated test topics: fleet-user command publish was not delivered, `iot-admin` command publish was delivered, and fleet-user telemetry publish was delivered.
- End-of-day stop point: core hardening is live and reboot-tested. Pick up after the 2026-07-05 `02:15` CDT backup window by checking the restic log/snapshot and then move to floorplan/dashboard polish or compact operator runbooks.

### Version Mismatch OTA Trigger

- Added optional collector-side desired firmware version checking. When a device reports a different `firmwareVersion`, the collector records a `deployment_attempts` row with the stable device ID, current version, target version, and optional reported `localIp`.
- Added opt-in collector `--auto-ota` publishing from an already staged
  `data/firmware/{version}/manifest.json`, with a cooldown to avoid repeated
  commands for the same device/version. Superseded by DR-022 on 2026-08-07;
  collector OTA publishing was removed in favor of operator-only authority.
- Updated ESP32 status and telemetry payloads to include `localIp` as diagnostic metadata.
- Verified the code path with `.venv/bin/python -m pytest` and confirmed the firmware still builds with `.venv/bin/pio run -d firmware`.
- USB-flashed the exact build to the local `Bench Device` ESP32 first and verified it came back online over MQTT with `firmwareVersion` and `localIp` in the status payload.
- Fleet rollout remains gated on testing the exact firmware build on the USB-connected `Bench Device` first.

## 2026-07-03

### Phase 5 Hardening Pass

- Confirmed the unattended restic cron backup succeeded at `2026-07-03T02:15:01-05:00` and saved snapshot `0043918c`.
- Stopped new firmware telemetry publishes from using the MQTT retain flag.
- Added collector/database dedupe for repeated `(device_id, seq, datetime)` telemetry so retained or replayed messages do not create duplicate reading rows.
- Tested the non-retained telemetry firmware change on the USB bench ESP32 only. USB flash succeeded, the device booted, connected to WiFi/MQTT, applied retained config, and reported fresh dashboard telemetry. A bench-only config reapply produced fresh telemetry with MQTT retain flag `0`.
- Temporarily set the bench ESP32 report interval to 30 seconds, observed periodic telemetry publishes with retain flag `0`, then restored the retained bench config to `reportIntervalSeconds=600` and `changeThresholdF=1.0`.
- Cleared the old retained bench telemetry message from Mosquitto after validating the new non-retained publishes.
- Pinned the firmware PlatformIO `espressif32` platform to `6.10.0` and added `platformio run -d firmware` to GitHub Actions CI.
- Smoke-tested collector dedupe against the real local broker using a temporary SQLite database and separate MQTT client IDs: first retained delivery inserted 20 readings; the second retained delivery against the same DB kept the reading count at 20.
- Added collector handling for empty MQTT payloads so retained-message deletes are ignored instead of logged as JSON parse errors.
- Added optional dashboard Basic auth, controlled by `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`; `/firmware/...` remains restricted by private/link-local source IP rather than dashboard auth so ESP32 OTA downloads still work.
- Smoke-tested dashboard Basic auth on temporary port `8002`: unauthenticated and wrong-password `/api/latest` requests returned `401`, and correct credentials returned `200`.
- Updated the systemd dashboard unit to read `/etc/iot-home/iot-home.env`, and updated the service installer to write optional dashboard credentials when provided.
- Updated the port `1883` Mosquitto LAN configuration script to install ACL protection: the current shared `iot` user can keep telemetry/status flow, while OTA/config publishing moves to `iot-admin`.
- Smoke-tested the MQTT ACL rules on a temporary local Mosquitto listener: `iot` telemetry publish was delivered, `iot` command publish was denied, and `iot-admin` command publish was delivered.
- Updated runbooks so config and OTA publisher commands use `iot-admin` after ACLs are enabled.
- Verified with `.venv/bin/python -m pytest`, `.venv/bin/python -m compileall app scripts`, `bash -n` on shell scripts, `platformio run -d firmware`, and `platformio check -d firmware`.

## 2026-07-01

### Signed OTA Batch

- Verified the live dashboard API before rollout: 21 mapped devices online, 0 stale, 8 devices on `0.1.3-signed-ota`, and 13 devices still on `0.1.2-filtered-telemetry`.
- Verified `http://<pi-ip-address>:8000/firmware/0.1.3-signed-ota/firmware.bin` returned HTTP 200 and matched the staged firmware SHA-256.
- Published signed OTA rollout `20260701T171632Z-0.1.3-small-batch-2` to three indoor devices.
- Observed OTA download start on all three devices. Two also published `rebooting` / `firmware update applied`; the dashboard API confirmed all three returned online, non-stale, status `OK`, and reporting `0.1.3-signed-ota`.
- Signed OTA rollout count is now 11 devices. Ten devices remain on `0.1.2-filtered-telemetry`.
- Published signed OTA rollout `20260701T181636Z-0.1.3-small-batch-3` to three utility-area devices.
- Observed OTA download start and `rebooting` / `firmware update applied` on all three devices. The dashboard API confirmed all three returned online, non-stale, status `OK`, and reporting `0.1.3-signed-ota`.
- Signed OTA rollout count is now 14 devices. Seven devices remain on `0.1.2-filtered-telemetry`.
- Published signed OTA rollout `20260702T001656Z-0.1.3-small-batch-4` to two remaining devices.
- Published signed OTA rollout `20260702T001833Z-0.1.3-final-batch` to the final five devices.
- Observed OTA download start on all seven remaining devices and `rebooting` / `firmware update applied` on all final-batch devices. The dashboard API confirmed all 21 mapped devices are online, non-stale, status `OK`, and reporting `0.1.3-signed-ota`.
- Signed OTA rollout is complete for the mapped fleet. Zero mapped devices remain on `0.1.2-filtered-telemetry`.

## 2026-07-02

### Backup Verification

- Created a fresh local SQLite backup: `data/backups/iot-20260702T214335Z.sqlite.gz`.
- Restore-checked the local SQLite backup through `/tmp/iot-restore-check.sqlite`; `PRAGMA integrity_check` returned `ok`, and the restored database contained 53,261 readings.
- Found the scheduled restic backup failed at `2026-07-02T02:15:01-05:00` because cron could not find `restic` in its default `PATH`.
- Added an explicit cron-safe `PATH` to both `scripts/restic_iot_backup.sh` and the live cron copy at `~/scripts/restic-iot-backup.sh`.
- Re-ran the live cron script under a minimal cron-like environment; it completed successfully and created restic snapshot `d5802848`.
- Restored the latest restic snapshot into `~/restore-test`; the expected `IoT`, `config`, and `.config/restic` roots were present. Removed the scratch restore tree after verification.
- Ran `restic check`; it completed with no repository errors.

### Architecture And Security Review

- Reviewed an external architecture/security assessment against the local codebase.
- Confirmed the most actionable findings: unauthenticated dashboard on `0.0.0.0:8000`, plaintext/shared-credential MQTT as the current fleet path, no ACL on the port `1883` broker config, retained telemetry inserts on collector restart, no OTA anti-rollback, unpinned PlatformIO platform, and CI static-checking firmware without compiling it.
- Agreed on the practical priority order for the next hardening pass: retained telemetry fix, firmware CI compile plus platform pin, MQTT ACL protection, dashboard access control, then OTA anti-rollback.
- Noted that extracting the dashboard HTML/CSS/JS from the Python monolith is valid maintainability work, but lower priority than the safety and data-integrity fixes above.

## 2026-06-28

### AtticDoor ESP32 Provisioning

- Attached a new ESP32 over USB as the first of two attic sensors and identified it as the new USB serial adapter rather than the existing bench device.
- Flashed the current signed firmware, `0.1.3-signed-ota`, directly over USB.
- Added ignored local mappings so the device appears as `AtticDoor` and is included in the `Separate` Temperature Graph group through a `utility` floorplan zone.
- Initial sensor checks exposed a bad DHT22: first it failed reads and triggered watchdog resets in the DHT read path, then a replacement sensor returned implausible `265.8 F / 99.9%` values that firmware correctly filtered.
- After swapping to another 3-pin DHT22 module, serial output showed stable valid readings and the dashboard API reported `AtticDoor` as online with status `OK`.
- Relocated `AtticDoor` to the attic-door location and verified it came back online from the attic with usable RSSI, plausible attic temperature/humidity telemetry, and firmware `0.1.3-signed-ota`.
- End-of-day live dashboard check showed 21 mapped devices online, 0 stale, and 8 devices on signed OTA.

### Dashboard Rotation Fit And Graph Controls

- Tightened the four-view dashboard rotation for a 1920x1080 display: the 20-device Device List Grid and Latest Readings table now fit cleanly without vertical cutoff.
- Shortened device-card metric labels and firmware labels, and hid the table's device-ID column in the rotated Latest Readings view.
- Restored populated Temperature Graph selector groups by deriving `Inside`, `Outside`, and `Separate` membership from floorplan zone metadata instead of old placeholder location names.
- Kept one laundry-room utility location in the `Inside` graph group while leaving the other utility-marked locations in `Separate`.
- Added a `Pause Views` / `Resume Views` control so the active dashboard view can be inspected without the 5-second rotation advancing; live data refresh continues while paused.
- Verified with `python3 -m py_compile app/iot_home/dashboard.py`, live port `8000`, and 1920x1080 Chromium screenshots of the Device List Grid, Temperature Graph, and Latest Readings views.

### Stale Detection And Signed OTA Batch

- Investigated a signed-OTA device that appeared stale while still publishing fresh telemetry. The device had published startup readings with `1970-01-01T00:00:00Z` before NTP was ready, which caused the dashboard to use a bad device timestamp for stale detection.
- Patched the dashboard API to calculate staleness from the collector receipt timestamp when available while still exposing the device-reported `lastSeen` value for diagnostics.
- Verified the patched dashboard on temporary port `8002` against the production SQLite database; `/api/latest` reported 20 devices online, 0 stale, and the affected device showed `observedAt` from the collector receipt time.
- Rebooted the Pi and verified `iot-home-dashboard.service` came back active on normal port `8000`; `/api/latest` reported 20 mapped devices online, 0 stale, and 7 devices on signed OTA with the collector-receipt-time stale calculation loaded.
- Published signed OTA `0.1.3-signed-ota` to three additional indoor devices. All three reported OTA download start; two reported `rebooting`, and the dashboard API confirmed all three came back online on `0.1.3-signed-ota` with fresh post-reboot telemetry.
- Signed OTA rollout count is now 7 devices. Watch this expanded batch through the next normal telemetry intervals before continuing.

### Dashboard Four-View Rotation

- Updated the IoT Home Monitor dashboard so the main content rotates every 5 seconds through four views: House Diagram, Device List Grid, Temperature Graph, and Latest Readings.
- Kept the header and summary metrics visible while the active main view changes.
- Added a compact active-view status pill with progress dots.
- Verified the edited dashboard with `python3 -m py_compile app/iot_home/dashboard.py`.
- Smoke-tested the edited dashboard on temporary port `8002` against `/home/scotty/IoT/data/iot.db`; `/api/latest` reported 20 devices, all online and non-stale, `/api/history` returned rows, and `/api/floorplan` returned 20 zones.
- Normal dashboard port `8000` was later verified serving the four-view rotation and the collector-receipt-time stale calculation after the Pi reboot.

### End-Of-Day Stop Point

- Refreshed the project roadmap: Phases 0 through 4 are complete for the current local-first system, and Phase 5 is the active plan for fleet operations, dashboard workflows, backups, and staged security hardening.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are active and enabled.
- Verified the dashboard API on port `8000` reports 20 mapped devices, all online and non-stale.
- Verified the signed-OTA first indoor soak batch remains healthy: `RoomE`, `RoomF`, and `RoomA` are online, non-stale, status `OK`, and reporting firmware `0.1.3-signed-ota`.
- Verified `Bench Device` is also online, non-stale, status `OK`, and reporting firmware `0.1.3-signed-ota`.
- Noted `OutdoorA` humidity remains suspect: it previously pegged high and now reports an implausibly low humidity value, so the dashboard rule should be expanded beyond only `>=99%`.
- GitHub CLI is installed locally at `/home/scotty/.local/bin/gh`, but terminal-based GitHub API workflows still require `gh auth login`.
- Stop point: continue signed OTA rollout in small batches, then add Phase 5 operations basics: SQLite backup/export, a sensor replacement checklist, and a compact service/OTA runbook.

## 2026-06-27

### Operational Review

- Verified Git SSH fetch works from the Pi and the local branch is synced with `origin/main`.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are active and enabled.
- Verified the dashboard API on port `8000` reports 20 mapped devices, all online and non-stale.
- Verified the recovered watch-list devices have recent readings within the expected 10-minute telemetry window: `UtilityF`, `OutdoorB`, `RoomH`, `RoomJ`, and `RoomC`.
- Verified `Bench Device` remains visible as the USB bench unit on `/dev/ttyUSB0`.

### Dashboard Floorplan Configuration

- Added `app/iot_home/floorplan.py` for loading and validating a local floorplan JSON file.
- Added tracked `config/floorplan.sample.json` and ignored local `config/floorplan.json` so sensor placements can be tuned on the Pi without editing dashboard JavaScript.
- Added `/api/floorplan` to the dashboard and updated the browser code to use configured zones when present, with built-in approximate zones as a fallback.
- Added `/dashboard-assets/...` serving for local dashboard images under `data/dashboard-assets/`.
- Updated the dashboard systemd unit to pass `--floorplan /home/scotty/IoT/config/floorplan.json` and `--asset-dir /home/scotty/IoT/data/dashboard-assets`.
- Validated the new code with `python3 -m py_compile`, a temporary dashboard server on port `8002`, and the live restarted dashboard service on port `8000`.

## 2026-06-16

### Reviewed Existing Material

- Reviewed existing project notes from local reference material.
- Reviewed current ESP32 code reference from local reference material.
- Reviewed sample AWS IoT payloads from local reference material.
- Reviewed existing AWS-oriented requirements document, `IoT Home Monitoring Requirements v2 2.md`.

### Architecture Direction Changed

- Decided future implementation will remain on ESP32 hardware.
- Removed need for a local OLED/display on each ESP32.
- Removed AWS IoT from the core architecture.
- Chose local-first design using this Raspberry Pi as:
  - MQTT message bus host
  - Data collector
  - SQLite database host
  - Realtime dashboard host
  - Future OTA coordinator

### Local Architecture Documented

- Added `Local-First-Architecture.md`.
- Captured local MQTT topic direction.
- Captured Pi-owned room/location mapping.
- Captured initial local OTA approach.

### USB Test ESP32 Investigation

- Checked for `/dev/ttyUSB*` and `/dev/ttyACM*`; no serial device was visible.
- Checked USB enumeration with elevated `lsusb`; no ESP32 serial bridge was visible.
- Noted likely follow-up items:
  - Confirm data-capable USB cable.
  - Confirm ESP32 board exposes a USB serial interface.
  - Install PlatformIO and/or `esptool`.
  - Ensure user has serial device permissions.
- After changing USB cords, `lsusb` shows `10c4:ea60 Silicon Labs CP210x UART Bridge`.
- Kernel logs show the CP210x adapter attached as `/dev/ttyUSB0`.
- `/dev/ttyUSB0` exists with `root:dialout` ownership and `0660` permissions.
- Installed `esptool` in the project virtual environment.
- Verified ESP32 chip access with `.venv/bin/esptool --port /dev/ttyUSB0 chip-id`.
- Identified chip as ESP32-D0WDQ6 revision v1.0, MAC `<device-mac>`.
- Read serial at 115200 baud for 10 seconds; no firmware log lines appeared.
- Added `scotty` to the `dialout` group from another terminal.
- Verified account-level groups now include `dialout`.
- Installed PlatformIO Core in the project virtual environment.
- Verified `.venv/bin/pio device list` detects `/dev/ttyUSB0` as a CP2102 USB to UART Bridge Controller.

### Project Tracking Started

- Created local documentation structure under `/home/scotty/IoT/docs`.
- Added initial README, progress log, decision record, implementation plan, and hardware notes.
- Added `docs/current-status.md` as the quick restart/context-switch summary.
- Established documentation flow:
  - `docs/current-status.md` for where we are right now.
  - `docs/progress-log.md` for accomplishments.
  - `docs/implementation-plan.md` for plans and next tasks.
  - `docs/decision-record.md` for accepted decisions and reasoning.

### Phase 1 Started

- Installed Mosquitto broker, Mosquitto CLI clients, `python3-paho-mqtt`, and `sqlite3`.
- Added `app/iot_home/simulator.py` for simulated ESP32 MQTT telemetry.
- Added `app/iot_home/collector.py` to subscribe to MQTT and write SQLite readings.
- Added `app/iot_home/dashboard.py` for a local dashboard with browser-side polling.
- Added shared SQLite schema/helpers in `app/iot_home/db.py`.
- Added `docs/phase-1-runbook.md`.
- Verified simulator to MQTT to collector to SQLite with three simulated devices.
- Verified dashboard API reads latest SQLite device state.
- Added stale/offline state to the dashboard API and UI.

### Phase 2 Started

- Created PlatformIO firmware project under `firmware/`.
- Added local MQTT firmware that removes AWS IoT and OLED/display dependencies.
- Preserved DHT22 reads on GPIO 15.
- Added retained MQTT online/offline status and local telemetry topic publishing.
- Added ignored `firmware/include/secrets.h` for WiFi/MQTT settings and tracked `secrets.sample.h`.
- Built firmware successfully with PlatformIO.
- Found system Mosquitto only listened on localhost port `1883`.
- Added project-local Mosquitto test config on LAN port `1884`.
- Uploaded firmware to ESP32 on `/dev/ttyUSB0`.
- Verified real ESP32 telemetry in SQLite:
  - Device: `esp32-device-id`
  - Temperature: `82.9 F`
  - Humidity: `44.4 %`
  - Timestamp: `2026-06-16T20:05:57Z`
  - RSSI: `-61`
- Fixed initial `1970-01-01T00:00:00Z` timestamp by waiting for NTP time before publishing.
- Increased MQTT keepalive to 60 seconds after broker logs showed a timeout with the default.
- Added MQTT username/password support to firmware, collector, and simulator.
- Added `scripts/configure_mosquitto_lan.sh` to configure system Mosquitto for authenticated LAN access on port `1883`.
- Built firmware successfully for authenticated MQTT on port `1883`; upload is pending Mosquitto config.
- Configured system Mosquitto to listen on the LAN with username/password authentication.
- Verified authenticated publish to production Mosquitto.
- Uploaded authenticated port `1883` firmware to ESP32.
- Verified real ESP32 telemetry through production Mosquitto into SQLite:
  - Device: `esp32-device-id`
  - Temperature: `84.4 F`
  - Humidity: `46.6 %`
  - Timestamp: `2026-06-16T21:34:05Z`
  - RSSI: `-42`
- Added Pi-side location mapping support with ignored `config/locations.json`.
- Added local mapping from `esp32-device-id` to `Bench Device`.
- Created public GitHub repository `luminerdy/IoT`.
- Sanitized local git history to remove old reference files, local IPs, credentials, and legacy AWS-oriented material before public publishing.
- Verified staged/local history scans did not find known WiFi password, MQTT password, local LAN IPs, old AWS endpoint, or key material patterns.
- Local git push from this Pi is blocked by missing GitHub HTTPS/SSH credentials.
- Submitted project documentation to GitHub through the GitHub connector.

## 2026-06-18

### Always-On Services

- Added tracked systemd unit files for:
  - `iot-home-collector.service`
  - `iot-home-dashboard.service`
- Added `scripts/install_systemd_services.sh` to install the unit files, create `/etc/iot-home/iot-home.env`, enable the services, and start them.
- Installed and started both services on the Pi.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are running.
- Verified the dashboard is listening on `0.0.0.0:8000`.
- Verified the dashboard API shows `esp32-device-id` mapped to `Bench Device`.
- Verified a fresh real ESP32 reading reached the collector:
  - Temperature: `78.6 F`
  - Humidity: `53.9 %`
  - Timestamp: `2026-06-18T13:59:15Z`
  - RSSI: `-61`
- Published the sanitized local source tree to `luminerdy/IoT` through the GitHub connector after local HTTPS and SSH push attempts remained unavailable.

## 2026-06-19

### Phase 3 Started

- Added retained per-device runtime config handling to ESP32 firmware.
- Supported `reportIntervalSeconds` and `changeThresholdF` from `home/sensors/{deviceId}/config`.
- Added config apply/reject responses on `home/sensors/{deviceId}/response`.
- Added active config reporting in telemetry.
- Added `iot_home.publish_config` for publishing retained config from the Pi, including explicit defaults and retained-delete modes.
- Flashed retained-config firmware to the real ESP32.
- Verified a retained config update changed active config to `reportIntervalSeconds=30` and `changeThresholdF=0.2`.
- Verified telemetry reported the updated active config.
- Verified a non-retained invalid config was rejected without changing the active config.
- Restored retained config to firmware defaults: `reportIntervalSeconds=300` and `changeThresholdF=0.5`.
- Cleared retained simulator telemetry/status messages from MQTT.
- Backed up SQLite to `data/iot-before-sim-cleanup.db`.
- Removed historical `esp32-sim-*` rows from SQLite so the dashboard shows only the physical ESP32.

### Phase 4 Started

- Confirmed the default ESP32 partition table includes `ota_0` and `ota_1`, each `0x140000` bytes.
- Added firmware handling for `ota_update` commands on `home/sensors/{deviceId}/command`.
- Added firmware OTA status publishing on `home/sensors/{deviceId}/ota/status`.
- Added HTTP firmware download, SHA-256 verification, OTA partition write, and reboot handling.
- Added dashboard file serving for staged OTA artifacts under `/firmware/...`.
- Added `iot_home.publish_ota` to stage `firmware.bin`, write `manifest.json`, and publish a per-device OTA command.
- Staged `0.1.0-ota-mvp` under `data/firmware/0.1.0-ota-mvp/`.
- Verified staged firmware download and SHA-256 through a temporary dashboard server on port `8001`.
- USB-flashed the OTA-capable firmware to `esp32-device-id`.
- Verified the ESP32 came back online and published DHT22 telemetry after the OTA-capable USB flash.
- Attempted to restart `iot-home-dashboard.service`, but sudo required an interactive password. The running dashboard still returns 404 for `/firmware/...` until restarted.

## 2026-06-20

### First Live OTA Rollout

- Verified the normal dashboard service on port `8000` serves the staged OTA artifact with a `GET` request:
  - URL: `http://127.0.0.1:8000/firmware/0.1.0-ota-mvp/firmware.bin`
  - Result: HTTP `200`, `824272` bytes.
- Confirmed `curl -I` is not a valid check for the current dashboard server because it does not implement `HEAD` and returns HTTP `501`.
- Published OTA rollout `20260620T180807Z-0.1.0-ota-mvp` to `esp32-device-id`.
- Observed OTA status progression:
  - `downloading` at `2026-06-20T18:08:08Z`
  - `rebooting` at `2026-06-20T18:08:22Z`
- Verified post-OTA telemetry after reboot:
  - Timestamp: `2026-06-20T18:08:33Z`
  - Temperature: `78.6 F`
  - Humidity: `55.9 %`
  - RSSI: `-43`
  - Uptime: `9` seconds
  - Restart reason: `Software`
- Noted follow-up: telemetry still reports `firmwareVersion` as `0.1.0-local` even though the rollout version was `0.1.0-ota-mvp`.
- Updated the firmware build flag to report `FIRMWARE_VERSION` as `0.1.1-ota-version`.
- Built and staged `0.1.1-ota-version`; verified the dashboard served the new artifact with HTTP `200`, `824272` bytes.
- Published OTA rollout `20260620T182134Z-0.1.1-ota-version` to `esp32-device-id`.
- Verified retained device status after reboot reported `firmwareVersion` as `0.1.1-ota-version` at `2026-06-20T18:22:24Z`.
- Verified post-OTA telemetry reported `firmwareVersion` as `0.1.1-ota-version`:
  - Timestamp: `2026-06-20T18:24:12Z`
  - Temperature: `78.1 F`
  - Humidity: `51.0 %`
  - RSSI: `-44`
  - Uptime: `113` seconds
  - Restart reason: `Software`
- Verified the dashboard API now shows `Bench Device` online with `firmwareVersion` set to `0.1.1-ota-version`.

## 2026-06-21

### Web Dashboard Upgrade

- Upgraded `app/iot_home/dashboard.py` from the minimal polling table into a fuller local web app:
  - Summary metrics for device count, average temperature, average humidity, and average RSSI.
  - Per-device cards with online/stale/offline state.
  - Latest-reading table with firmware version and relative last-seen timestamps.
  - Dependency-free inline SVG 24-hour temperature and humidity trend.
- Added bounded SQLite history querying through `iot_home.db.reading_history`.
- Added `/api/history` with bounded `hours` and `limit` query parameters.
- Restarted `iot-home-dashboard.service` so the boot-enabled service loaded the new dashboard code.
- Verified `iot-home-dashboard.service` is enabled, active, and listening on `0.0.0.0:8000`.
- Verified the updated HTML, `/api/latest`, and `/api/history` are served from the live dashboard service.

### Filtered Telemetry Policy

- Confirmed the live retained ESP32 config was `reportIntervalSeconds=300` and `changeThresholdF=0.5`, producing roughly 5-minute readings.
- Decided to return the default report interval to 600 seconds to preserve the original AWS-cost-conscious cadence if telemetry is later forwarded to cloud services.
- Added firmware filtering policy for DHT22 readings:
  - sample every 2 seconds,
  - reject implausible temperature/humidity values,
  - median-filter the last 5 valid samples,
  - suppress one-off temperature jumps more than `8°F` from the recent median unless 3 similar samples arrive consecutively,
  - publish early only after 3 consecutive valid filtered samples exceed the configured temperature threshold.
- Updated default firmware and Pi config helper values to `reportIntervalSeconds=600` and `changeThresholdF=1.0`.
- Updated dashboard stale-device default to 1200 seconds for 10-minute telemetry with headroom.
- Built firmware version `0.1.2-filtered-telemetry`, staged it under `data/firmware/0.1.2-filtered-telemetry/`, verified the dashboard served the binary with HTTP `200`, and published the OTA command.
- Verified the ESP32 came back online and published telemetry with `firmwareVersion` set to `0.1.2-filtered-telemetry`, `numFilteredReadings=0`, and active config `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Could not restart `iot-home-dashboard.service` to load the 1200-second stale threshold because `sudo` requires an interactive password in this session. The updated default will load on the next service restart or reboot.

### Existing Device HTTP OTA

- Checked existing device `http://<private-ip>/update`; it serves ElegantOTA and reports identity `{"id":"C215B80C","hardware":"ESP32"}`.
- Uploaded `0.1.2-filtered-telemetry` using ElegantOTA multipart `POST /update` with fields `MD5` and `firmware`.
- Verified the device joined local MQTT as `esp32-device-id` with `firmwareVersion` set to `0.1.2-filtered-telemetry`.
- Published retained defaults for `esp32-device-id`: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Added `esp32-device-id` to `config/locations.json` as `UtilityADriveay` and updated the current SQLite device row so the live dashboard shows it immediately.
- Updated dashboard code so `/api/latest` reloads `config/locations.json` on each request after the next service restart.
- Committed the local source and documentation changes with message `Add filtered telemetry and dashboard history`.
- Attempted to push to GitHub. HTTPS push failed because no username/token is configured locally; SSH push failed because this Pi does not have a GitHub public key configured.

### Fleet ElegantOTA HTTP Migration

- Verified all ten requested legacy update URLs initially served `/update` with HTTP `200`:
  - `RoomE` `<private-ip>`
  - `RoomA` `<private-ip>`
  - `UtilityA` `<private-ip>`
  - `UtilityF` `<private-ip>`
  - `UtilityD` `<private-ip>`
  - `RoomH` `<private-ip>`
  - `RoomD` `<private-ip>`
  - `OutdoorA` `<private-ip>`
  - `UtilityC` `<private-ip>`
  - `UtilityB` `<private-ip>`
- Added follow-up device candidate:
  - `OutdoorB` `<private-ip>`; this device reportedly connects infrequently. Probes returned `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`. Neighbor discovery resolved MAC `<device-mac>`, so the expected local firmware device ID is `esp32-device-id`.
- Uploaded `data/firmware/0.1.2-filtered-telemetry/firmware.bin` with MD5 `9071f35fb2984b23d05ab371a4192d48` using ElegantOTA multipart `POST /update`.
- Upload responses:
  - HTTP `200 OK`: `RoomE`, `RoomA`, `UtilityA`, `UtilityD`, `RoomH`, `RoomD`, `OutdoorA`, `UtilityC`, `UtilityB`
  - Uncertain/failure: `UtilityF` returned an empty reply during the first POST; retry returned HTTP `400` with body `OTA could not begin`, and old `/update` still responds.
- Confirmed MQTT reporting on `0.1.2-filtered-telemetry`:
  - `RoomE` -> `esp32-device-id`
  - `RoomA` -> `esp32-device-id`
  - `UtilityA` -> `esp32-device-id`
  - `OutdoorA` -> `esp32-device-id`
  - `UtilityC` -> `esp32-device-id`
- Added those mappings to ignored local `config/locations.json`, updated current SQLite device rows, and published retained defaults (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) to the confirmed migrated devices. Also pre-added `OutdoorB` as `esp32-device-id` based on the resolved MAC-derived ID.
- Final legacy `/update` probe after upload:
  - still HTTP `200`: `UtilityF` `<private-ip>`
  - no longer responding on old `/update`: all other nine requested IPs
- `UtilityD`, `RoomH`, `RoomD`, and `UtilityB` had HTTP `200 OK` upload responses and old `/update` disappeared, but no MQTT status/telemetry had been seen by the final check.
- Attempted `systemctl restart iot-home-collector.service` so the collector would reload the new local mappings, but systemd required interactive authentication. A reboot should reload `config/locations.json` for collector writes; the dashboard API already reloads the mapping file dynamically.

### 12-Device Follow-Up Check

- Rechecked the 11 listed fleet devices plus `Bench Device` on 2026-06-21 at about 21:06 CDT.
- Dashboard API confirmed MQTT telemetry on firmware `0.1.2-filtered-telemetry` for `RoomE`, `RoomA`, `UtilityA`, `UtilityD`, `OutdoorA`, `UtilityC`, and `Bench Device`. The existing `UtilityADriveay` sensor is also online on the same firmware.
- Neighbor discovery showed `Bench Device` at `<private-ip>`, matching MAC/device ID `<device-mac>` / `esp32-device-id`.
- Direct HTTP probes showed the migrated MQTT-reporting devices refuse port 80, which is expected after leaving the old ElegantOTA firmware.
- `UtilityF` at `<private-ip>` still serves legacy `Version 5.2.1` at `/` and returns HTTP `401` on `/update`.
- `RoomH` (`<private-ip>`), `RoomD` (`<private-ip>`), `UtilityB` (`<private-ip>`), and `OutdoorB` (`<private-ip>`) failed direct HTTP checks and have no current MQTT telemetry records.
- Corrected the current SQLite `devices` row for `esp32-device-id` from `UNMAPPED` to `UtilityD`; collector service restart remains blocked by interactive systemd authentication, so a reboot or manual service restart is still needed for future collector log lines to load the newest location file.

### Post-Device-Reboot Follow-Up

- Rechecked after manual reboot of all target IoT devices except `OutdoorB` on 2026-06-21 at about 21:32 CDT.
- `RoomD` came online as `esp32-device-id`; neighbor discovery maps that MAC-derived ID to `<private-ip>`.
- `UtilityB` came online as `esp32-device-id`; neighbor discovery maps that MAC-derived ID to `<private-ip>`.
- Added `RoomD` and `UtilityB` to ignored local `config/locations.json`, updated their SQLite device rows, and published retained defaults (`reportIntervalSeconds=600`, `changeThresholdF=1.0`) to both devices.
- Dashboard API now shows `RoomE`, `RoomA`, `UtilityA`, `UtilityADriveay`, `UtilityD`, `RoomD`, `OutdoorA`, `Bench Device`, `UtilityC`, and `UtilityB` online on `0.1.2-filtered-telemetry`.
- `RoomH` (`<private-ip>`) still times out on `/` and `/update` and has no MQTT telemetry record.
- `UtilityF` (`<private-ip>`) still serves legacy `Version 5.2.1` at `/` and returns HTTP `401` on `/update`.
- `OutdoorB` was not rebooted during this check and remains pending/not reporting.
- Attempted `systemctl restart iot-home-collector.service` after adding the new local mappings, but systemd still requires interactive authentication. The dashboard API shows the corrected labels; collector log labels will need a Pi reboot or manual service restart to load the new mapping file.

### Post-Pi-Reboot Verification

- Rechecked after the Pi reboot on 2026-06-21 at about 21:37 CDT.
- Verified `mosquitto.service`, `iot-home-collector.service`, and `iot-home-dashboard.service` are enabled and active since boot at 21:35:51 CDT.
- Verified the collector loaded `config/locations.json`; service logs show `RoomD` and `UtilityB` by name.
- Verified `http://127.0.0.1:8000/api/latest` shows `RoomE`, `RoomA`, `UtilityA`, `UtilityADriveay`, `UtilityD`, `RoomD`, `OutdoorA`, `Bench Device`, `UtilityC`, and `UtilityB` online on `0.1.2-filtered-telemetry`.
- Confirmed `RoomD` and `UtilityB` mappings are present in `config/locations.json` and SQLite device rows.
- Rechecked remaining devices:
  - `UtilityF` (`<private-ip>`) still serves legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`; mapped ID `esp32-device-id` still has no retained MQTT status or telemetry.
  - `RoomH` (`<private-ip>`) still fails direct HTTP checks on `/` and `/update`; no device ID has been discovered from MQTT.
  - `OutdoorB` (`<private-ip>`) still fails direct HTTP checks on `/` and `/update`; mapped expected ID `esp32-device-id` still has no retained MQTT status or telemetry.

### RoomJ Added

- Added `RoomJ` at `<private-ip>` on 2026-06-21 at about 21:43 CDT.
- Verified it still serves legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`.
- Neighbor discovery resolved MAC `<device-mac>`, so the expected local firmware device ID is `esp32-device-id`.
- Added `esp32-device-id` to ignored local `config/locations.json` as `RoomJ`.
- Added a current SQLite device placeholder for `RoomJ` with status `legacy-pending` so the dashboard/API can track it before migration.

### UtilityF OTA Retry

- Retried `UtilityF` (`<private-ip>`, expected `esp32-device-id`) ElegantOTA migration on 2026-06-21 at about 21:50 CDT.
- Precheck confirmed it was still serving legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`.
- Reused `data/firmware/0.1.2-filtered-telemetry/firmware.bin` with MD5 `9071f35fb2984b23d05ab371a4192d48`.
- Authenticated multipart upload returned HTTP `200 OK` with body `OK`; this is different from the earlier `OTA could not begin` failure.
- Follow-up checks found the legacy HTTP endpoint no longer responding and neighbor discovery showing `<private-ip>` as incomplete.
- No fresh MQTT status or telemetry arrived during two post-upload listen windows, and `/api/latest` still shows `UtilityF` offline with no firmware version or last-seen timestamp.
- Updated the SQLite device status for `esp32-device-id` to `ota-upload-ok-no-mqtt`.

### RoomJ OTA Attempt

- Tried migrating `RoomJ` (`<private-ip>`, expected `esp32-device-id`) on 2026-06-21 at about 21:55 CDT.
- Precheck confirmed it was still serving legacy `Version 5.2.1` at `/` and HTTP `401` digest auth at `/update`; neighbor discovery still matched MAC `<device-mac>`.
- Reused `data/firmware/0.1.2-filtered-telemetry/firmware.bin` with MD5 `9071f35fb2984b23d05ab371a4192d48`.
- Two authenticated multipart upload attempts reset the connection without returning `OK`.
- Follow-up checks showed `RoomJ` still serving legacy `Version 5.2.1`, still exposing authenticated `/update`, and not publishing MQTT as `esp32-device-id`.
- Updated the SQLite device status for `esp32-device-id` to `ota-upload-reset`.

### End-of-Day Handoff for 2026-06-22

- Final dashboard/API state before stopping: 10 devices are online on `0.1.2-filtered-telemetry`: `RoomE`, `RoomA`, `UtilityA`, `UtilityADriveay`, `UtilityD`, `RoomD`, `OutdoorA`, `Bench Device`, `UtilityC`, and `UtilityB`.
- Offline mapped follow-up devices:
  - `UtilityF` / `esp32-device-id`: latest ElegantOTA upload returned `OK`, old HTTP disappeared, no MQTT yet; SQLite status `ota-upload-ok-no-mqtt`.
  - `RoomJ` / `esp32-device-id`: two ElegantOTA uploads reset, old HTTP still serves `Version 5.2.1`, no MQTT; SQLite status `ota-upload-reset`.
  - `RoomH` / unknown device ID: earlier upload returned HTTP `200 OK`, old HTTP disappeared, no MQTT.
  - `OutdoorB` / `esp32-device-id`: pre-mapped from MAC, currently not reachable/reporting.
- Tomorrow's first checks should be `/api/latest`, retained MQTT status/telemetry for the expected IDs, and direct HTTP probes for `<private-ip>`, `<private-ip>`, `<private-ip>`, and `<private-ip>`.
- Operational note for tomorrow: if a device accepted upload but has no MQTT, try physical power-cycle before another upload attempt; use USB recovery if it stays silent after power-cycle.

## 2026-06-24

### Device List Cleanup And Recovery

- Removed stale duplicate `UtilityA` device `esp32-device-id` from ignored local `config/locations.json` and from the live SQLite `devices` table. No historical readings existed for that ID. The remaining `UtilityA` device is `esp32-device-id`.
- Added `RoomC` at `<private-ip>`. Neighbor discovery resolved MAC `<device-mac>`, so the expected local firmware device ID is `esp32-device-id`.
- Uploaded `data/firmware/0.1.2-filtered-telemetry/firmware.bin` to `RoomC` through authenticated legacy `/update`; the upload returned HTTP `200 OK` with body `OK`.
- Published retained default config for `esp32-device-id`. Follow-up live data now shows `RoomC` reporting telemetry on `0.1.2-filtered-telemetry`; the device still reports location `UNMAPPED`, and the dashboard maps it to `RoomC` through `config/locations.json`.
- Retried `OutdoorB` at `<private-ip>` using the same firmware artifact and MD5 `9071f35fb2984b23d05ab371a4192d48`; authenticated `/update` returned HTTP `200 OK` with body `OK`.
- Published retained default config for `esp32-device-id`. Follow-up live data shows `OutdoorB` online on `0.1.2-filtered-telemetry`, but as of the latest check it had status only and no DHT telemetry payload yet.
- Removed stale `RetiredLocation` device `esp32-device-id` from ignored local `config/locations.json` and from the live SQLite `devices` table. No historical readings existed for that ID.
- Live SQLite/API state now shows `UtilityF`, `RoomH`, and `RoomJ` reporting on `0.1.2-filtered-telemetry`; those are no longer offline recovery blockers.
- Corrected the local display spelling from `UtilityADriveay` to `OutdoorC` in `config/locations.json`, the live SQLite device row, and current documentation.
- Marked `OutdoorB` as parked for manual physical inspection tomorrow. Check DHT22 VCC, GND, DATA pin, pull-up, and configured GPIO before resuming software-side follow-up.
- Expanded the OTA hardening backlog into concrete bad URL, bad SHA-256, interrupted download, and oversized image test cases.

### OutdoorB ESP32 Replacement

- Identified the new USB-connected ESP32 MAC as `<device-mac>`, so its local firmware device ID is `esp32-device-id`.
- USB-flashed `0.1.2-filtered-telemetry` to the replacement board on `/dev/ttyUSB0`.
- Replaced the local `OutdoorB` mapping from retired `esp32-device-id` to `esp32-device-id`.
- Published retained default config for `esp32-device-id`: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Verified retained MQTT status: `esp32-device-id` is online on firmware `0.1.2-filtered-telemetry`.
- Serial monitor verified the board received and applied the retained config. While bench-connected over USB, it repeatedly read implausible `265.8F` / `99.9%` DHT values, which firmware filtered. Validate normal DHT telemetry after installing it on the verified lightpole wiring.
- Removed the retired `esp32-device-id` row from live SQLite, set the replacement row to `OutdoorB`, and cleared retained MQTT status/config/telemetry for the retired ID.
- After replacing the DHT22 sensor and rebooting the ESP32, `OutdoorB` published valid telemetry: `85.3F`, `51.7%`, RSSI `-43`, status `OK`, sequence `2` at `2026-06-24T16:59:21Z`. The dashboard API maps the row to `OutdoorB`.
- Moved `OutdoorB` to its outside location and restored `Bench Device` as the USB-connected bench target. `esptool` confirmed `/dev/ttyUSB0` is MAC `<device-mac>`, device ID `esp32-device-id`. Use this device for code updates and new feature testing before fleet deployment.
- Added an approximate dashboard house diagram using the current known locations, with live temperature and humidity values placed in each zone. Added follow-up work to replace it with an uploaded house image and configurable sensor overlays. Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py` and tested the new page/API on temporary port `8002`; normal port `8000` needs a reboot or service restart to pick up the code.
- Refined the house diagram labels so humidity and last-seen sit on the line below location/temp, removed the per-room box outline, and changed `RoomG` from exterior/detached to an interior grandkids room.
- Updated the dashboard history graph into a selectable temperature graph with 6h, 12h, 24h, 48h, and 7-day ranges plus per-device toggles. History rows now use the configured location mapping, and the SQLite readings table has a created-at index plus a larger bounded history limit for longer chart ranges.
- Adjusted the dashboard house diagram placement: moved `UtilityA` and `OutdoorC` to the right side, and moved `OutdoorB` to the top row immediately right of `OutdoorA`. Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py`.
- Published the dashboard graph, diagram placement, and memory updates to GitHub as draft PR #1 (`https://github.com/luminerdy/IoT/pull/1`) through the GitHub connector. Local `git push` remains blocked by missing HTTPS/SSH credentials on the Pi.

## 2026-06-26

### Temperature Graph Grouping

- Updated the dashboard Temperature Graph selector from one flat list of per-device toggles to three grouped sections with group-level `All` checkboxes and individual device checkboxes.
- Group membership is currently hard-coded in `app/iot_home/dashboard.py`:
  - `Outside`: `OutdoorA`, `OutdoorB`, `OutdoorC`.
  - `Separate`: `UtilityA`, `UtilityB`, `UtilityC`, `UtilityD`.
  - `Inside`: all other reporting locations not in `Outside` or `Separate`.
- Preserved the existing graph behavior: new devices are selected by default, individual device toggles still work, and the selected readings count updates from the chosen devices.
- Added responsive styling so the three group panels sit side by side on desktop and stack on narrower screens.
- Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py`.
- Tested the updated dashboard on temporary port `8002` with live SQLite data and headless Chromium screenshots. The review server is currently running at `http://<private-ip>:8002`.
- Attempted to restart `iot-home-dashboard.service` so the normal port `8000` would load the new code, but systemd required interactive authentication. Port `8000` may still show the older dashboard until the service is restarted manually or the Pi reboots.
- Confirmed the Pi rebooted at `2026-06-25 22:12:45 CDT`; `iot-home-dashboard.service` started at `2026-06-25 22:12:57 CDT` and normal port `8000` now serves the grouped Temperature Graph code.
- Live dashboard/API smoke test on port `8000` showed 18 mapped devices. The recovered follow-up devices `UtilityF`, `OutdoorB`, `RoomH`, `RoomJ`, and `RoomC` were online with fresh telemetry and had readings in the last hour. `OutdoorC` initially appeared stale, then reported again by the final check at `2026-06-26T18:23:13Z`.

### Humidity Quality Flagging

- Accepted the operating assumption that outdoor DHT22 humidity readings are approximate and can degrade over time.
- Added a dashboard-side suspect humidity flag for outdoor DHT22 locations when humidity is at or above `99%`.
- The current outdoor humidity flag applies to `OutdoorA`, `OutdoorB`, and `OutdoorC`; live data flags `OutdoorA` at `99.9%`, while current `OutdoorB` and `OutdoorC` readings are not flagged.
- Suspect humidity is excluded from the dashboard average humidity summary, while temperature and device status remain visible.
- Verified syntax with `python3 -m py_compile app/iot_home/dashboard.py` and smoke-tested the modified dashboard on temporary port `8002`.
- Tried to restart `iot-home-dashboard.service` so normal port `8000` would load the suspect humidity flag, but systemd required interactive authentication. The change will load after a manual service restart or the planned reboot.

### USB Cable Check

- Plugged the retired old `OutdoorB` ESP32 into the test cable to confirm the cable supports data.
- The Pi enumerated the board as a CP2102 serial bridge on `/dev/ttyUSB1`; the existing bench ESP32 remained on `/dev/ttyUSB0`.
- `esptool` connected to `/dev/ttyUSB1` and read MAC `<device-mac>`, confirming the cable is data-capable.
- The probe/reset briefly caused retained MQTT/status and SQLite rows for retired device `esp32-device-id`; cleared retained MQTT state and removed the transient SQLite row. Final API check showed `unmapped_count=0`.

### OTA Failure-Path Testing

- Tested the bad OTA URL failure path against USB-recoverable `Bench Device` / `esp32-device-id`.
- Published rollout `20260626T153900Z-bad-url-test` with a missing firmware URL: `http://iot-pi.local:8000/firmware/bad-url-test/missing.bin`.
- Observed OTA status progression on `home/sensors/esp32-device-id/ota/status`: `downloading` with message `ota download started`, then `failed` with message `firmware download failed`.
- Verified the retained status still reports firmware `0.1.2-filtered-telemetry`; the retained online timestamp did not refresh, so there was no indication of a reboot during the bad URL test.
- Tested the bad SHA-256 failure path against `Bench Device` using the valid staged firmware URL and an intentionally wrong SHA-256.
- First bad-SHA command used a version string longer than the firmware's 31-character field and was rejected as `invalid ota command`; reran with shorter version `bad-sha-test`.
- Published rollout `20260626T190800Z-bad-sha` with URL `http://<private-ip>:8000/firmware/0.1.2-filtered-telemetry/firmware.bin`, size `825200`, and SHA-256 set to all `f` characters.
- Observed OTA status progression: `downloading` with message `ota download started`, then `rejected` with message `firmware sha256 mismatch`.
- Verified retained status still reports firmware `0.1.2-filtered-telemetry`; retained online timestamp did not refresh. Latest telemetry after the earlier bad-SHA attempt still had high uptime and `restartReason` set to `PowerOn`, so there was no indication of a reboot.
- Tested the interrupted download failure path against `Bench Device` using a temporary HTTP server on port `8003`.
- The temporary server advertised the full firmware `Content-Length` of `825200` bytes but sent only `65536` bytes before closing the connection. Server logs confirmed the ESP32 at `<private-ip>` requested the interrupted firmware URL.
- Published rollout `20260626T191300Z-interrupted` with URL `http://<private-ip>:8003/firmware-interrupted.bin`, the correct full SHA-256, and expected size `825200`.
- Observed OTA status progression: `downloading` with message `ota download started`, then `failed` with message `firmware length mismatch`.
- Stopped the temporary port `8003` server after the test. Retained status still reported firmware `0.1.2-filtered-telemetry`, and the dashboard still showed `Bench Device` online and not stale.
- Tested the oversized image failure path against `Bench Device` using a temporary HTTP server on port `8003`.
- The temporary server advertised `Content-Length: 2000000`, larger than the OTA partition capacity, and sent a small placeholder body. Server logs confirmed the ESP32 at `<private-ip>` requested the oversized firmware URL.
- Published rollout `20260626T203800Z-oversized` with URL `http://<private-ip>:8003/firmware-oversized.bin`, expected size `2000000`, and a placeholder SHA-256.
- Observed OTA status progression: `downloading` with message `ota download started`, then `failed` with message `ota partition unavailable`.
- Stopped the temporary port `8003` server after the test. Retained status still reported firmware `0.1.2-filtered-telemetry`, and the dashboard still showed `Bench Device` online and not stale.
- Added decision record `DR-015` accepting the OTA failure-path safety validation for the local OTA MVP, while leaving firmware signing, rollback workflow, and richer rollout controls as Phase 5 hardening work.
- Updated the implementation plan and current status so OTA failure-path testing is marked complete and new ESP32 provisioning is listed as an upcoming task.
- Added decision record `DR-016` accepting outdoor DHT22 humidity as advisory and documenting the dashboard suspect-humidity threshold.

## Ready Next

- After the planned reboot, verify port `8000` loads the suspect humidity flag and no retired `OutdoorB` / `UNMAPPED` row is present.
- Provision the remaining new ESP32 devices when they arrive.
- Confirm newly recovered devices stay stable across a few 10-minute telemetry intervals.
- Confirm replacement `OutdoorB` remains stable across a few 10-minute telemetry intervals.

## 2026-06-27

### First Indoor Signed-OTA Soak Batch

- Published signed OTA `0.1.3-signed-ota` only to three indoor devices: `RoomE` / `esp32-device-id`, `RoomF` / `esp32-device-id`, and `RoomA` / `esp32-device-id`.
- Observed expected OTA status progression on all three: `downloading` / `ota download started`, then `rebooting` / `firmware update applied`.
- Verified all three returned online and non-stale through SQLite/dashboard API:
  - `RoomE`: `0.1.3-signed-ota`, status `OK`.
  - `RoomF`: `0.1.3-signed-ota`, status `OK`.
  - `RoomA`: `0.1.3-signed-ota`, status `OK`.
- Hold further fleet rollout for a few hours of soak time.

### RoomB ESP32 Provisioned

- Detected a new ESP32 on `/dev/ttyUSB1`; existing bench `Bench Device` remained on `/dev/ttyUSB0`.
- Read MAC `<device-mac>`, so the local device ID is `esp32-device-id`.
- USB-flashed firmware `0.1.2-filtered-telemetry` to `/dev/ttyUSB1`.
- Published retained default config: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Verified MQTT status, config response, and telemetry:
  - status: `online`
  - firmware: `0.1.2-filtered-telemetry`
  - config response: `applied`
  - telemetry: `78.6F`, `48.9%`, RSSI `-46`, status `OK`
- Mapped `esp32-device-id` to `RoomB` in local `config/locations.json` and updated the current SQLite device/reading rows.
- Added `RoomB` to the dashboard house diagram between `RoomA` and `RoomC`.
- Verified `http://127.0.0.1:8000/api/latest` shows `RoomB` online and `UNMAPPED` count is `0`.

### UtilityE ESP32 Provisioned

- Detected a new ESP32 on `/dev/ttyUSB1`; existing bench `Bench Device` remained on `/dev/ttyUSB0`.
- Read MAC `<device-mac>`, so the local device ID is `esp32-device-id`.
- USB-flashed firmware `0.1.2-filtered-telemetry` to `/dev/ttyUSB1`.
- Published retained default config: `reportIntervalSeconds=600`, `changeThresholdF=1.0`.
- Verified MQTT status, retained config, and telemetry:
  - status: `online`
  - firmware: `0.1.2-filtered-telemetry`
  - telemetry: `76.6F`, `54.4%`, RSSI `-45`, status `OK`
- Mapped `esp32-device-id` to `UtilityE` in local `config/locations.json` and updated the current SQLite device/reading rows.
- Added `UtilityE` to the dashboard house diagram between `RoomA` and `RoomG`.
- Added `UtilityE` to the dashboard Temperature Graph `Separate` group with other non-room/equipment readings.

### Wrap-Up Notes

- Decision: classify `UtilityE` as a `Separate` graph location because it is an equipment/utility reading rather than a normal room-comfort trend.
- Observation: both new boards were provisioned successfully over the same data-capable USB cable on `/dev/ttyUSB1`; `Bench Device` remained the bench device on `/dev/ttyUSB0`.
- Issue: `iot-home-dashboard.service` still cannot be restarted from this session because `systemctl`/`sudo` requires interactive authentication, so the new floorplan code should be verified after reboot.

### GitHub SSH and Dashboard Verification

- Created and configured a dedicated GitHub SSH key at `/home/scotty/.ssh/id_ed25519_github`.
- Switched the local repo remote to `git@github.com:luminerdy/IoT.git`.
- Added a repo-local `core.sshCommand` so Git bypasses the broken system SSH config symlink at `/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf`.
- Verified GitHub accepts the key as `luminerdy`.
- Reconciled the local `codex/dashboard-graph-diagram-memory` branch with its remote duplicate-history branch using a merge commit that keeps the local tree canonical.
- Pushed the reconciled branch to GitHub; `HEAD` and `origin/codex/dashboard-graph-diagram-memory` are now in sync at merge commit `ad87d94`.
- Verified normal port `8000` serves the suspect humidity flag and includes `RoomB` and `UtilityE` in the house diagram floorplan.
- Verified live device state shows 20 mapped devices online, no `UNMAPPED` rows, and no retired `esp32-device-id` row.
- Confirmed recovered-device telemetry is still arriving for `UtilityF`, `OutdoorB`, `RoomH`, `RoomJ`, and `RoomC`.

### Ready Next

- New ESP32 provisioning is complete for the current batch: `RoomB` and `UtilityE`.
- Continue watching recovered devices across a few 10-minute telemetry intervals.
- Start the next dashboard improvement: replace the approximate house diagram with an uploaded house image and configurable sensor placement overlays.

## 2026-06-30

### Project Hardening Review Follow-Up

- Added Python project metadata in `pyproject.toml` so the Pi-side app can be installed/tested consistently.
- Added focused pytest coverage for:
  - SQLite telemetry/status recording and history bounds.
  - Location mapping behavior.
  - Floorplan config validation and normalization.
  - Retained config payload generation.
- Added `.github/workflows/ci.yml` to run Python compile/tests and PlatformIO firmware checking on GitHub pushes/PRs.
- Updated the CI firmware job to copy `firmware/include/secrets.sample.h` to ignored `secrets.h` so clean GitHub runners can run PlatformIO checks without local secrets.
- Added `.gitignore` entries for `.pytest_cache/` and `*.egg-info/`.
- Ran validation locally:
  - `python3 -m compileall app scripts`: passed.
  - `./.venv/bin/python -m pytest`: 17 tests passed.
  - `./.venv/bin/platformio check -d firmware`: passed with only low/style warnings.
  - Re-ran firmware check with sample `secrets.h` to confirm the GitHub Actions clean-runner path works.
- Fixed the prior medium firmware static-analysis warning by adding an explicit invalid-count guard in `medianOf`.

### Backup Prep

- Added `scripts/backup_sqlite.sh` for verified SQLite backups using SQLite `.backup`, `PRAGMA integrity_check`, and gzip compression.
- Ran the backup script successfully against `data/iot.db`; it created an ignored local backup under `data/backups/`.
- Added `docs/backup-runbook.md` with local backup, restore-check, and future AWS S3 copy instructions through `S3_URI=s3://...`.
- Updated `README.md` and `docs/implementation-plan.md` to point at the backup runbook and note that the initial backup workflow is in place.

### Sunroom Recovery

- Investigated `Sunroom` / `esp32-device-id` after it stopped reporting and showed repeated low sequence numbers.
- Confirmed the device had disappeared from the LAN neighbor table while nearby Sunroom devices continued reporting.
- After the Sunroom wire was replaced, the device returned to the LAN and began reporting again.
- Follow-up check showed `Sunroom` online, last sequence `27`, RSSI around `-67`, and steady roughly 10-minute telemetry intervals.
- Decision: continue watching `Sunroom` before including it in a signed OTA batch.

### Fleet State At Stop

- Latest live SQLite check around 22:45 CDT showed 21 devices online and 0 offline.
- Firmware counts:
  - `0.1.3-signed-ota`: 8 devices.
  - `0.1.2-filtered-telemetry`: 13 devices.
- One online signed-OTA device is currently `UNMAPPED` and needs local mapping cleanup.
- Worktree intentionally remains uncommitted with the June 30 hardening changes pending review/commit.

### Ready Next

- Review, commit, and push the hardening changes.
- Watch `Sunroom` through more normal telemetry intervals before OTA.
- Clean up the current `UNMAPPED` device mapping.
- Continue signed OTA rollout in small batches after the fleet is stable.
- Finish AWS S3 backup setup later this week: bucket/prefix, IAM credentials, and a restore drill.

## 2026-07-01

### Hardening Commit Prep

- Rechecked the live dashboard API on normal port `8000` before committing the June 30 hardening changes.
- `/api/latest` reported 21 mapped devices online, 0 stale, and no `UNMAPPED` rows.
- Firmware counts remained:
  - `0.1.3-signed-ota`: 8 devices.
  - `0.1.2-filtered-telemetry`: 13 devices.
- `Sunroom` remained online after the wire replacement and had advanced to sequence 145.
- `/api/floorplan` loaded the local configured zones; `backgroundImage` is still unset until the actual house image is uploaded.

# LED-Off Firmware Rollout

- Built and signed firmware `0.1.5-led-off` with anti-rollback build number `2026071201`; the staged and dashboard-served binaries matched SHA-256 `6f8caa48dc9f948c7d4e714a0645eeea66c731d53d62a4631f99076e347febf8`.
- USB-flashed the exact build to `Sunroom Test` / `esp32-9c9c1fda3670` and verified it remained online and non-stale through a full ten-minute telemetry interval.
- Rolled out successfully to `Den`, `Kitchen`, `Office`, `FrontBedroom`, `Entryway`, and `Laundryroom`; each returned online and non-stale on `0.1.5-led-off`.
- Initial canary commands using `iot-pi.local` were acknowledged but could not reach the firmware endpoint. Retrying with the numeric Pi LAN address completed successfully.
- Paused the rollout at `MasterBedroom`: it remains online and non-stale on `0.1.4-antirollback`, but repeated commands were missed during MQTT reconnects or stopped after `downloading`. Do not retry broadly until its connectivity/download path is checked. `Studio` and the rest of the fleet were intentionally left untouched after the batch pause.
# 2026-07-24

## Unattended Device Recovery

- Added firmware `0.1.6-recovery` build `2026072401` for difficult-to-access
  sensors.
- Replaced the indefinitely blocking initial WiFi connection loop with bounded
  reconnect attempts.
- Added a recovery reboot after 15 continuous minutes without both WiFi and
  MQTT, plus a deterministic device-staggered safety reboot after 7–8 days.
- Persisted `network_timeout` or `weekly_safety` across the restart so the next
  successful telemetry reports the cause once.
- Kept recovery timers outside the synchronous OTA application path so they
  cannot interrupt an update.
- Built successfully, passed all 30 Python tests and PlatformIO static analysis,
  and USB-flashed `/dev/ttyUSB0`. The uploader confirmed MAC
  `<bench-mac>`, matching `Sunroom Test` / `esp32-device-id`.
- Verified Sunroom Test returned online and non-stale on `0.1.6-recovery`,
  publishing fresh DHT22 telemetry after the flash.

# 2026-07-25

## Recovery Firmware Bench Gate

- Isolated only `Sunroom Test` from MQTT by temporarily flashing a build pointed
  at a user-owned TCP proxy on port `1884`; the production broker and fleet
  remained online.
- Held the MQTT path down continuously for the production 15-minute interval.
  The device logged `Recovery restart requested: network_timeout` and rebooted.
- Restored the proxy and verified automatic MQTT recovery. The first telemetry
  reported `restartReason=Software` and `recoveryReason=network_timeout`; the
  next successful telemetry reported `recoveryReason=none`.
- Temporarily shortened the safety interval to 60–70 seconds on the USB bench
  device. It rebooted with `weekly_safety`, returned automatically, reported
  the reason once, and cleared it on the next telemetry.
- Restored the real 7–8 day safety constants and direct MQTT port `1883`, then
  rebuilt and USB-flashed the exact production `0.1.6-recovery` build
  `2026072401`.
- Recorded production firmware SHA-256
  `56db51afdd3d3e05c3e2741ea90ee6143046b332de19774f317c634b432b8704`.
- Verified fresh production telemetry from `Sunroom Test` with
  `recoveryReason=none`.
- Final checks passed: PlatformIO build, 30 Python tests, and PlatformIO static
  analysis with only the existing five low-level style notices.

# 2026-08-01

## Backup Verification And Recovery Firmware Rollout

- Verified the scheduled 02:05 local SQLite backup
  `data/backups/iot-20260801T070501Z.sqlite.gz` by restoring it and running
  `PRAGMA integrity_check;`; the result was `ok`.
- Verified the scheduled 02:15 restic/S3 snapshot `b4d60733`, confirmed it
  contains `data/iot.db` and the current local SQLite archive, and completed
  `restic check --read-data-subset=1/100` with no errors.
- Staged and served the bench-validated `0.1.6-recovery` build `2026072401`;
  the served binary matched SHA-256
  `56db51afdd3d3e05c3e2741ea90ee6143046b332de19774f317c634b432b8704`.
- Rolled the firmware out in acknowledged batches. Each device either reported
  `downloading` then `rebooting`, or was confirmed at build `2026072401` by an
  anti-rollback rejection on a retry.
- Retried Kitchen after its first command was missed and confirmed a complete
  acknowledged update. Updated MasterBedroom alone; it completed
  `downloading` then `rebooting` successfully.
- Final dashboard verification showed 23 devices online, 0 stale, 0 unmapped,
  and all 23 on `0.1.6-recovery`. Mosquitto, collector, and dashboard services
  remained active with no recent warning-level logs.

# 2026-08-06

## Firmware Download Capability Key

- Implemented SEC-016 capability-key protection for `/firmware/` downloads;
  missing, wrong, or duplicate keys receive HTTP 401 and the configured key is
  compared in constant time.
- Required `FIRMWARE_DOWNLOAD_KEY` at dashboard startup and added it to the
  systemd environment installer without exposing the value in tracked files.
- Updated OTA staging and manifest reconstruction to add or preserve the
  URL-encoded capability key. Removed secret-bearing OTA payloads from CLI
  success output and removed query strings from dashboard access logs.
- Added live HTTP route tests plus OTA URL construction/preservation tests.
  All 39 Python tests passed. A temporary LAN listener returned 401 for missing
  and wrong keys, returned 200 for the correct key, and served bytes matching
  the staged production artifact. No OTA command or firmware update was sent.
- Installed the generated capability key in `/etc/iot-home/iot-home.env`, mode
  `0600`, and restarted the dashboard. Live port `8000` returned HTTP 401 for
  missing and wrong keys and HTTP 200 for the correct key; the downloaded bytes
  matched the staged `0.1.6-recovery` artifact. Mosquitto, collector, and
  dashboard remained active, and the USB-connected `Sunroom Test` bench device
  remained online on Wi-Fi. No OTA command or firmware update was sent.

## Authenticated Dashboard Writes And Resource Handling

- Added constant-time HTTP Basic authentication for `POST /api/locations` and
  an explicit `--allow-unauthenticated-read` deployment option so normal
  dashboard viewing remains open on the home network by policy.
- Added username/password fields to Manage Devices; credentials are sent only
  on mapping writes. Generated credentials are stored outside the repository
  in the root-owned service environment and a user-readable mode-`0600` local
  credentials file.
- Serialized location-file read/modify/write operations to prevent lost
  concurrent updates.
- Removed per-request schema initialization and explicitly close every
  per-request SQLite connection; schema initialization remains at startup.
- Added Basic-auth and live HTTP tests, including eight concurrent mapping
  writes with all updates preserved.
- Deployed the updated dashboard with `--allow-unauthenticated-read`. Live
  verification returned 200 for an unauthenticated read, 401 for missing and
  wrong write credentials, and reached normal 400 input validation with valid
  credentials. Basic-authenticated firmware download returned the exact staged
  production bytes. All three core services remained active with no warning
  logs, and the USB bench device remained online; no OTA command was sent.

## Historical Data Preservation Decision

- Rejected the proposed 90-day telemetry pruning plan. Readings, deployment
  attempts, and system metrics must be preserved indefinitely.
- Reframed the next database milestone as integrity checks, backup validation,
  capacity/free-space monitoring, alerts, and safe optimization without row
  deletion. Any future lossless archival requires explicit approval plus copy,
  integrity, row-count, and restore verification before live rows move.
