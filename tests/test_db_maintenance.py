import gzip
import os
import sqlite3
from contextlib import closing

from iot_home.db import connect, init_db
from iot_home.db_maintenance import main, maintain_database


def _database_with_history(path):
    with closing(connect(path)) as conn:
        init_db(conn)
        conn.execute(
            "INSERT INTO readings (device_id, temperature, humidity, datetime) VALUES (?, ?, ?, ?)",
            ("esp32-one", 72.0, 40.0, "2026-08-07T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO deployment_attempts (device_id, to_version, status) VALUES (?, ?, ?)",
            ("esp32-one", "0.1.6", "detected"),
        )
        conn.execute(
            "INSERT INTO system_metrics (metric, value) VALUES (?, ?)",
            ("pi_cpu_temperature_f", 120.0),
        )
        conn.commit()


def _compressed_backup(db_path, backup_dir):
    backup_dir.mkdir()
    backup_path = backup_dir / "iot-20260807T070501Z.sqlite.gz"
    with db_path.open("rb") as source, gzip.open(backup_path, "wb") as target:
        target.write(source.read())
    return backup_path


def test_maintenance_preserves_rows_and_checks_backup(tmp_path):
    db_path = tmp_path / "iot.db"
    backup_dir = tmp_path / "backups"
    _database_with_history(db_path)
    backup_path = _compressed_backup(db_path, backup_dir)

    result = maintain_database(
        db_path,
        backup_dir,
        min_free_bytes=0,
        min_free_percent=0,
        max_database_bytes=10**9,
        now=backup_path.stat().st_mtime,
    )
    repeated = maintain_database(
        db_path,
        backup_dir,
        min_free_bytes=0,
        min_free_percent=0,
        max_database_bytes=10**9,
        now=backup_path.stat().st_mtime,
    )

    assert result.row_counts == {
        "readings": 1,
        "deployment_attempts": 1,
        "system_metrics": 1,
    }
    assert result.alerts == ()
    assert repeated.row_counts == result.row_counts
    assert repeated.alerts == ()
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 1


def test_maintenance_reports_capacity_and_stale_backup_alerts(tmp_path):
    db_path = tmp_path / "iot.db"
    backup_dir = tmp_path / "backups"
    _database_with_history(db_path)
    backup_path = _compressed_backup(db_path, backup_dir)
    os.utime(backup_path, (1000, 1000))

    result = maintain_database(
        db_path,
        backup_dir,
        max_backup_age_hours=1,
        min_free_bytes=10**30,
        min_free_percent=101,
        max_database_bytes=1,
        now=1000 + 7200,
    )

    assert len(result.alerts) == 4
    assert any("backup" in alert for alert in result.alerts)
    assert any("database" in alert for alert in result.alerts)


def test_main_fails_when_backup_is_missing(tmp_path, capsys):
    db_path = tmp_path / "iot.db"
    _database_with_history(db_path)

    exit_code = main(["--db", str(db_path), "--backup-dir", str(tmp_path / "missing")])

    assert exit_code == 2
    assert "no SQLite backups found" in capsys.readouterr().err
