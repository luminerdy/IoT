from __future__ import annotations

import argparse
import json
import os

import paho.mqtt.client as mqtt

from iot_home.mqtt_schema import CONFIG_TOPIC


DEFAULT_REPORT_INTERVAL_SECONDS = 600
DEFAULT_CHANGE_THRESHOLD_F = 1.0
MIN_REPORT_INTERVAL_SECONDS = 10
MAX_REPORT_INTERVAL_SECONDS = 3600
MIN_CHANGE_THRESHOLD_F = 0.1
MAX_CHANGE_THRESHOLD_F = 10.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish retained runtime config for an ESP32 sensor.")
    parser.add_argument("device_id", help="Device ID, for example esp32-9c9c1fda3670.")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host.")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--client-id", default="iot-pi-config-publisher", help="MQTT client ID.")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username.")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password.")
    parser.add_argument(
        "--report-interval",
        type=int,
        help="Telemetry report interval in seconds. Valid range: 10-3600.",
    )
    parser.add_argument(
        "--change-threshold",
        type=float,
        help="Temperature change threshold in Fahrenheit. Valid range: 0.1-10.0.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the retained config for this device by publishing an empty retained message.",
    )
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="Publish firmware default config as a retained message for offline-safe reset behavior.",
    )
    return parser.parse_args()


def config_payload(args: argparse.Namespace) -> bytes:
    selected_actions = sum(
        [
            args.clear,
            args.defaults,
            args.report_interval is not None or args.change_threshold is not None,
        ]
    )
    if selected_actions != 1:
        raise SystemExit("provide exactly one of --clear, --defaults, or config field flags")

    if args.clear:
        return b""

    if args.defaults:
        payload: dict[str, float | int] = {
            "reportIntervalSeconds": DEFAULT_REPORT_INTERVAL_SECONDS,
            "changeThresholdF": DEFAULT_CHANGE_THRESHOLD_F,
        }
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    payload: dict[str, float | int] = {}
    if args.report_interval is not None:
        if not MIN_REPORT_INTERVAL_SECONDS <= args.report_interval <= MAX_REPORT_INTERVAL_SECONDS:
            raise SystemExit(
                f"--report-interval must be between {MIN_REPORT_INTERVAL_SECONDS} and "
                f"{MAX_REPORT_INTERVAL_SECONDS} seconds"
            )
        payload["reportIntervalSeconds"] = args.report_interval

    if args.change_threshold is not None:
        if not MIN_CHANGE_THRESHOLD_F <= args.change_threshold <= MAX_CHANGE_THRESHOLD_F:
            raise SystemExit(
                f"--change-threshold must be between {MIN_CHANGE_THRESHOLD_F} and "
                f"{MAX_CHANGE_THRESHOLD_F} Fahrenheit"
            )
        payload["changeThresholdF"] = round(args.change_threshold, 1)

    if not payload:
        raise SystemExit("provide --report-interval, --change-threshold, or --clear")

    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def main() -> None:
    args = parse_args()
    topic = CONFIG_TOPIC.format(device_id=args.device_id)
    payload = config_payload(args)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
    if args.username:
        client.username_pw_set(args.username, args.password)
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()
    result = client.publish(topic, payload, qos=1, retain=True)
    result.wait_for_publish(timeout=10)
    client.loop_stop()
    client.disconnect()

    if not result.is_published():
        raise SystemExit(f"publish to {topic} did not complete")
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise SystemExit(f"publish to {topic} failed with MQTT result code {result.rc}")

    if args.clear:
        print(f"deleted retained config on {topic}")
    else:
        print(f"published retained config on {topic}: {payload.decode('utf-8')}")


if __name__ == "__main__":
    main()
