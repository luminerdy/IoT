import argparse
from contextlib import closing

from iot_home.collector import maybe_record_deployment, read_pi_temperature_f
from iot_home.db import connect, init_db


def test_read_pi_temperature_f(tmp_path):
    thermal_file = tmp_path / "temp"
    thermal_file.write_text("53800\n", encoding="utf-8")

    assert read_pi_temperature_f(thermal_file) == 128.8


def args_for():
    return argparse.Namespace(
        desired_firmware_version="0.1.4",
        ota_cooldown_seconds=3600,
    )


def test_mismatch_records_attempt_for_operator_action(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        init_db(conn)
        maybe_record_deployment(
            conn,
            args_for(),
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


def test_matching_version_does_not_record(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        init_db(conn)
        maybe_record_deployment(
            conn,
            args_for(),
            {"deviceId": "esp32-one", "firmwareVersion": "0.1.4"},
        )
        attempt_count = conn.execute("SELECT COUNT(*) FROM deployment_attempts").fetchone()[0]

    assert attempt_count == 0


def test_missing_desired_or_reported_version_does_not_record(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        init_db(conn)
        no_desired = args_for()
        no_desired.desired_firmware_version = None
        maybe_record_deployment(conn, no_desired, {"deviceId": "esp32-one"})
        maybe_record_deployment(conn, args_for(), {"deviceId": "esp32-one"})
        attempt_count = conn.execute("SELECT COUNT(*) FROM deployment_attempts").fetchone()[0]

    assert attempt_count == 0


def test_recent_attempt_suppresses_duplicate_deployment(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        init_db(conn)
        payload = {"deviceId": "esp32-one", "firmwareVersion": "0.1.3"}
        maybe_record_deployment(conn, args_for(), payload)
        maybe_record_deployment(conn, args_for(), payload)
        attempt_count = conn.execute("SELECT COUNT(*) FROM deployment_attempts").fetchone()[0]

    assert attempt_count == 1
