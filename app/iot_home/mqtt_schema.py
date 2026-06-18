from __future__ import annotations

TELEMETRY_TOPIC = "home/sensors/{device_id}/telemetry"
STATUS_TOPIC = "home/sensors/{device_id}/status"
TELEMETRY_SUBSCRIPTION = "home/sensors/+/telemetry"
STATUS_SUBSCRIPTION = "home/sensors/+/status"


def device_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 4:
        return None
    if parts[0] != "home" or parts[1] != "sensors":
        return None
    return parts[2]
