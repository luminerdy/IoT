from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from iot_home import provision_mqtt

CA_CERT = """-----BEGIN CERTIFICATE-----
dGVzdC1jZXJ0aWZpY2F0ZQ==
-----END CERTIFICATE-----
"""
DEVICE_ID = "esp32-" + "001122" + "aabbcc"
TEST_PASSWORD = "x" * 16


class FakeChannel:
    def __init__(self, outcomes: list[bytes | Exception]):
        self.outcomes = outcomes
        self.writes: list[bytes] = []

    def write(self, payload: bytes) -> None:
        self.writes.append(payload)

    def wait_for(self, markers: tuple[bytes, ...], timeout: float) -> bytes:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert outcome in markers
        return outcome


def test_profile_json_is_typed_bounded_and_secret_is_not_in_repr() -> None:
    profile = provision_mqtt.build_profile(
        device_id=DEVICE_ID,
        connect_host="10.10.10.123",
        tls_hostname="broker.test",
        port=8883,
        password=TEST_PASSWORD,
        ca_cert=CA_CERT,
    )
    payload = json.loads(profile.as_json())
    assert TEST_PASSWORD not in repr(profile)
    assert payload == {
        "schemaVersion": 2,
        "mqttConnectHost": "10.10.10.123",
        "mqttTlsHostname": "broker.test",
        "mqttPort": 8883,
        "mqttUsername": DEVICE_ID,
        "mqttPassword": TEST_PASSWORD,
        "mqttUseTls": True,
        "mqttCaCert": CA_CERT,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("device_id", "esp32-wrong", "device ID"),
        ("connect_host", "https://broker.test", "connect host"),
        ("tls_hostname", "192.0.2.1", "TLS hostname"),
        ("port", 0, "MQTT port"),
        ("password", "short", "MQTT password"),
        ("ca_cert", "not a certificate", "CA certificate"),
    ],
)
def test_profile_validation_rejects_unsafe_values(field: str, value, message: str) -> None:
    values = {
        "device_id": DEVICE_ID,
        "connect_host": "10.10.10.123",
        "tls_hostname": "broker.test",
        "port": 8883,
        "password": TEST_PASSWORD,
        "ca_cert": CA_CERT,
    }
    values[field] = value
    with pytest.raises(ValueError, match=message):
        provision_mqtt.build_profile(**values)


def test_password_file_requires_private_permissions(tmp_path: Path) -> None:
    password_file = tmp_path / "password"
    password_file.write_text(f"{TEST_PASSWORD}\n", encoding="utf-8")
    os.chmod(password_file, 0o644)
    with pytest.raises(ValueError, match="0600"):
        provision_mqtt.read_password_file(password_file)
    os.chmod(password_file, 0o600)
    assert provision_mqtt.read_password_file(password_file) == TEST_PASSWORD


def test_usb_serial_writes_are_paced_in_bounded_chunks(monkeypatch) -> None:
    channel = provision_mqtt.UsbSerialChannel(Path("/dev/ttyUSB-test"))
    channel.fd = 123
    writes: list[bytes] = []
    drains: list[int] = []
    pauses: list[float] = []

    def fake_write(fd: int, payload: memoryview) -> int:
        assert fd == 123
        writes.append(bytes(payload))
        return len(payload)

    monkeypatch.setattr(os, "write", fake_write)
    monkeypatch.setattr(provision_mqtt.termios, "tcdrain", drains.append)
    monkeypatch.setattr(provision_mqtt.time, "sleep", pauses.append)

    channel.write(b"x" * 600)

    assert [len(chunk) for chunk in writes] == [64] * 9 + [24]
    assert drains == [123] * 10
    assert pauses == [0.02] * 9


def test_ca_certificate_rejects_invalid_base64_inside_valid_framing() -> None:
    invalid = """-----BEGIN CERTIFICATE-----
!!!!
-----END CERTIFICATE-----
"""
    with pytest.raises(ValueError, match="PEM is invalid"):
        provision_mqtt.normalize_ca_certificate(invalid)


def test_provision_waits_for_ready_and_sends_one_secret_bearing_command() -> None:
    profile = provision_mqtt.build_profile(
        device_id=DEVICE_ID,
        connect_host="10.10.10.123",
        tls_hostname="broker.test",
        port=8883,
        password=TEST_PASSWORD,
        ca_cert=CA_CERT,
    )
    channel = FakeChannel(
        [TimeoutError(), provision_mqtt.STATUS_MARKER, provision_mqtt.APPLIED_MARKER]
    )
    provision_mqtt.provision(channel, profile, timeout=3)
    assert channel.writes[:2] == [provision_mqtt.STATUS_COMMAND, provision_mqtt.STATUS_COMMAND]
    assert channel.writes[2].startswith(provision_mqtt.PROVISION_PREFIX)
    assert channel.writes[2].endswith(b"\n")


def test_rejection_and_clear_failure_are_reported_without_response_body() -> None:
    profile = provision_mqtt.build_profile(
        device_id=DEVICE_ID,
        connect_host="10.10.10.123",
        tls_hostname="broker.test",
        port=8883,
        password=TEST_PASSWORD,
        ca_cert=CA_CERT,
    )
    rejected = FakeChannel([provision_mqtt.STATUS_MARKER, provision_mqtt.REJECTED_MARKER])
    with pytest.raises(RuntimeError, match="rejected"):
        provision_mqtt.provision(rejected, profile, timeout=1)

    failed_clear = FakeChannel([provision_mqtt.STATUS_MARKER, provision_mqtt.CLEAR_FAILED_MARKER])
    with pytest.raises(RuntimeError, match="could not clear"):
        provision_mqtt.clear(failed_clear, timeout=1)
