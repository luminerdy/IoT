import json

import pytest

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
        b"iot-home-ota-v2\n"
        + b"a" * 64
        + b"\n2026070401\n0.1.4-antirollback\n826928\n"
    )


def test_command_from_manifest_requires_anti_rollback_fields(tmp_path):
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
    assert replace_firmware_url_base(
        "http://old-host:8000/firmware/0.1.6-recovery/firmware.bin?key=test-key",
        "http://10.0.0.1:8000",
    ) == "http://10.0.0.1:8000/firmware/0.1.6-recovery/firmware.bin?key=test-key"

    with pytest.raises(ValueError, match="missing its firmware download capability key"):
        replace_firmware_url_base(
            "http://old-host:8000/firmware/0.1.6-recovery/firmware.bin",
            "http://10.0.0.1:8000",
        )
