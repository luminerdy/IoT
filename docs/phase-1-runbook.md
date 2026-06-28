# Phase 1 Runbook

Goal: prove the local Pi data path with simulated ESP32 devices.

## Installed Packages

- `mosquitto`
- `mosquitto-clients`
- `python3-paho-mqtt`
- `sqlite3`

## Terminal 1: Start Collector

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.collector
```

The collector subscribes to:

```text
home/sensors/+/telemetry
home/sensors/+/status
```

It writes to:

```text
data/iot.db
```

## Optional LAN Test Broker

The system Mosquitto package may listen only on localhost by default. For ESP32 WiFi tests without changing system config, run a project-local broker on port `1884`:

```bash
cd /home/scotty/IoT
mosquitto -c config/mosquitto-local-test.conf
```

Then start the collector against that port:

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.collector --port 1884
```

## Terminal 2: Start Simulator

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.simulator
```

The simulator publishes three retained simulated ESP32 devices every five seconds.

## Terminal 3: Start Dashboard

```bash
cd /home/scotty/IoT
PYTHONPATH=app python3 -m iot_home.dashboard --host <bind-address> --port 8000
```

Open:

```text
http://iot-pi.local:8000
```

or:

```text
http://<pi-ip-address>:8000
```

## Always-On Services

Install or refresh the collector and dashboard systemd services:

```bash
cd /home/scotty/IoT
scripts/install_systemd_services.sh
```

The installer creates `/etc/iot-home/iot-home.env`, installs service files under `/etc/systemd/system`, enables the services, and starts them.

Service names:

```text
iot-home-collector.service
iot-home-dashboard.service
mosquitto.service
```

Check status:

```bash
systemctl status --no-pager --full iot-home-collector.service iot-home-dashboard.service mosquitto.service
```

View recent logs:

```bash
journalctl -u iot-home-collector.service -u iot-home-dashboard.service --since '30 minutes ago' --no-pager
```

## Smoke Checks

Check broker manually:

```bash
mosquitto_sub -h localhost -t 'home/sensors/+/telemetry' -C 1
```

Check database manually:

```bash
sqlite3 data/iot.db 'select device_id, location, temperature, humidity, datetime from readings order by id desc limit 5;'
```

## Current Limitations

- Dashboard is intentionally minimal and uses browser-side polling.
- Reboot-time service recovery has not been verified with an actual Pi reboot yet.
