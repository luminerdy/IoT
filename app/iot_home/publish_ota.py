from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt

from iot_home.mqtt_schema import COMMAND_TOPIC


DEFAULT_FIRMWARE_BIN = Path("firmware/.pio/build/esp32dev/firmware.bin")
DEFAULT_FIRMWARE_DIR = Path("data/firmware")
DEFAULT_SIGNING_KEY = Path("data/keys/ota_signing_key.pem")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage and publish a local OTA update command.")
    parser.add_argument("device_id", help="Device ID, for example esp32-9c9c1fda3670.")
    parser.add_argument("version", help="Firmware version label to stage, for example 0.2.0-local.")
    parser.add_argument("--firmware-bin", type=Path, default=DEFAULT_FIRMWARE_BIN, help="Built firmware.bin path.")
    parser.add_argument("--firmware-dir", type=Path, default=DEFAULT_FIRMWARE_DIR, help="OTA firmware staging directory.")
    parser.add_argument("--base-url", default="http://piserver.local:8000", help="Base dashboard URL reachable by ESP32.")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host.")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--client-id", default="iot-pi-ota-publisher", help="MQTT client ID.")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username.")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password.")
    parser.add_argument("--tls", action="store_true", help="Use MQTT over TLS.")
    parser.add_argument("--ca-cert", type=Path, help="CA certificate for MQTT TLS.")
    parser.add_argument(
        "--signing-key",
        type=Path,
        default=DEFAULT_SIGNING_KEY,
        help="P-256 private key used to sign OTA firmware.",
    )
    parser.add_argument("--rollout-id", help="Rollout ID to include in the OTA command.")
    parser.add_argument("--stage-only", action="store_true", help="Stage firmware and manifest without publishing MQTT.")
    return parser.parse_args()


def validate_version(version: str) -> None:
    if not version or "/" in version or "\\" in version or version in {".", ".."}:
        raise SystemExit("version must be a simple path-safe label")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as firmware:
        for chunk in iter(lambda: firmware.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sign_firmware(path: Path, signing_key: Path) -> str:
    if not signing_key.is_file():
        raise SystemExit(f"OTA signing key not found: {signing_key}")

    with tempfile.NamedTemporaryFile() as signature_file:
        subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                str(signing_key),
                "-out",
                signature_file.name,
                str(path),
            ],
            check=True,
        )
        return Path(signature_file.name).read_bytes().hex()


def stage_firmware(args: argparse.Namespace) -> dict:
    validate_version(args.version)
    source = args.firmware_bin
    if not source.is_file():
        raise SystemExit(f"firmware binary not found: {source}")

    release_dir = args.firmware_dir / args.version
    release_dir.mkdir(parents=True, exist_ok=True)
    staged_bin = release_dir / "firmware.bin"
    shutil.copy2(source, staged_bin)

    size = staged_bin.stat().st_size
    sha256 = sha256_file(staged_bin)
    signature = sign_firmware(staged_bin, args.signing_key)
    rollout_id = args.rollout_id or f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{args.version}"
    firmware_url = f"{args.base_url.rstrip('/')}/firmware/{args.version}/firmware.bin"

    command = {
        "command": "ota_update",
        "rolloutId": rollout_id,
        "version": args.version,
        "url": firmware_url,
        "sha256": sha256,
        "signature": signature,
        "size": size,
    }
    manifest = {
        **command,
        "deviceId": args.device_id,
        "createdAt": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    (release_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return command


def publish_command(args: argparse.Namespace, command: dict) -> None:
    topic = COMMAND_TOPIC.format(device_id=args.device_id)
    payload = json.dumps(command, separators=(",", ":")).encode("utf-8")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls:
        client.tls_set(ca_certs=str(args.ca_cert) if args.ca_cert else None, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()
    result = client.publish(topic, payload, qos=1, retain=False)
    result.wait_for_publish(timeout=10)
    client.loop_stop()
    client.disconnect()

    if not result.is_published():
        raise SystemExit(f"publish to {topic} did not complete")
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise SystemExit(f"publish to {topic} failed with MQTT result code {result.rc}")
    print(f"published OTA command on {topic}: {payload.decode('utf-8')}")


def main() -> None:
    args = parse_args()
    command = stage_firmware(args)
    manifest_path = args.firmware_dir / args.version / "manifest.json"
    print(f"staged OTA manifest: {manifest_path}")
    if not args.stage_only:
        publish_command(args, command)


if __name__ == "__main__":
    main()
