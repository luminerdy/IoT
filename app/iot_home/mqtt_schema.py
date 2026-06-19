from __future__ import annotations

TELEMETRY_TOPIC = "home/sensors/{device_id}/telemetry"
STATUS_TOPIC = "home/sensors/{device_id}/status"
CONFIG_TOPIC = "home/sensors/{device_id}/config"
COMMAND_TOPIC = "home/sensors/{device_id}/command"
RESPONSE_TOPIC = "home/sensors/{device_id}/response"
OTA_STATUS_TOPIC = "home/sensors/{device_id}/ota/status"
TELEMETRY_SUBSCRIPTION = "home/sensors/+/telemetry"
STATUS_SUBSCRIPTION = "home/sensors/+/status"


def device_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 4:
        return None
    if parts[0] != "home" or parts[1] != "sensors":
        return None
    return parts[2]
