# MQTT Schema

Draft schema for the local-first implementation.

## Topic Principles

- Use stable device IDs in topics, not room names.
- Keep room/location mapping on the Pi.
- Use retained messages for latest telemetry, latest status, and latest config.
- Use QoS 1 for telemetry, status, config, command, and OTA status.

## Topics

```text
home/sensors/{deviceId}/telemetry
home/sensors/{deviceId}/status
home/sensors/{deviceId}/config
home/sensors/{deviceId}/command
home/sensors/{deviceId}/response
home/sensors/{deviceId}/ota/status
home/fleet/config
home/ota/available
```

## Telemetry

Topic:

```text
home/sensors/{deviceId}/telemetry
```

Example:

```json
{
  "schemaVersion": "2.0-local",
  "seq": 1,
  "deviceId": "esp32-aabbccddeeff",
  "location": "UNMAPPED",
  "firmwareVersion": "0.1.0",
  "sensorType": "DHT22",
  "datetime": "2026-06-16T17:00:00Z",
  "temperature": 76.4,
  "humidity": 41.2,
  "units": {
    "temperature": "F"
  },
  "rssi": -58,
  "uptimeSeconds": 3600,
  "numReadErrors": 0,
  "restartReason": "PowerOn",
  "status": "OK"
}
```

## Status

Topic:

```text
home/sensors/{deviceId}/status
```

Example online payload:

```json
{
  "deviceId": "esp32-aabbccddeeff",
  "status": "online",
  "firmwareVersion": "0.1.0",
  "datetime": "2026-06-16T17:00:00Z"
}
```

Example Last Will payload:

```json
{
  "deviceId": "esp32-aabbccddeeff",
  "status": "offline",
  "reason": "mqtt_lwt"
}
```

## Config

Topic:

```text
home/sensors/{deviceId}/config
```

Retained: yes

Example:

```json
{
  "reportIntervalSeconds": 300,
  "changeThresholdF": 0.5
}
```

Supported fields:

- `reportIntervalSeconds`: number, 10 to 3600.
- `changeThresholdF`: number, 0.1 to 10.0.

Devices ignore unsupported fields and reject config payloads that do not contain any supported fields.

Publishing an empty retained payload deletes the retained broker value. A connected device treats that message as a request to restore firmware defaults; an offline device will not receive it later. Publish explicit default values when the reset must be applied on the next reconnect.

## Response

Topic:

```text
home/sensors/{deviceId}/response
```

Config apply/reject example:

```json
{
  "deviceId": "esp32-aabbccddeeff",
  "type": "config",
  "status": "applied",
  "message": "config applied",
  "datetime": "2026-06-16T17:00:00Z",
  "activeConfig": {
    "reportIntervalSeconds": 300,
    "changeThresholdF": 0.5
  }
}
```
