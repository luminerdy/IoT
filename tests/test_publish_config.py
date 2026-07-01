from argparse import Namespace

import pytest

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
    assert config_payload(args(defaults=True)) == b'{"reportIntervalSeconds":600,"changeThresholdF":1.0}'


def test_config_payload_clear():
    assert config_payload(args(clear=True)) == b""


def test_config_payload_custom_values():
    assert config_payload(args(report_interval=120, change_threshold=1.25)) == (
        b'{"reportIntervalSeconds":120,"changeThresholdF":1.2}'
    )


def test_config_payload_requires_one_action():
    with pytest.raises(SystemExit, match="exactly one"):
        config_payload(args(clear=True, defaults=True))
