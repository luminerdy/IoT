from __future__ import annotations

import argparse
import json
import math
import os
import random
import signal
import ssl
import time
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt

from iot_home.mqtt_schema import STATUS_TOPIC, TELEMETRY_TOPIC


DEVICES = [
    {"deviceId": "esp32-sim-kitchen", "location": "RoomF", "baseTemp": 73.5, "baseHumidity": 42.0},
    {"deviceId": "esp32-sim-office", "location": "RoomD", "baseTemp": 75.0, "baseHumidity": 39.0},
    {"deviceId": "esp32-sim-bedroom", "location": "Room", "baseTemp": 71.8, "baseHumidity": 45.0},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish simulated ESP32 DHT22 telemetry.")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host.")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between publish cycles.")
    parser.add_argument("--client-id", default="iot-simulated-esp32-fleet", help="MQTT client ID.")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username.")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password.")
    parser.add_argument("--tls", action="store_true", help="Use MQTT over TLS.")
    parser.add_argument("--ca-cert", type=Path, help="CA certificate for MQTT TLS.")
    return parser.parse_args()


def iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def status_payload(device: dict, status: str) -> bytes:
    return json.dumps(
        {
            "deviceId": device["deviceId"],
            "status": status,
            "firmwareVersion": "sim-0.1.0",
            "datetime": iso_now(),
        },
        separators=(",", ":"),
    ).encode("utf-8")


def telemetry_payload(device: dict, seq: int, tick: int) -> bytes:
    wave = math.sin((tick + seq) / 8)
    temperature = device["baseTemp"] + wave + random.uniform(-0.2, 0.2)
    humidity = device["baseHumidity"] + (wave * 1.5) + random.uniform(-0.5, 0.5)
    return json.dumps(
        {
            "schemaVersion": "2.0-local",
            "seq": seq,
            "deviceId": device["deviceId"],
            "location": device["location"],
            "firmwareVersion": "sim-0.1.0",
            "sensorType": "DHT22",
            "datetime": iso_now(),
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
            "units": {"temperature": "F"},
            "rssi": random.randint(-68, -42),
            "uptimeSeconds": tick * 5,
            "numReadErrors": 0,
            "restartReason": "PowerOn",
            "status": "OK",
        },
        separators=(",", ":"),
    ).encode("utf-8")


def main() -> None:
    args = parse_args()
    running = True

    def stop(signum, frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls:
        client.tls_set(ca_certs=str(args.ca_cert) if args.ca_cert else None, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()

    for device in DEVICES:
        topic = STATUS_TOPIC.format(device_id=device["deviceId"])
        client.publish(topic, status_payload(device, "online"), qos=1, retain=True)

    seq_by_device = {device["deviceId"]: 0 for device in DEVICES}
    tick = 0

    try:
        while running:
            tick += 1
            for device in DEVICES:
                device_id = device["deviceId"]
                seq_by_device[device_id] += 1
                topic = TELEMETRY_TOPIC.format(device_id=device_id)
                payload = telemetry_payload(device, seq_by_device[device_id], tick)
                client.publish(topic, payload, qos=1, retain=True)
                print(f"published {topic} seq={seq_by_device[device_id]}", flush=True)
            time.sleep(args.interval)
    finally:
        for device in DEVICES:
            topic = STATUS_TOPIC.format(device_id=device["deviceId"])
            client.publish(topic, status_payload(device, "offline"), qos=1, retain=True)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
