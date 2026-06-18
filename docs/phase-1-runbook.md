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
http://piserver.local:8000
```

or:

```text
http://<pi-ip-address>:8000
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
- Services are not installed under systemd yet.
- Real ESP32 publishing is still blocked by USB visibility/tooling.
