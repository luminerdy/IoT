import argparse
import json
from contextlib import closing
from types import SimpleNamespace

import paho.mqtt.client as mqtt
import pytest
from iot_home import collector
from iot_home.db import connect


def _collector_args(tmp_path):
    return argparse.Namespace(
        broker="broker.test",
        port=8883,
        db=tmp_path / "iot.db",
        client_id="collector-test",
        username="collector",
        password="secret",
        tls=True,
        ca_cert=None,
        locations=tmp_path / "locations.json",
        retired_devices=tmp_path / "retired_devices.json",
        desired_firmware_version=None,
        ota_cooldown_seconds=3600,
        pi_temperature_interval_seconds=1,
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "missing telemetry fields"),
        (
            {
                "deviceId": "esp32-test",
                "datetime": "now",
                "temperature": 186,
                "humidity": 50,
                "seq": 1,
            },
            "temperature out of range",
        ),
        (
            {
                "deviceId": "esp32-test",
                "datetime": "now",
                "temperature": 70,
                "humidity": -1,
                "seq": 1,
            },
            "humidity out of range",
        ),
        (
            {
                "deviceId": "esp32-test",
                "datetime": "now",
                "temperature": "invalid",
                "humidity": 50,
                "seq": 1,
            },
            "could not convert",
        ),
        (
            {
                "deviceId": "esp32-test",
                "datetime": "now",
                "temperature": 70,
                "humidity": 50,
            },
            "missing telemetry fields: seq",
        ),
        (
            {
                "deviceId": "esp32-test",
                "datetime": "now",
                "temperature": 70,
                "humidity": 50,
                "seq": "1",
            },
            "invalid telemetry seq",
        ),
    ],
)
def test_validate_telemetry_rejects_invalid_payloads(payload, message):
    with pytest.raises(ValueError, match=message):
        collector.validate_telemetry(payload)


def test_validate_telemetry_accepts_range_edges():
    collector.validate_telemetry(
        {
            "deviceId": "esp32-test",
            "datetime": "now",
            "temperature": -40,
            "humidity": 100,
            "seq": 1,
        }
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [({}, "missing status field"), ({"deviceId": "esp32-test", "status": "sleeping"}, "invalid")],
)
def test_validate_status_rejects_invalid_payloads(payload, message):
    with pytest.raises(ValueError, match=message):
        collector.validate_status(payload)


def test_validate_status_accepts_online_and_offline():
    collector.validate_status({"deviceId": "esp32-test", "status": "online"})
    collector.validate_status({"deviceId": "esp32-test", "status": "offline"})


def test_parse_args_supports_service_options(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "sys.argv",
        [
            "collector",
            "--broker",
            "broker.test",
            "--port",
            "8883",
            "--db",
            str(tmp_path / "iot.db"),
            "--tls",
            "--desired-firmware-version",
            "1.2.3",
        ],
    )

    args = collector.parse_args()

    assert args.broker == "broker.test"
    assert args.port == 8883
    assert args.tls is True
    assert args.desired_firmware_version == "1.2.3"

    monkeypatch.setattr("sys.argv", ["collector", "--auto-ota"])
    with pytest.raises(SystemExit):
        collector.parse_args()


class _ServiceClient:
    def __init__(self):
        self.on_connect = None
        self.on_message = None
        self.subscriptions = []
        self.loop_calls = 0
        self.reconnect_calls = 0
        self.disconnected = False

    def username_pw_set(self, username, password):
        self.credentials = (username, password)

    def tls_set(self, **kwargs):
        self.tls_options = kwargs

    def connect(self, host, port, keepalive):
        self.connection = (host, port, keepalive)
        self.on_connect(self, None, None, 1)
        self.on_connect(self, None, None, 0)

    def subscribe(self, subscriptions):
        self.subscriptions.extend(subscriptions)

    def loop(self, timeout):
        self.loop_calls += 1
        if self.loop_calls == 1:
            messages = [
                ("home/sensors/esp32-test/telemetry", b""),
                (
                    "home/sensors/esp32-test/telemetry",
                    json.dumps(
                        {
                            "deviceId": "esp32-test",
                            "datetime": "2026-08-07T12:00:00Z",
                            "temperature": 72.5,
                            "humidity": 41.0,
                            "seq": 1,
                            "firmwareVersion": "1.0.0",
                        }
                    ).encode(),
                ),
                (
                    "home/sensors/esp32-test/status",
                    b'{"deviceId":"esp32-test","status":"online"}',
                ),
                ("home/sensors/esp32-test/telemetry", b"not-json"),
            ]
            for topic, payload in messages:
                self.on_message(self, None, SimpleNamespace(topic=topic, payload=payload))
            return mqtt.MQTT_ERR_NO_CONN
        if self.loop_calls == 2:
            return mqtt.MQTT_ERR_SUCCESS
        raise KeyboardInterrupt

    def reconnect(self):
        self.reconnect_calls += 1
        raise OSError("broker unavailable")

    def disconnect(self):
        self.disconnected = True


def test_main_processes_messages_reconnects_and_samples_temperature(monkeypatch, tmp_path):
    args = _collector_args(tmp_path)
    args.locations.write_text('{"esp32-test":"Test Room"}', encoding="utf-8")
    client = _ServiceClient()
    temperatures = iter([111.2, ValueError("bad thermal reading")])

    monkeypatch.setattr(collector, "parse_args", lambda: args)
    monkeypatch.setattr(collector.mqtt, "Client", lambda *args, **kwargs: client)
    monkeypatch.setattr(collector.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(collector.time, "monotonic", iter([0.0, 11.0]).__next__)

    def read_temperature():
        value = next(temperatures)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(collector, "read_pi_temperature_f", read_temperature)

    collector.main()

    assert client.credentials == ("collector", "secret")
    assert client.connection == ("broker.test", 8883, 60)
    assert len(client.subscriptions) == 2
    assert client.reconnect_calls == 1
    assert client.disconnected is True
    with closing(connect(args.db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM system_metrics").fetchone()[0] == 1
        device = conn.execute("SELECT location, online FROM devices").fetchone()
    assert tuple(device) == ("Test Room", 1)


def test_main_ignores_retired_devices(monkeypatch, tmp_path):
    args = _collector_args(tmp_path)
    args.retired_devices.write_text('["esp32-test"]', encoding="utf-8")
    client = _ServiceClient()

    monkeypatch.setattr(collector, "parse_args", lambda: args)
    monkeypatch.setattr(collector.mqtt, "Client", lambda *args, **kwargs: client)
    monkeypatch.setattr(collector.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(collector.time, "monotonic", iter([0.0, 11.0]).__next__)
    monkeypatch.setattr(collector, "read_pi_temperature_f", lambda: 111.2)

    collector.main()

    with closing(connect(args.db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 0
