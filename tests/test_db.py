from iot_home.db import connect, init_db, latest_readings, reading_history, record_status, record_telemetry


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
