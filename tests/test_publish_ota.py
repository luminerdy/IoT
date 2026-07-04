import json

import pytest

from iot_home.publish_ota import command_from_manifest, metadata_payload


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
    )

    assert command["buildNumber"] == 2026070401
    assert command["metadataSignature"] == "c" * 128
    assert command["url"] == "http://iot-pi.local:8000/firmware/0.1.4-antirollback/firmware.bin"
