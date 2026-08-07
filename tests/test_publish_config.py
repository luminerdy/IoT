from argparse import Namespace

import paho.mqtt.client as mqtt
import pytest
from iot_home import publish_config
from iot_home.publish_config import config_payload


def args(**overrides):
    defaults = {
        "clear": False,
        "defaults": False,
        "report_interval": None,
        "change_threshold": None,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def test_config_payload_defaults():
    assert (
        config_payload(args(defaults=True))
        == b'{"reportIntervalSeconds":600,"changeThresholdF":1.0}'
    )


def test_config_payload_clear():
    assert config_payload(args(clear=True)) == b""


def test_config_payload_custom_values():
    assert config_payload(args(report_interval=120, change_threshold=1.25)) == (
        b'{"reportIntervalSeconds":120,"changeThresholdF":1.2}'
    )


def test_config_payload_requires_one_action():
    with pytest.raises(SystemExit, match="exactly one"):
        config_payload(args(clear=True, defaults=True))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({}, "exactly one"),
        ({"report_interval": 9}, "report-interval"),
        ({"report_interval": 3601}, "report-interval"),
        ({"change_threshold": 0.09}, "change-threshold"),
        ({"change_threshold": 10.1}, "change-threshold"),
    ],
)
def test_config_payload_rejects_missing_or_out_of_range_values(overrides, message):
    with pytest.raises(SystemExit, match=message):
        config_payload(args(**overrides))


def test_parse_args_reads_config_options(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "publish-config",
            "esp32-test",
            "--broker",
            "broker.test",
            "--port",
            "8883",
            "--report-interval",
            "120",
            "--tls",
        ],
    )

    parsed = publish_config.parse_args()

    assert parsed.device_id == "esp32-test"
    assert parsed.report_interval == 120
    assert parsed.port == 8883
    assert parsed.tls is True


class _PublishResult:
    def __init__(self, *, published=True, result_code=mqtt.MQTT_ERR_SUCCESS):
        self.published = published
        self.rc = result_code
        self.wait_timeout = None

    def wait_for_publish(self, timeout):
        self.wait_timeout = timeout

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


def _main_args(tmp_path, **overrides):
    values = {
        "device_id": "esp32-test",
        "broker": "broker.test",
        "port": 8883,
        "client_id": "config-test",
        "username": "admin",
        "password": "secret",
        "tls": True,
        "ca_cert": tmp_path / "ca.pem",
        "report_interval": None,
        "change_threshold": None,
        "clear": False,
        "defaults": True,
    }
    values.update(overrides)
    return Namespace(**values)


def test_main_publishes_retained_config(monkeypatch, tmp_path, capsys):
    result = _PublishResult()
    client = _MqttClient(result)
    monkeypatch.setattr(publish_config, "parse_args", lambda: _main_args(tmp_path))
    monkeypatch.setattr(publish_config.mqtt, "Client", lambda *args, **kwargs: client)

    publish_config.main()

    publish = next(call for call in client.calls if call[0] == "publish")
    assert publish[1] == "home/sensors/esp32-test/config"
    assert publish[3:] == (1, True)
    assert result.wait_timeout == 10
    assert "published retained config" in capsys.readouterr().out


def test_main_reports_retained_config_delete(monkeypatch, tmp_path, capsys):
    client = _MqttClient(_PublishResult())
    monkeypatch.setattr(
        publish_config,
        "parse_args",
        lambda: _main_args(
            tmp_path,
            clear=True,
            defaults=False,
            username=None,
            tls=False,
            ca_cert=None,
        ),
    )
    monkeypatch.setattr(publish_config.mqtt, "Client", lambda *args, **kwargs: client)

    publish_config.main()

    assert "deleted retained config" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (_PublishResult(published=False), "did not complete"),
        (_PublishResult(result_code=mqtt.MQTT_ERR_NO_CONN), "failed with MQTT result code"),
    ],
)
def test_main_rejects_incomplete_publish(monkeypatch, tmp_path, result, message):
    client = _MqttClient(result)
    monkeypatch.setattr(publish_config, "parse_args", lambda: _main_args(tmp_path))
    monkeypatch.setattr(publish_config.mqtt, "Client", lambda *args, **kwargs: client)

    with pytest.raises(SystemExit, match=message):
        publish_config.main()
