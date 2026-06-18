# IoT Home Monitoring - Local-First Architecture

## Direction

Future implementation will stay on ESP32 devices, remove all local ESP32 displays, and remove AWS IoT from the core design.

The Raspberry Pi host will run the local message bus, data collector, database, and dashboard. ESP32 sensors will publish temperature, humidity, and health telemetry to the Pi over the local network.

Current target host:

- Hostname: `PiServer`
- OS/kernel family: Raspberry Pi Debian, aarch64
- Role: MQTT broker, collector service, SQLite storage, web dashboard

## Goals

- Keep ESP32 sensor nodes simple and reliable.
- Run the complete system locally on the home network.
- Display current room readings in near real time.
- Avoid cloud dependency for normal operation.
- Preserve a clean path for OTA updates and future remote access without requiring AWS.

## Proposed Architecture

```text
ESP32 + DHT22 sensors
    |
    | MQTT over local WiFi
    v
Raspberry Pi / PiServer
    |
    +-- Mosquitto MQTT broker
    +-- Collector service
    +-- SQLite database
    +-- Dashboard web app
    +-- Firmware/OTA file server, optional
```

## Raspberry Pi Services

### Development/Test ESP32

One ESP32 is intended to remain connected to the Pi over USB for development and test flashing.

Uses:

- Validate firmware builds before OTA rollout.
- Flash recovery builds over USB if OTA breaks.
- Exercise MQTT publishing against the local broker.
- Run short soak tests while connected to serial logs.

Expected serial device paths:

```text
/dev/ttyUSB0
/dev/ttyACM0
```

Current observation on this Pi:

- No `/dev/ttyUSB*` or `/dev/ttyACM*` device was visible during review.
- `lsusb` did not show a typical ESP32 USB serial bridge.
- `esptool.py` and PlatformIO were not installed on PATH.
- User `scotty` is not currently in a typical serial access group such as `dialout`.

Items to resolve before USB flashing from the Pi:

- Confirm the ESP32 is connected with a data-capable USB cable, not charge-only.
- Confirm the board is powered and exposes a USB serial chip.
- Identify the serial adapter type, usually CP210x, CH340, FTDI, or native USB CDC.
- Install firmware tooling on the Pi, preferably PlatformIO and `esptool`.
- Add the runtime user to the serial device group if needed.

Once visible, the basic smoke test is:

```bash
esptool.py --port /dev/ttyUSB0 chip_id
```

or, for PlatformIO:

```bash
pio device list
pio run -t upload --upload-port /dev/ttyUSB0
pio device monitor --port /dev/ttyUSB0 --baud 115200
```

### MQTT Broker

Use Mosquitto as the local MQTT broker.

- Listens on the local network.
- Receives telemetry from each ESP32.
- Retains latest telemetry and device status messages.
- Provides local publish/subscribe for dashboard and collector services.

Recommended ports:

- `1883`: MQTT on trusted local network
- `8883`: MQTT over TLS, optional later

For the first version, plain MQTT on an isolated/trusted LAN is acceptable if the sensors are on a private home network. If sensors are placed on an IoT VLAN or untrusted WiFi, enable MQTT username/password and consider TLS.

### Collector Service

The collector subscribes to telemetry topics, validates messages, and writes data to SQLite.

Responsibilities:

- Subscribe to `home/sensors/+/telemetry`.
- Subscribe to `home/sensors/+/status`.
- Validate JSON schema and numeric ranges.
- Store latest reading per device/location.
- Store recent history for dashboard charts if desired.
- Track stale/offline devices.

### Dashboard

The dashboard runs locally on the Pi.

Recommended stack:

- Python FastAPI
- SQLite
- Jinja2 templates
- HTMX or Server-Sent Events for live updates
- Systemd services for automatic startup

Initial dashboard scope:

- Current temperature per room.
- Current humidity per room.
- Last update time.
- Online/offline/stale status.
- WiFi signal quality if ESP32 reports RSSI.
- Responsive layout for desktop and phone.

## ESP32 Firmware

The ESP32 firmware should be rebuilt as a modular PlatformIO project.

Core responsibilities:

- Connect to WiFi.
- Connect to local MQTT broker on `PiServer`.
- Read DHT22 sensor.
- Validate readings.
- Publish telemetry at a configurable interval.
- Publish online/offline status using MQTT Last Will and Testament.
- Report health fields such as firmware version, RSSI, uptime, error count, and restart reason.

Removed responsibilities:

- No OLED/local display.
- No AWS IoT certificates.
- No AWS Device Shadow.
- No AWS IoT Jobs.
- No hardcoded MAC-to-room mapping in firmware.

## MQTT Topic Design

Recommended topics:

```text
home/sensors/{deviceId}/telemetry
home/sensors/{deviceId}/status
home/sensors/{deviceId}/config
home/sensors/{deviceId}/command
home/sensors/{deviceId}/response
home/fleet/config
```

Use `deviceId` or `thingName`, not room name, in the topic. Room/location names should be metadata in the message or resolved by the Pi. This avoids topic changes when a device moves rooms or a room is renamed.

Example device ID:

```text
esp32-aabbccddeeff
```

## Telemetry Message

Example:

```json
{
  "schemaVersion": "2.0-local",
  "seq": 12345,
  "deviceId": "esp32-aabbccddeeff",
  "location": "Kitchen",
  "sensorType": "DHT22",
  "datetime": "2026-06-16T16:30:00Z",
  "temperature": 76.4,
  "humidity": 41.2,
  "units": {
    "temperature": "F"
  },
  "rssi": -58,
  "uptimeSeconds": 68400,
  "numReadErrors": 2,
  "restartReason": "PowerOn",
  "status": "OK"
}
```

## Location Mapping

The Pi should own location mapping.

Recommended first version:

```json
{
  "esp32-aabbccddeeff": "Kitchen",
  "esp32-112233445566": "Office"
}
```

Store this in a local `locations.json` file or a SQLite table. The firmware may include a fallback location like `UNMAPPED`, but it should not require reflashing to change room names.

## Configuration

Replace AWS Device Shadow with local MQTT config.

Options:

1. Pi publishes retained config messages to `home/sensors/{deviceId}/config`.
2. ESP32 subscribes to its config topic.
3. ESP32 validates config and reports applied values in telemetry or response topic.

Example retained config:

```json
{
  "reportIntervalSeconds": 300,
  "changeThresholdF": 0.5,
  "humidityThreshold": 2.0,
  "reportMode": "both"
}
```

## OTA Updates

Without AWS IoT Jobs, OTA can still be automated locally.

Recommended phased approach:

1. MVP: USB flashing during development.
2. Phase 2: ESP32 checks the Pi for a firmware manifest.
3. Phase 3: Dashboard can trigger rollout to selected devices.
4. Phase 4: Fleet rollout controls with canary, pause, retry, and rollback.

Local OTA model:

```text
Pi hosts firmware manifest and binaries over HTTP.
ESP32 receives update command over MQTT.
ESP32 downloads firmware from Pi.
ESP32 verifies checksum.
ESP32 writes OTA partition and reboots.
```

Example manifest URL:

```text
http://piserver.local:8080/firmware/manifest.json
```

### OTA Control Flow

The Pi should be the OTA coordinator.

```text
Dashboard or CLI
    |
    v
OTA coordinator on Pi
    |
    +-- Publishes retained desired firmware version
    +-- Publishes per-device update commands
    +-- Serves firmware binaries over HTTP
    +-- Tracks acknowledgments and failures
    v
ESP32 devices
```

Recommended MQTT topics:

```text
home/ota/available
home/ota/rollout/{rolloutId}
home/sensors/{deviceId}/command
home/sensors/{deviceId}/response
home/sensors/{deviceId}/ota/status
```

Example update command:

```json
{
  "command": "ota_update",
  "rolloutId": "2026-06-16-v0.2.0",
  "version": "0.2.0",
  "url": "http://piserver.local:8080/firmware/0.2.0/firmware.bin",
  "sha256": "replace-with-real-checksum",
  "size": 1048576,
  "reboot": true
}
```

Example OTA status response:

```json
{
  "deviceId": "esp32-aabbccddeeff",
  "rolloutId": "2026-06-16-v0.2.0",
  "version": "0.2.0",
  "status": "downloading",
  "progress": 42,
  "message": "Downloaded 438 KB"
}
```

Status values:

```text
queued
accepted
rejected
downloading
verifying
installing
rebooting
succeeded
failed
rolled_back
```

### OTA Safety Requirements

Local OTA should include the following from the first OTA-capable release:

- Use ESP32 OTA partitions so the previous firmware remains recoverable.
- Verify SHA-256 before installing.
- Reject firmware that is too large for the OTA partition.
- Reject downgrades unless explicitly allowed by the command.
- Publish status before download, during progress, before reboot, and after successful boot.
- Mark the new firmware valid only after it connects to WiFi, connects to MQTT, reads the sensor, and publishes telemetry.
- Keep USB flashing available as the recovery path.

Firmware signing can be added after basic OTA works. For a home-local system, checksum validation plus controlled local network access is a reasonable first step; signed firmware is better before exposing update controls remotely.

### OTA Rollout Strategy

Rollouts should be staged even on a small home fleet.

Recommended process:

1. Flash the USB-connected test ESP32.
2. Run a short local test and verify serial logs.
3. OTA one canary device.
4. Wait for successful reboot and at least two telemetry messages.
5. Roll out to the remaining devices in small batches.
6. Stop automatically if failures exceed the threshold.

Initial failure threshold:

- Stop rollout after 1 failed canary.
- Stop rollout if more than 20% of a batch fails.
- Do not retry failed devices indefinitely; require manual review after 2 failures.

Rollback strategy:

- Keep the previous firmware binary on the Pi.
- Allow a rollback command to target a known-good version.
- Devices should report current version and last update result in every telemetry payload.

### Firmware Manifest

The Pi should store firmware releases in a predictable directory:

```text
/opt/iot-dashboard/firmware/
  manifest.json
  0.1.0/
    firmware.bin
    firmware.sha256
  0.2.0/
    firmware.bin
    firmware.sha256
```

Example manifest:

```json
{
  "currentVersion": "0.2.0",
  "versions": {
    "0.2.0": {
      "url": "http://piserver.local:8080/firmware/0.2.0/firmware.bin",
      "sha256": "replace-with-real-checksum",
      "size": 1048576,
      "releasedAt": "2026-06-16T00:00:00Z",
      "notes": "Local MQTT telemetry MVP"
    }
  }
}
```

## Database

Use SQLite on the Pi.

Suggested tables:

```sql
CREATE TABLE readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    location TEXT,
    sensor_type TEXT,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    datetime TEXT NOT NULL,
    rssi INTEGER,
    status TEXT,
    seq INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    location TEXT,
    firmware_version TEXT,
    last_seen TEXT,
    online INTEGER NOT NULL DEFAULT 0,
    last_rssi INTEGER,
    last_status TEXT
);
```

## MVP Scope

Recommended first implementation:

- Mosquitto broker on Pi.
- ESP32 firmware publishes local MQTT telemetry.
- Pi collector writes readings to SQLite.
- Dashboard displays current readings and stale/offline state.
- Location mapping managed on the Pi.
- Manual USB firmware flashing while firmware stabilizes.

Defer until after MVP:

- Local OTA rollout automation.
- Historical charts.
- Dashboard admin panel.
- Authentication and remote access.
- TLS for MQTT, unless network segmentation requires it immediately.

## Open Decisions

- MQTT authentication: anonymous local-only vs username/password.
- MQTT TLS: defer or enable from day one.
- Dashboard stack: FastAPI/HTMX recommended unless another stack is preferred.
- Location mapping storage: `locations.json` vs SQLite table.
- OTA strategy: ArduinoOTA push, HTTP pull from Pi, or dashboard-managed rollouts.
- Remote access: local only, VPN, or tunnel.
