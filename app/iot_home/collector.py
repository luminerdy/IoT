from __future__ import annotations

import argparse
import json
import logging
import os
import ssl
import time
from pathlib import Path

import paho.mqtt.client as mqtt

from iot_home.db import (
    DEFAULT_DB_PATH,
    connect,
    init_db,
    observed_ip,
    recent_deployment_attempt_exists,
    record_deployment_attempt,
    record_status,
    record_system_metric,
    record_telemetry,
    update_deployment_attempt,
)
from iot_home.locations import DEFAULT_LOCATIONS_PATH, load_locations, mapped_location
from iot_home.mqtt_schema import COMMAND_TOPIC, STATUS_SUBSCRIPTION, TELEMETRY_SUBSCRIPTION
from iot_home.publish_ota import DEFAULT_FIRMWARE_DIR, command_from_manifest


LOG = logging.getLogger("iot_home.collector")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect MQTT sensor readings into SQLite.")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host.")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path.")
    parser.add_argument("--client-id", default="iot-pi-collector", help="MQTT client ID.")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username.")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password.")
    parser.add_argument("--tls", action="store_true", help="Use MQTT over TLS.")
    parser.add_argument("--ca-cert", type=Path, help="CA certificate for MQTT TLS.")
    parser.add_argument(
        "--locations",
        type=Path,
        default=DEFAULT_LOCATIONS_PATH,
        help="JSON file mapping device IDs to display locations.",
    )
    parser.add_argument(
        "--desired-firmware-version",
        help="Desired firmware version. Mismatched device reports create deployment attempt records.",
    )
    parser.add_argument(
        "--auto-ota",
        action="store_true",
        help="Publish a staged OTA command when a firmware version mismatch is detected.",
    )
    parser.add_argument(
        "--firmware-dir",
        type=Path,
        default=DEFAULT_FIRMWARE_DIR,
        help="Directory containing staged OTA manifests.",
    )
    parser.add_argument("--base-url", default="http://iot-pi.local:8000", help="Base dashboard URL reachable by ESP32.")
    parser.add_argument(
        "--firmware-download-key",
        default=os.getenv("FIRMWARE_DOWNLOAD_KEY"),
        help="Firmware download capability key (defaults to FIRMWARE_DOWNLOAD_KEY).",
    )
    parser.add_argument(
        "--ota-cooldown-seconds",
        type=int,
        default=86400,
        help="Minimum seconds between deployment attempts for the same device and target version.",
    )
    parser.add_argument(
        "--pi-temperature-interval-seconds",
        type=int,
        default=600,
        help="Seconds between Raspberry Pi CPU temperature samples (default: 600).",
    )
    return parser.parse_args()


PI_TEMPERATURE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")


def read_pi_temperature_f(path: Path = PI_TEMPERATURE_PATH) -> float:
    celsius = float(path.read_text(encoding="utf-8").strip()) / 1000.0
    return round((celsius * 9 / 5) + 32, 1)


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


def maybe_trigger_deployment(
    client: mqtt.Client,
    conn,
    args: argparse.Namespace,
    payload: dict,
) -> None:
    desired_version = args.desired_firmware_version
    if not desired_version:
        return

    device_id = str(payload["deviceId"])
    current_version = payload.get("firmwareVersion")
    if not current_version or current_version == desired_version:
        return
    if recent_deployment_attempt_exists(conn, device_id, desired_version, args.ota_cooldown_seconds):
        LOG.info("Skipping OTA mismatch for %s; deployment attempt is inside cooldown", device_id)
        return

    ip = observed_ip(payload)
    attempt_id = record_deployment_attempt(
        conn,
        device_id=device_id,
        from_version=str(current_version),
        to_version=desired_version,
        observed_ip=ip,
        status="detected",
        message="firmware version mismatch detected",
    )
    LOG.info(
        "Firmware mismatch for %s: current=%s desired=%s ip=%s attempt=%s",
        device_id,
        current_version,
        desired_version,
        ip or "unknown",
        attempt_id,
    )

    if not args.auto_ota:
        return

    try:
        command = command_from_manifest(
            args.firmware_dir,
            desired_version,
            args.base_url,
            args.firmware_download_key,
        )
    except Exception as exc:
        update_deployment_attempt(conn, attempt_id, status="failed", message=str(exc))
        LOG.exception("Cannot publish OTA for %s", device_id)
        return

    topic = COMMAND_TOPIC.format(device_id=device_id)
    mqtt_payload = json.dumps(command, separators=(",", ":")).encode("utf-8")
    result = client.publish(topic, mqtt_payload, qos=1, retain=False)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        message = f"MQTT publish failed with result code {result.rc}"
        update_deployment_attempt(conn, attempt_id, status="failed", rollout_id=command["rolloutId"], message=message)
        LOG.error("%s for %s on %s", message, device_id, topic)
        return

    update_deployment_attempt(
        conn,
        attempt_id,
        status="published",
        rollout_id=command["rolloutId"],
        message=f"published OTA command to {topic}",
    )
    LOG.info("Published OTA command for %s rollout=%s target=%s", device_id, command["rolloutId"], desired_version)


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
            if not message.payload:
                LOG.info("Ignoring empty MQTT message on %s", message.topic)
                return
            payload = json.loads(message.payload.decode("utf-8"))
            if message.topic.endswith("/telemetry"):
                validate_telemetry(payload)
                payload["location"] = mapped_location(
                    str(payload["deviceId"]),
                    payload.get("location"),
                    locations,
                )
                record_telemetry(conn, payload)
                maybe_trigger_deployment(client, conn, args, payload)
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
                maybe_trigger_deployment(client, conn, args, payload)
                LOG.info("Status %s %s", payload["deviceId"], payload["status"])
        except Exception:
            LOG.exception("Failed to process MQTT message on %s", message.topic)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls:
        client.tls_set(ca_certs=str(args.ca_cert) if args.ca_cert else None, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=60)
    temperature_interval = max(10, args.pi_temperature_interval_seconds)
    next_temperature_sample = 0.0
    try:
        while True:
            result = client.loop(timeout=1.0)
            if result != mqtt.MQTT_ERR_SUCCESS:
                LOG.warning("MQTT loop stopped with code %s; reconnecting", result)
                time.sleep(1)
                try:
                    client.reconnect()
                except OSError:
                    LOG.exception("MQTT reconnect failed")
                    time.sleep(4)
            now = time.monotonic()
            if now >= next_temperature_sample:
                next_temperature_sample = now + temperature_interval
                try:
                    temperature_f = read_pi_temperature_f()
                    record_system_metric(conn, "pi_cpu_temperature_f", temperature_f)
                    LOG.info("Pi CPU temperature %.1f F", temperature_f)
                except (OSError, ValueError):
                    LOG.exception("Failed to sample Pi CPU temperature")
    except KeyboardInterrupt:
        LOG.info("Collector stopped")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
