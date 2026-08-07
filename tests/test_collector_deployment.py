import argparse
import json

import paho.mqtt.client as mqtt

from iot_home.collector import maybe_trigger_deployment, read_pi_temperature_f
from iot_home.db import connect, init_db


def test_read_pi_temperature_f(tmp_path):
    thermal_file = tmp_path / "temp"
    thermal_file.write_text("53800\n", encoding="utf-8")

    assert read_pi_temperature_f(thermal_file) == 128.8


class FakePublishResult:
    rc = mqtt.MQTT_ERR_SUCCESS


class FakeMqttClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return FakePublishResult()


def args_for(tmp_path, *, auto_ota=False):
    return argparse.Namespace(
        desired_firmware_version="0.1.4",
        auto_ota=auto_ota,
        firmware_dir=tmp_path / "firmware",
        base_url="http://iot-pi.local:8000",
        firmware_download_key="test-key",
        ota_cooldown_seconds=3600,
    )


def write_manifest(tmp_path):
    release_dir = tmp_path / "firmware" / "0.1.4"
    release_dir.mkdir(parents=True)
    manifest = {
        "command": "ota_update",
        "rolloutId": "test-rollout",
        "version": "0.1.4",
        "url": "http://old-host/firmware/0.1.4/firmware.bin",
        "sha256": "a" * 64,
        "signature": "b" * 128,
        "size": 123,
        "buildNumber": 2026070401,
        "metadataSignature": "c" * 128,
    }
    (release_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_mismatch_records_attempt_without_auto_publish(tmp_path):
    client = FakeMqttClient()
    with connect(tmp_path / "iot.db") as conn:
        init_db(conn)
        maybe_trigger_deployment(
            client,
            conn,
            args_for(tmp_path),
            {
                "deviceId": "esp32-one",
                "firmwareVersion": "0.1.3",
                "localIp": "192.168.1.25",
            },
        )
        row = conn.execute("SELECT * FROM deployment_attempts").fetchone()

    assert row["device_id"] == "esp32-one"
    assert row["from_version"] == "0.1.3"
    assert row["to_version"] == "0.1.4"
    assert row["observed_ip"] == "192.168.1.25"
    assert row["status"] == "detected"
    assert client.published == []


def test_mismatch_auto_publishes_staged_ota_command(tmp_path):
    write_manifest(tmp_path)
    client = FakeMqttClient()
    with connect(tmp_path / "iot.db") as conn:
        init_db(conn)
        maybe_trigger_deployment(
            client,
            conn,
            args_for(tmp_path, auto_ota=True),
            {"deviceId": "esp32-one", "firmwareVersion": "0.1.3"},
        )
        row = conn.execute("SELECT * FROM deployment_attempts").fetchone()

    assert row["status"] == "published"
    assert row["rollout_id"] == "test-rollout"
    assert len(client.published) == 1
    topic, payload, qos, retain = client.published[0]
    command = json.loads(payload.decode("utf-8"))
    assert topic == "home/sensors/esp32-one/command"
    assert command["url"] == "http://iot-pi.local:8000/firmware/0.1.4/firmware.bin?key=test-key"
    assert qos == 1
    assert retain is False


def test_matching_version_does_not_record_or_publish(tmp_path):
    client = FakeMqttClient()
    with connect(tmp_path / "iot.db") as conn:
        init_db(conn)
        maybe_trigger_deployment(
            client,
            conn,
            args_for(tmp_path, auto_ota=True),
            {"deviceId": "esp32-one", "firmwareVersion": "0.1.4"},
        )
        attempt_count = conn.execute("SELECT COUNT(*) FROM deployment_attempts").fetchone()[0]

    assert attempt_count == 0
    assert client.published == []
