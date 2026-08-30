from contextlib import closing

from iot_home.db import (
    connect,
    init_db,
    latest_monitoring_events,
    latest_readings,
    latest_system_metric,
    reading_history,
    recent_deployment_attempt_exists,
    record_deployment_attempt,
    record_monitoring_event,
    record_status,
    record_system_metric,
    record_telemetry,
    system_metric_history,
)


def test_record_and_read_latest_system_metric(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_system_metric(conn, "pi_cpu_temperature_f", 121.5)
        record_system_metric(conn, "pi_cpu_temperature_f", 123.1)
        row = latest_system_metric(conn, "pi_cpu_temperature_f")

    assert row is not None
    assert row["value"] == 123.1


def test_system_metric_history_bounds_limit_and_hours(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_system_metric(conn, "internet_outdoor_temperature_f", 91.4)
        record_system_metric(conn, "internet_outdoor_temperature_f", 92.2)

        rows = system_metric_history(conn, "internet_outdoor_temperature_f", hours=9999, limit=1)

    assert len(rows) == 1
    assert rows[0]["value"] == 92.2


def test_record_and_read_latest_monitoring_events(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_monitoring_event(
            conn,
            source="hub",
            event_type="post_reboot_check",
            severity="info",
            status="ok",
            message="post-reboot verification passed",
            details={"checks": [{"name": "services", "ok": True}]},
            created_at="2026-08-09 12:00:00",
        )
        record_monitoring_event(
            conn,
            source="pi-watchdog",
            event_type="watchdog_relay",
            severity="critical",
            status="recovery",
            message="Target power restored after 15s",
            created_at="2026-08-09 12:05:00",
        )

        all_events = latest_monitoring_events(conn)
        relay_events = latest_monitoring_events(conn, event_type="watchdog_relay")

    assert [row["event_type"] for row in all_events] == [
        "watchdog_relay",
        "post_reboot_check",
    ]
    assert relay_events[0]["message"] == "Target power restored after 15s"
    assert '"services"' in all_events[1]["details_json"]


def test_record_telemetry_updates_latest_device_state(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
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
                "numReadErrors": 2,
                "numFilteredReadings": 1,
            },
        )

        rows = latest_readings(conn)

    assert len(rows) == 1
    assert rows[0]["device_id"] == "esp32-one"
    assert rows[0]["location"] == "Kitchen"
    assert rows[0]["online"] == 1
    assert rows[0]["temperature"] == 72.4
    assert rows[0]["humidity"] == 45.2
    assert rows[0]["recent_seq_resets"] == 0
    assert rows[0]["num_read_errors"] == 2
    assert rows[0]["num_filtered_readings"] == 1
    assert rows[0]["read_error_delta"] == 2
    assert rows[0]["filtered_reading_delta"] == 1


def test_latest_readings_reports_sensor_counter_deltas(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        for index, counters in enumerate(((2, 1), (5, 1), (1, 0)), start=1):
            record_telemetry(
                conn,
                {
                    "deviceId": "esp32-one",
                    "location": "Kitchen",
                    "datetime": f"2026-06-30T12:00:0{index}Z",
                    "temperature": 72.4,
                    "humidity": 45.2,
                    "seq": index,
                    "numReadErrors": counters[0],
                    "numFilteredReadings": counters[1],
                },
            )

        rows = latest_readings(conn)

    assert rows[0]["num_read_errors"] == 1
    assert rows[0]["num_filtered_readings"] == 0
    assert rows[0]["read_error_delta"] == 1
    assert rows[0]["filtered_reading_delta"] == 0


def test_latest_readings_counts_recent_sequence_resets(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        for index, seq in enumerate((1, 8, 1), start=1):
            record_telemetry(
                conn,
                {
                    "deviceId": "esp32-one",
                    "location": "Kitchen",
                    "datetime": f"2026-06-30T12:00:0{index}Z",
                    "temperature": 72.4,
                    "humidity": 45.2,
                    "seq": seq,
                },
            )

        rows = latest_readings(conn)

    assert rows[0]["recent_seq_resets"] == 2


def test_record_telemetry_tracks_valid_last_ip(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 72.4,
                "humidity": 45.2,
                "localIp": "192.168.1.25",
                "seq": 1,
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

    with closing(connect(db_path)) as conn:
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

    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_telemetry(conn, payload)
        record_telemetry(conn, {**payload, "seq": 8})

        reading_count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    assert reading_count == 2


def test_status_without_timestamp_preserves_last_seen(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 70,
                "humidity": 40,
                "seq": 1,
            },
        )
        record_status(conn, {"deviceId": "esp32-one", "status": "offline"})

        row = latest_readings(conn)[0]

    assert row["online"] == 0
    assert row["last_seen"] == "2026-06-30T12:00:00Z"


def test_record_deployment_attempt_and_recent_check(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        attempt_id = record_deployment_attempt(
            conn,
            device_id="esp32-one",
            from_version="0.1.3",
            to_version="0.1.4",
            observed_ip="192.168.1.25",
            status="detected",
        )

        row = conn.execute(
            "SELECT * FROM deployment_attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        recent = recent_deployment_attempt_exists(conn, "esp32-one", "0.1.4", 3600)

    assert row["device_id"] == "esp32-one"
    assert row["from_version"] == "0.1.3"
    assert row["to_version"] == "0.1.4"
    assert row["observed_ip"] == "192.168.1.25"
    assert row["status"] == "detected"
    assert recent is True


def test_reading_history_bounds_limit_and_hours(tmp_path):
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-one",
                "datetime": "2026-06-30T12:00:00Z",
                "temperature": 70,
                "humidity": 40,
                "seq": 1,
            },
        )

        rows = reading_history(conn, hours=9999, limit=999999)

    assert len(rows) == 1
    assert rows[0]["device_id"] == "esp32-one"
