import argparse
import hashlib
import json
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest
from iot_home import publish_ota
from iot_home.publish_ota import (
    command_from_manifest,
    firmware_download_url,
    metadata_payload,
    replace_firmware_url_base,
)


def test_metadata_payload_is_canonical():
    payload = metadata_payload(
        sha256="a" * 64,
        build_number=2026070401,
        version="0.1.4-antirollback",
        size=826928,
    )

    assert payload == (
        b"iot-home-ota-v2\n" + b"a" * 64 + b"\n2026070401\n0.1.4-antirollback\n826928\n"
    )


def test_command_from_manifest_requires_anti_rollback_fields(tmp_path):
    release_dir = tmp_path / "firmware" / "0.1.4-antirollback"
    release_dir.mkdir(parents=True, exist_ok=True)
    (release_dir / "manifest.json").write_text(
        json.dumps(
            {
                "command": "ota_update",
                "rolloutId": "test-rollout",
                "version": "0.1.4-antirollback",
                "url": "http://old-host/firmware/0.1.4-antirollback/firmware.bin",
                "sha256": "a" * 64,
                "signature": "b" * 128,
                "size": 123,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="buildNumber, metadataSignature"):
        command_from_manifest(tmp_path / "firmware", "0.1.4-antirollback")


def test_command_from_manifest_includes_anti_rollback_fields(tmp_path):
    release_dir = tmp_path / "firmware" / "0.1.4-antirollback"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text(
        json.dumps(
            {
                "command": "ota_update",
                "rolloutId": "test-rollout",
                "version": "0.1.4-antirollback",
                "url": "http://old-host/firmware/0.1.4-antirollback/firmware.bin",
                "sha256": "a" * 64,
                "signature": "b" * 128,
                "size": 123,
                "buildNumber": 2026070401,
                "metadataSignature": "c" * 128,
            }
        ),
        encoding="utf-8",
    )

    command = command_from_manifest(
        tmp_path / "firmware",
        "0.1.4-antirollback",
        base_url="http://iot-pi.local:8000",
        download_key="test-key",
    )

    assert command["buildNumber"] == 2026070401
    assert command["metadataSignature"] == "c" * 128
    assert command["url"] == (
        "http://iot-pi.local:8000/firmware/0.1.4-antirollback/firmware.bin?key=test-key"
    )


def test_firmware_download_url_requires_and_encodes_key():
    assert firmware_download_url("http://iot-pi.local:8000/", "0.1.6-recovery", "a key/+?") == (
        "http://iot-pi.local:8000/firmware/0.1.6-recovery/firmware.bin?key=a%20key%2F%2B%3F"
    )
    with pytest.raises(ValueError, match="FIRMWARE_DOWNLOAD_KEY"):
        firmware_download_url("http://iot-pi.local:8000", "0.1.6-recovery", None)


def test_replace_firmware_url_base_preserves_capability_key():
    assert (
        replace_firmware_url_base(
            "http://old-host:8000/firmware/0.1.6-recovery/firmware.bin?key=test-key",
            "http://10.0.0.1:8000",
        )
        == "http://10.0.0.1:8000/firmware/0.1.6-recovery/firmware.bin?key=test-key"
    )

    with pytest.raises(ValueError, match="missing its firmware download capability key"):
        replace_firmware_url_base(
            "http://old-host:8000/firmware/0.1.6-recovery/firmware.bin",
            "http://10.0.0.1:8000",
        )


@pytest.mark.parametrize("version", ["", ".", "..", "folder/release", "folder\\release"])
def test_validate_version_rejects_unsafe_labels(version):
    with pytest.raises(SystemExit, match="path-safe"):
        publish_ota.validate_version(version)


def test_validate_version_accepts_simple_label():
    publish_ota.validate_version("0.1.6-recovery")


def test_sha256_file_hashes_complete_binary(tmp_path):
    binary = tmp_path / "firmware.bin"
    binary.write_bytes(b"firmware" * 200000)

    assert publish_ota.sha256_file(binary) == hashlib.sha256(binary.read_bytes()).hexdigest()


def test_signing_helpers_invoke_openssl_and_return_hex(monkeypatch, tmp_path):
    binary = tmp_path / "firmware.bin"
    key = tmp_path / "key.pem"
    binary.write_bytes(b"firmware")
    key.write_text("test key", encoding="utf-8")

    def fake_run(command, check):
        assert check is True
        Path(command[command.index("-out") + 1]).write_bytes(b"\x01\x02")

    monkeypatch.setattr(publish_ota.subprocess, "run", fake_run)

    assert publish_ota.sign_firmware(binary, key) == "0102"
    assert (
        publish_ota.sign_metadata(
            sha256="a" * 64,
            build_number=1,
            version="test",
            size=8,
            signing_key=key,
        )
        == "0102"
    )


def test_signing_helpers_require_key_and_valid_build_number(tmp_path):
    missing = tmp_path / "missing.pem"
    binary = tmp_path / "firmware.bin"
    binary.write_bytes(b"firmware")

    with pytest.raises(SystemExit, match="signing key not found"):
        publish_ota.sign_firmware(binary, missing)
    with pytest.raises(SystemExit, match="between 1"):
        publish_ota.sign_metadata(
            sha256="a" * 64,
            build_number=0,
            version="test",
            size=8,
            signing_key=missing,
        )
    key = tmp_path / "key.pem"
    key.write_text("key", encoding="utf-8")
    with pytest.raises(SystemExit, match="signing key not found"):
        publish_ota.sign_metadata(
            sha256="a" * 64,
            build_number=1,
            version="test",
            size=8,
            signing_key=missing,
        )


def _ota_args(tmp_path, **overrides):
    values = {
        "device_id": "esp32-test",
        "version": "0.2.0-test",
        "firmware_bin": tmp_path / "build" / "firmware.bin",
        "firmware_dir": tmp_path / "releases",
        "base_url": "http://hub.test:8000",
        "firmware_download_key": "download key",
        "broker": "broker.test",
        "port": 8883,
        "client_id": "ota-test",
        "username": "admin",
        "password": "secret",
        "tls": True,
        "ca_cert": tmp_path / "ca.pem",
        "signing_key": tmp_path / "key.pem",
        "rollout_id": "rollout-test",
        "build_number": 2026080701,
        "stage_only": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_stage_firmware_copies_binary_and_writes_manifest(monkeypatch, tmp_path):
    args = _ota_args(tmp_path)
    args.firmware_bin.parent.mkdir()
    args.firmware_bin.write_bytes(b"test firmware")
    monkeypatch.setattr(publish_ota, "sign_firmware", lambda path, key: "firmware-signature")
    monkeypatch.setattr(publish_ota, "sign_metadata", lambda **kwargs: "metadata-signature")

    command = publish_ota.stage_firmware(args)

    release_dir = args.firmware_dir / args.version
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    assert (release_dir / "firmware.bin").read_bytes() == b"test firmware"
    assert command["rolloutId"] == "rollout-test"
    assert command["signature"] == "firmware-signature"
    assert command["metadataSignature"] == "metadata-signature"
    assert command["url"].endswith("?key=download%20key")
    assert manifest["deviceId"] == "esp32-test"
    assert manifest["createdAt"].endswith("Z")


def test_stage_firmware_requires_existing_binary(tmp_path):
    with pytest.raises(SystemExit, match="firmware binary not found"):
        publish_ota.stage_firmware(_ota_args(tmp_path))


def _manifest(tmp_path, **overrides):
    version = "0.2.0-test"
    release_dir = tmp_path / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "command": "ota_update",
        "rolloutId": "rollout-test",
        "version": version,
        "url": f"http://old.test/firmware/{version}/firmware.bin",
        "sha256": "a" * 64,
        "signature": "b" * 128,
        "size": 123,
        "buildNumber": 7,
        "metadataSignature": "c" * 128,
    }
    payload.update(overrides)
    (release_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path / "releases", version


def test_command_from_manifest_validates_file_command_and_version(tmp_path):
    with pytest.raises(FileNotFoundError, match="manifest not found"):
        command_from_manifest(tmp_path, "missing")

    firmware_dir, version = _manifest(tmp_path, command="restart")
    with pytest.raises(ValueError, match="unsupported OTA command"):
        command_from_manifest(firmware_dir, version)

    (firmware_dir / version / "manifest.json").unlink()
    firmware_dir, version = _manifest(tmp_path, version="wrong")
    with pytest.raises(ValueError, match="does not match"):
        command_from_manifest(firmware_dir, version)


def test_command_from_manifest_reconstructs_url_for_legacy_manifest(tmp_path):
    firmware_dir, version = _manifest(tmp_path)

    command = command_from_manifest(
        firmware_dir,
        version,
        base_url="http://hub.test:8000",
        download_key="new-key",
    )

    assert command["url"] == f"http://hub.test:8000/firmware/{version}/firmware.bin?key=new-key"
    assert command_from_manifest(firmware_dir, version)["url"].startswith("http://old.test")


class _PublishResult:
    def __init__(self, *, published=True, result_code=mqtt.MQTT_ERR_SUCCESS):
        self.published = published
        self.rc = result_code

    def wait_for_publish(self, timeout):
        self.timeout = timeout

    def is_published(self):
        return self.published


class _MqttClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def username_pw_set(self, username, password):
        self.calls.append(("credentials", username, password))

    def tls_set(self, **kwargs):
        self.calls.append(("tls", kwargs))

    def connect(self, host, port, keepalive):
        self.calls.append(("connect", host, port, keepalive))

    def loop_start(self):
        self.calls.append(("loop_start",))

    def publish(self, topic, payload, qos, retain):
        self.calls.append(("publish", topic, payload, qos, retain))
        return self.result

    def loop_stop(self):
        self.calls.append(("loop_stop",))

    def disconnect(self):
        self.calls.append(("disconnect",))


def test_publish_command_sends_non_retained_qos_one(monkeypatch, tmp_path, capsys):
    result = _PublishResult()
    client = _MqttClient(result)
    monkeypatch.setattr(publish_ota.mqtt, "Client", lambda *args, **kwargs: client)

    publish_ota.publish_command(_ota_args(tmp_path), {"rolloutId": "rollout-test"})

    publish = next(call for call in client.calls if call[0] == "publish")
    assert publish[1] == "home/sensors/esp32-test/command"
    assert publish[3:] == (1, False)
    assert result.timeout == 10
    assert "rollout-test" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (_PublishResult(published=False), "did not complete"),
        (_PublishResult(result_code=mqtt.MQTT_ERR_NO_CONN), "failed with MQTT result code"),
    ],
)
def test_publish_command_rejects_incomplete_publish(monkeypatch, tmp_path, result, message):
    monkeypatch.setattr(publish_ota.mqtt, "Client", lambda *args, **kwargs: _MqttClient(result))

    with pytest.raises(SystemExit, match=message):
        publish_ota.publish_command(_ota_args(tmp_path), {"rolloutId": "rollout-test"})


def test_parse_args_reads_required_ota_options(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["publish-ota", "esp32-test", "0.2.0", "--build-number", "7", "--stage-only"],
    )

    args = publish_ota.parse_args()

    assert args.device_id == "esp32-test"
    assert args.version == "0.2.0"
    assert args.build_number == 7
    assert args.stage_only is True


def test_main_stages_and_optionally_publishes(monkeypatch, tmp_path, capsys):
    staged = {"rolloutId": "rollout-test"}
    published = []
    args = _ota_args(tmp_path)
    monkeypatch.setattr(publish_ota, "parse_args", lambda: args)
    monkeypatch.setattr(publish_ota, "stage_firmware", lambda actual: staged)
    monkeypatch.setattr(
        publish_ota, "publish_command", lambda actual, command: published.append(command)
    )

    publish_ota.main()

    assert published == [staged]
    assert "staged OTA manifest" in capsys.readouterr().out

    args.stage_only = True
    published.clear()
    publish_ota.main()
    assert published == []
