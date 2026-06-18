from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import paho.mqtt.client as mqtt

from iot_home.db import DEFAULT_DB_PATH, connect, init_db, record_status, record_telemetry
from iot_home.locations import DEFAULT_LOCATIONS_PATH, load_locations, mapped_location
from iot_home.mqtt_schema import STATUS_SUBSCRIPTION, TELEMETRY_SUBSCRIPTION


LOG = logging.getLogger("iot_home.collector")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect MQTT sensor readings into SQLite.")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host.")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path.")
    parser.add_argument("--client-id", default="iot-pi-collector", help="MQTT client ID.")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username.")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password.")
    parser.add_argument(
        "--locations",
        type=Path,
        default=DEFAULT_LOCATIONS_PATH,
        help="JSON file mapping device IDs to display locations.",
    )
    return parser.parse_args()


def validate_telemetry(payload: dict) -> None:
    required = ["deviceId", "datetime", "temperature", "humidity"]
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"missing telemetry fields: {', '.join(missing)}")

    temperature = float(payload["temperature"])
    humidity = float(payload["humidity"])
    if not -40 <= temperature <= 185:
        raise ValueError(f"temperature out of range: {temperature}")
    if not 0 <= humidity <= 100:
        raise ValueError(f"humidity out of range: {humidity}")


def validate_status(payload: dict) -> None:
    if "deviceId" not in payload:
        raise ValueError("missing status field: deviceId")
    if payload.get("status") not in {"online", "offline"}:
        raise ValueError(f"invalid device status: {payload.get('status')}")


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = connect(args.db)
    init_db(conn)
    locations = load_locations(args.locations)
    if locations:
        LOG.info("Loaded %d location mapping(s) from %s", len(locations), args.locations)

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code != 0:
            LOG.error("MQTT connect failed: %s", reason_code)
            return
        LOG.info("Connected to MQTT broker %s:%s", args.broker, args.port)
        client.subscribe([(TELEMETRY_SUBSCRIPTION, 1), (STATUS_SUBSCRIPTION, 1)])
        LOG.info("Subscribed to %s and %s", TELEMETRY_SUBSCRIPTION, STATUS_SUBSCRIPTION)

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if message.topic.endswith("/telemetry"):
                validate_telemetry(payload)
                payload["location"] = mapped_location(
                    str(payload["deviceId"]),
                    payload.get("location"),
                    locations,
                )
                record_telemetry(conn, payload)
                LOG.info(
                    "Telemetry %s location=%s temp=%.1f humidity=%.1f",
                    payload["deviceId"],
                    payload["location"],
                    float(payload["temperature"]),
                    float(payload["humidity"]),
                )
            elif message.topic.endswith("/status"):
                validate_status(payload)
                record_status(conn, payload)
                LOG.info("Status %s %s", payload["deviceId"], payload["status"])
        except Exception:
            LOG.exception("Failed to process MQTT message on %s", message.topic)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
    if args.username:
        client.username_pw_set(args.username, args.password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        LOG.info("Collector stopped")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
