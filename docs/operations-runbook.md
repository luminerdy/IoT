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

## Backup Check

Scheduled backups:

- Local SQLite export runs daily at `02:05` CDT.
- Restic/S3 off-device backup runs daily at `02:15` CDT.

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

## OTA Rollout

Standing rule: no firmware build goes to fleet devices until the exact binary has passed validation on the USB-connected bench ESP32.

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
```
