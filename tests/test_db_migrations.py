import sqlite3
import threading
from contextlib import closing

import pytest
from iot_home.db import (
    CURRENT_SCHEMA_VERSION,
    PRE_NTP_SENTINEL,
    apply_migrations,
    connect,
    init_db,
    record_telemetry,
)


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def insert_reading(
    conn: sqlite3.Connection,
    *,
    device_id: str = "esp32-one",
    seq: int = 7,
    reading_time: str = "2026-08-07T12:00:00Z",
    temperature: float = 72.4,
) -> None:
    conn.execute(
        """
        INSERT INTO readings (device_id, temperature, humidity, datetime, seq)
        VALUES (?, ?, 45.2, ?, ?)
        """,
        (device_id, temperature, reading_time, seq),
    )


def test_fresh_database_migrates_to_current_and_is_idempotent(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        init_db(conn)

        first_version = schema_version(conn)
        first_schema = conn.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY 1, 2"
        ).fetchall()
        init_db(conn)
        second_schema = conn.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY 1, 2"
        ).fetchall()

    assert first_version == CURRENT_SCHEMA_VERSION == 2
    assert [tuple(row) for row in first_schema] == [tuple(row) for row in second_schema]


def test_concurrent_start_skips_migration_completed_while_waiting_for_lock(tmp_path):
    db_path = tmp_path / "iot.db"
    waiting_for_lock = threading.Event()
    continue_migration = threading.Event()
    errors: list[Exception] = []

    class PausingConnection:
        def __init__(self, conn: sqlite3.Connection):
            self.conn = conn
            self.paused = False

        @property
        def in_transaction(self) -> bool:
            return self.conn.in_transaction

        def execute(self, sql: str, parameters=()):
            if sql == "BEGIN IMMEDIATE" and not self.paused:
                self.paused = True
                waiting_for_lock.set()
                assert continue_migration.wait(timeout=5)
            return self.conn.execute(sql, parameters)

        def commit(self) -> None:
            self.conn.commit()

        def rollback(self) -> None:
            self.conn.rollback()

    def migrate_from_stale_version() -> None:
        try:
            with closing(connect(db_path)) as conn:
                apply_migrations(PausingConnection(conn))
        except Exception as exc:  # pragma: no cover - asserted in the parent thread
            errors.append(exc)

    worker = threading.Thread(target=migrate_from_stale_version)
    worker.start()
    assert waiting_for_lock.wait(timeout=5)

    with closing(connect(db_path)) as conn:
        init_db(conn)

    continue_migration.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert errors == []
    with closing(connect(db_path)) as conn:
        assert schema_version(conn) == CURRENT_SCHEMA_VERSION
        init_db(conn)


def test_version_one_migration_preserves_legacy_duplicates_and_indexes_canonical_row(
    tmp_path,
):
    with closing(connect(tmp_path / "iot.db")) as conn:
        apply_migrations(conn, target_version=1)
        insert_reading(conn, temperature=72.4)
        insert_reading(conn, temperature=73.0)
        insert_reading(conn, seq=8, temperature=74.0)
        insert_reading(conn, seq=1, reading_time=PRE_NTP_SENTINEL, temperature=65.0)
        insert_reading(conn, seq=1, reading_time=PRE_NTP_SENTINEL, temperature=66.0)
        conn.commit()
        before = conn.execute(
            "SELECT id, device_id, temperature, humidity, datetime, seq FROM readings ORDER BY id"
        ).fetchall()

        init_db(conn)

        after = conn.execute(
            "SELECT id, device_id, temperature, humidity, datetime, seq FROM readings ORDER BY id"
        ).fetchall()
        exemptions = conn.execute(
            "SELECT legacy_dedupe_exempt FROM readings ORDER BY id"
        ).fetchall()
        migrated_version = schema_version(conn)

        with pytest.raises(sqlite3.IntegrityError):
            insert_reading(conn, temperature=75.0)
        conn.rollback()
        insert_reading(conn, seq=1, reading_time=PRE_NTP_SENTINEL, temperature=67.0)
        conn.commit()
        sentinel_count = conn.execute(
            "SELECT COUNT(*) FROM readings WHERE datetime = ?", (PRE_NTP_SENTINEL,)
        ).fetchone()[0]

    assert migrated_version == CURRENT_SCHEMA_VERSION == 2
    assert [tuple(row) for row in before] == [tuple(row) for row in after]
    assert [row[0] for row in exemptions] == [0, 1, 0, 0, 0]
    assert sentinel_count == 3


def test_database_unique_index_and_recording_enforce_dedupe_contract(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        init_db(conn)
        payload = {
            "deviceId": "esp32-one",
            "datetime": "2026-08-07T12:00:00Z",
            "temperature": 72.4,
            "humidity": 45.2,
            "seq": 7,
        }
        record_telemetry(conn, payload)
        record_telemetry(conn, {**payload, "temperature": 73.0})
        sentinel = {**payload, "datetime": PRE_NTP_SENTINEL, "seq": 1}
        record_telemetry(conn, sentinel)
        record_telemetry(conn, {**sentinel, "temperature": 74.0})

        rows = conn.execute("SELECT temperature, datetime FROM readings ORDER BY id").fetchall()

    assert [tuple(row) for row in rows] == [
        (72.4, "2026-08-07T12:00:00Z"),
        (72.4, PRE_NTP_SENTINEL),
        (74.0, PRE_NTP_SENTINEL),
    ]


def test_migration_rejects_database_from_newer_schema(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        conn.execute("PRAGMA user_version = 99")

        with pytest.raises(RuntimeError, match="newer than supported"):
            init_db(conn)


def test_failed_legacy_adoption_rolls_back_version_and_created_tables(tmp_path):
    with closing(connect(tmp_path / "iot.db")) as conn:
        conn.execute("CREATE TABLE readings (id INTEGER PRIMARY KEY)")
        conn.commit()

        with pytest.raises(RuntimeError, match="database migration 1"):
            init_db(conn)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        failed_version = schema_version(conn)

    assert failed_version == 0
    assert tables == {"readings"}
