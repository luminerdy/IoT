# Operations Runbook

Use this for routine fleet checks, service recovery, OTA rollout discipline, runtime config changes, backups, and sensor replacement. Phase-specific details remain in the phase runbooks.

## Daily Health Check

Check services:

```bash
systemctl --no-pager --plain status mosquitto.service iot-home-collector.service iot-home-dashboard.service
```

Check recent logs:

```bash
journalctl -u iot-home-collector.service -u iot-home-dashboard.service --since '30 minutes ago' --no-pager
```

Check dashboard API summary:

```bash
curl -fsS http://127.0.0.1:8000/api/latest
```

Expected normal state:

- 23 mapped devices online (current fleet size; adjust when devices are added or retired).
- 0 stale devices.
- 0 `UNMAPPED` rows.
- During the paused LED-off rollout: 7 devices on `0.1.5-led-off`, 16 on `0.1.4-antirollback`, and 0 stale.

Firmware `0.1.6-recovery` adds two unattended recovery paths for difficult-to-access
devices:

- A device that cannot restore both WiFi and MQTT for 15 continuous minutes
  records `network_timeout` and reboots.
- A healthy device performs a staggered safety reboot every 7–8 days. The
  device ID determines the offset so the fleet does not reboot together.
- The first successful telemetry after either recovery includes
  `recoveryReason`; it is cleared after that publish. `restartReason` continues
  to report the ESP32 hardware reset classification.
- OTA download and application are synchronous, so recovery timers are not
  evaluated in the middle of an update.

Treat repeated `network_timeout`, watchdog, panic, or brownout reasons as a
fault to investigate rather than relying on rebooting to conceal it.

## Pi3 External Watchdog

The external Raspberry Pi 3 is available through the `pi-watchdog` SSH alias.
Its `pi-watchdog.service` checks PiServer once per minute and requires the
gateway to remain reachable while PiServer ping, SSH, and dashboard checks all
fail. Production relay recovery occurs after 10 consecutive failed checks.
GPIO17 removes PiServer power for 15 seconds, then returns low to restore power.
A one-hour cooldown applies between actual relay cycles; the first qualified
recovery after watchdog startup is immediately eligible.

Use read-only checks first:

```bash
ssh pi-watchdog 'systemctl is-active pi-watchdog.service; systemctl is-enabled pi-watchdog.service; pinctrl get 17; journalctl -u pi-watchdog.service --since "30 minutes ago" --no-pager'
```

Do not manually toggle GPIO17 or initiate a PiServer shutdown merely to test the
watchdog without explicit approval. Investigate repeated relay recoveries as a
system, power, or network fault.

Import recent watchdog relay events into the dashboard-visible monitoring table:

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.post_reboot_check \
  --db data/iot.db \
  --backup-dir data/backups \
  --import-watchdog \
  --watchdog-since '24 hours ago'
```

The command also records the current post-reboot health check. It is read-only
except for inserting `monitoring_events` rows in SQLite.

Install or refresh the boot-time recorder:

```bash
scripts/install_post_reboot_monitoring.sh
```

The unit is `iot-home-post-reboot-check.service`; it runs once after boot and
imports the previous two hours of Pi3 watchdog journal entries.

## Backup Check

Scheduled backups:

- Local SQLite export runs daily at `02:05` CDT.
- Restic/S3 off-device backup runs daily at `02:15` CDT.
- Lossless database maintenance runs from a systemd timer at `03:05` CDT,
  after both backup jobs. It checks the live database and newest compressed
  backup, runs `PRAGMA optimize`, reports table/storage capacity, and fails if
  the backup is stale or capacity thresholds are crossed. It never prunes
  historical rows.

Check the preservation job and its next scheduled run:

```bash
systemctl status --no-pager iot-home-db-maintenance.timer
systemctl list-timers --all iot-home-db-maintenance.timer
journalctl -u iot-home-db-maintenance.service --since '2 days ago' --no-pager
```

Run the same check manually without restarting any production service:

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.db_maintenance \
  --db data/iot.db --backup-dir data/backups
```

Exit `1` means a freshness or capacity alert; exit `2` means an integrity,
backup restore, or execution failure. Defaults are a 30-hour maximum backup
age, 10 GiB and 10% minimum free space, and a 10 GiB maximum live database.
Install or refresh the units with `scripts/install_db_maintenance_timer.sh`.

### Database schema migrations

Schema changes are packaged as numbered SQL files and applied automatically at
collector startup. Never set `PRAGMA user_version` manually. Before deploying a
collector version with pending migrations:

1. Create a fresh online SQLite backup and verify its integrity.
2. Apply the candidate migrations to a scratch restore and compare preserved
   table row counts and original reading values.
3. During an explicitly approved maintenance window, restart the collector with
   the new code.
4. Verify `PRAGMA integrity_check`, `PRAGMA user_version`, collector logs, fresh
   telemetry, and preservation of `readings`, `deployment_attempts`, and
   `system_metrics`.

If migration fails, leave the collector stopped on the unchanged transactional
schema, retain the failed logs and backup, and investigate before retrying. Do
not delete duplicate history to force an index to build.

Check the local database-only backup first:

```bash
tail -80 ~/logs/iot-sqlite-backup.log
find /home/scotty/IoT/data/backups -maxdepth 1 -type f -name 'iot-*.sqlite.gz' -printf '%TY-%Tm-%Td %TH:%TM %s %f\n' | sort | tail -5
```

Restore-check the latest local SQLite archive:

```bash
cd /home/scotty/IoT
latest="$(find data/backups -maxdepth 1 -type f -name 'iot-*.sqlite.gz' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
gunzip -c "$latest" > /tmp/iot-local-restore-check.sqlite
sqlite3 /tmp/iot-local-restore-check.sqlite "PRAGMA integrity_check;"
rm -f /tmp/iot-local-restore-check.sqlite
```

Check restic/S3:

```bash
tail -120 ~/logs/restic-iot-backup.log
source ~/config/backup.env
restic snapshots --latest 5
```

Restore-check the latest snapshot into a scratch directory:

```bash
target="/tmp/iot-restic-restore-check-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$target"
source ~/config/backup.env
restic restore latest --target "$target"
test -d "$target/home/scotty/IoT"
test -d "$target/home/scotty/config"
test -d "$target/home/scotty/.config/restic"
rm -rf "$target"
```

Run a repository check:

```bash
source ~/config/backup.env
restic check --read-data-subset=1/100
```

For database-only backup:

```bash
cd /home/scotty/IoT
scripts/backup_sqlite.sh data/iot.db
```

## Runtime Config

Use the admin MQTT credentials for retained config changes. Do not use the fleet `iot` user for config publishing after ACL activation.

```bash
cd /home/scotty/IoT
source /home/scotty/.config/iot-home/operator-credentials.env
MQTT_USERNAME="$MQTT_ADMIN_USERNAME" MQTT_PASSWORD="$MQTT_ADMIN_PASSWORD" PYTHONPATH=app python3 -m iot_home.publish_config esp32-device-id \
  --report-interval 600 \
  --change-threshold 1.0
```

Restore firmware defaults for a device:

```bash
MQTT_USERNAME="$MQTT_ADMIN_USERNAME" MQTT_PASSWORD="$MQTT_ADMIN_PASSWORD" PYTHONPATH=app python3 -m iot_home.publish_config esp32-device-id --defaults
```

Clear retained config only when intentionally returning an online device to firmware defaults:

```bash
MQTT_USERNAME="$MQTT_ADMIN_USERNAME" MQTT_PASSWORD="$MQTT_ADMIN_PASSWORD" PYTHONPATH=app python3 -m iot_home.publish_config esp32-device-id --clear
```

## USB Per-Device MQTT TLS Provisioning

This is a physical bench/migration operation. It does not authorize changing
the live Mosquitto listener. First confirm the target on `/dev/ttyUSB0`, create
its unique broker user without using batch-mode passwords, and keep its CA and
password outside the repository:

Schema v2 separates the TCP endpoint from the TLS verification name. Use a
reliable `--connect-host` endpoint, such as the Pi LAN IP, and a
`--tls-hostname` value that appears in the broker certificate's DNS
subject-alternative-name (`PiServer.local` on this installation). This preserves
certificate/SNI validation while avoiding ESP32 mDNS resolution failures. The
legacy `--host` alias still sends one hostname for both roles.

```bash
scripts/add_mqtt_device_user.sh esp32-device-id
PYTHONPATH=app .venv/bin/python -m iot_home.provision_mqtt \
  --serial-port /dev/ttyUSB0 \
  --device-id esp32-device-id \
  --connect-host 10.10.10.123 \
  --tls-hostname PiServer.local \
  --mqtt-port 8883 \
  --ca-cert /etc/mosquitto/certs/iot-home/ca.crt
```

The provisioning tool prompts for the same password without echo. It may
instead read a mode-0600 `--password-file`; there is deliberately no password
argument. Verify the device reports fresh telemetry through TLS under only its
own ACL subtree. For a controlled bench rollback, remove only the MQTT NVS
profile and verify the compiled migration fallback reconnects:

```bash
PYTHONPATH=app .venv/bin/python -m iot_home.provision_mqtt \
  --serial-port /dev/ttyUSB0 --clear
```

Clearing does not erase the OTA build high-water mark. Never retire the shared
credential or plaintext fleet listener until every active device has been
individually provisioned and observed.

## OTA Rollout

Standing rule: no firmware build goes to fleet devices until the exact binary has passed validation on the USB-connected bench ESP32.

The collector may record desired-version mismatches, but it never publishes
OTA commands. Command publication is an explicit operator action using the
admin credentials below. The per-device target ACL can be verified without
touching the live broker:

```bash
.venv/bin/python -m pytest -q -o addopts='' tests/test_mqtt_acl.py
```

Confirm bench USB access:

```bash
ls -l /dev/ttyUSB0
groups
```

Build and stage firmware:

```bash
cd /home/scotty/IoT
.venv/bin/pio run -d firmware
PYTHONPATH=app python3 -m iot_home.publish_ota esp32-device-id 0.1.5-led-off \
  --base-url http://<pi-lan-ip>:8000 \
  --build-number 2026071201 \
  --stage-only
```

Verify staged firmware is served:

```bash
curl -s -o /tmp/iot-fw-test.bin -w '%{http_code} %{size_download}\n' \
  http://127.0.0.1:8000/firmware/0.1.5-led-off/firmware.bin
```

Publish OTA only after bench validation:

```bash
source /home/scotty/.config/iot-home/operator-credentials.env
MQTT_USERNAME="$MQTT_ADMIN_USERNAME" MQTT_PASSWORD="$MQTT_ADMIN_PASSWORD" PYTHONPATH=app python3 -m iot_home.publish_ota esp32-device-id 0.1.5-led-off \
  --base-url http://<pi-lan-ip>:8000 \
  --build-number 2026071201
```

Watch status:

```bash
pw=$(awk -F'"' '/MQTT_PASSWORD/ {print $2; exit}' firmware/include/secrets.h)
mosquitto_sub -h localhost -p 1883 -u iot -P "$pw" -t 'home/sensors/esp32-device-id/ota/status' -v
```

Expected successful progression:

```text
downloading
rebooting
online telemetry on the target firmware version
```

Roll out to the fleet in small batches. After each batch, verify `/api/latest` shows the expected firmware, no stale devices, and no `UNMAPPED` rows.

For each target, actively observe both `downloading` and `rebooting`, then
confirm fresh telemetry on the target version. If a command is missed, a
terminal OTA status is absent, or the device does not converge, stop expanding
the batch. Do not repeatedly hammer a reconnecting device. The July 12 rollout
also showed that ESP32 clients could not resolve `iot-pi.local`; use the
verified Pi LAN address for OTA until sensor-side mDNS resolution is proven.

## Add Or Replace A Sensor

Use this checklist when adding a new ESP32, replacing a failed board, replacing a DHT22, or moving a sensor.

1. Label the physical board and intended location before flashing or moving it.
2. Connect over USB and confirm the serial device:

```bash
ls -l /dev/ttyUSB0
.venv/bin/pio device list
```

3. Flash only the current bench-validated firmware over USB for new or recovered devices.
4. Confirm serial output shows WiFi, MQTT, firmware version, stable device ID, and valid DHT22 readings.
5. Add or update the ignored local mapping in `config/locations.json`.
6. If the sensor appears on the floorplan, add or adjust the ignored local zone in `config/floorplan.json`.
7. Publish retained default config for the stable device ID:

```bash
source /home/scotty/.config/iot-home/operator-credentials.env
MQTT_USERNAME="$MQTT_ADMIN_USERNAME" MQTT_PASSWORD="$MQTT_ADMIN_PASSWORD" PYTHONPATH=app python3 -m iot_home.publish_config esp32-device-id --defaults
```

8. Watch MQTT or the dashboard until the device reports valid telemetry on the expected location.
9. Check `/api/latest` for 0 stale devices and 0 `UNMAPPED` rows.
10. If replacing a device, remove stale retained MQTT state and old SQLite device rows only after confirming no historical readings need to be preserved under the retired ID.
11. Update `docs/progress-log.md` with the device ID placeholder, location, firmware version, and verification result.

## Common Recovery

Restart collector after code or service config changes:

```bash
sudo systemctl restart iot-home-collector.service
```

Restart dashboard after dashboard code, floorplan serving, or service config changes:

```bash
sudo systemctl restart iot-home-dashboard.service
```

If non-interactive `sudo` is unavailable, use the existing service `Restart=on-failure` policy only when intentional and record that in `docs/progress-log.md`.

After any reboot or restart:

```bash
systemctl is-active mosquitto.service iot-home-collector.service iot-home-dashboard.service
systemctl is-enabled mosquitto.service iot-home-collector.service iot-home-dashboard.service
curl -fsS http://127.0.0.1:8000/api/latest
PYTHONPATH=app python3 -m iot_home.post_reboot_check --db data/iot.db --backup-dir data/backups
```
