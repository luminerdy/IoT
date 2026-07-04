from iot_home.db import (
    connect,
    init_db,
    latest_readings,
    reading_history,
    recent_deployment_attempt_exists,
    record_deployment_attempt,
    record_status,
    record_telemetry,
)


def test_record_telemetry_updates_latest_device_state(tmp_path):
    db_path = tmp_path / "iot.db"
    with connect(db_path) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "location": "Kitchen",
                "firmwareVersion": "0.1.3",
                "sensorType": "DHT22",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 72.4,
                "humidity": 45.2,
                "rssi": -55,
                "status": "OK",
                "seq": 7,
            },
        )

        rows = latest_readings(conn)

    assert len(rows) == 1
    assert rows[0]["device_id"] == "esp32-one"
    assert rows[0]["location"] == "Kitchen"
    assert rows[0]["online"] == 1
    assert rows[0]["temperature"] == 72.4
    assert rows[0]["humidity"] == 45.2


def test_record_telemetry_tracks_valid_last_ip(tmp_path):
    db_path = tmp_path / "iot.db"
    with connect(db_path) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 72.4,
                "humidity": 45.2,
                "localIp": "192.168.1.25",
            },
        )

        rows = latest_readings(conn)

    assert rows[0]["last_ip"] == "192.168.1.25"


def test_record_telemetry_dedupes_repeated_device_seq_datetime(tmp_path):
    db_path = tmp_path / "iot.db"
    payload = {
        "deviceId": "esp32-one",
        "location": "Kitchen",
        "datetime": "2026-06-30T12:00:00Z",
        "temperature": 72.4,
        "humidity": 45.2,
        "seq": 7,
    }

    with connect(db_path) as conn:
        init_db(conn)
        record_telemetry(conn, payload)
        record_telemetry(conn, {**payload, "temperature": 73.0, "humidity": 46.0})

        reading_count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        rows = latest_readings(conn)

    assert reading_count == 1
    assert rows[0]["temperature"] == 72.4


def test_record_telemetry_records_new_seq_for_same_device_datetime(tmp_path):
    db_path = tmp_path / "iot.db"
    payload = {
        "deviceId": "esp32-one",
        "datetime": "2026-06-30T12:00:00Z",
        "temperature": 72.4,
        "humidity": 45.2,
        "seq": 7,
    }

    with connect(db_path) as conn:
        init_db(conn)
        record_telemetry(conn, payload)
        record_telemetry(conn, {**payload, "seq": 8})

        reading_count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    assert reading_count == 2


def test_status_without_timestamp_preserves_last_seen(tmp_path):
    db_path = tmp_path / "iot.db"
    with connect(db_path) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 70,
                "humidity": 40,
            },
        )
        record_status(conn, {"deviceId": "esp32-one", "status": "offline"})

        row = latest_readings(conn)[0]

    assert row["online"] == 0
    assert row["last_seen"] == "2026-06-30T12:00:00Z"


def test_record_deployment_attempt_and_recent_check(tmp_path):
    db_path = tmp_path / "iot.db"
    with connect(db_path) as conn:
        init_db(conn)
        attempt_id = record_deployment_attempt(
            conn,
            device_id="esp32-one",
            from_version="0.1.3",
            to_version="0.1.4",
            observed_ip="192.168.1.25",
            status="detected",
        )

        row = conn.execute("SELECT * FROM deployment_attempts WHERE id = ?", (attempt_id,)).fetchone()
        recent = recent_deployment_attempt_exists(conn, "esp32-one", "0.1.4", 3600)

    assert row["device_id"] == "esp32-one"
    assert row["from_version"] == "0.1.3"
    assert row["to_version"] == "0.1.4"
    assert row["observed_ip"] == "192.168.1.25"
    assert row["status"] == "detected"
    assert recent is True


def test_reading_history_bounds_limit_and_hours(tmp_path):
    db_path = tmp_path / "iot.db"
    with connect(db_path) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 70,
                "humidity": 40,
            },
        )

        rows = reading_history(conn, hours=9999, limit=999999)

    assert len(rows) == 1
    assert rows[0]["device_id"] == "esp32-one"
