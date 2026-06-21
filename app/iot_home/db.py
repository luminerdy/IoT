from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path("data/iot.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    location TEXT,
    sensor_type TEXT,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    datetime TEXT NOT NULL,
    rssi INTEGER,
    status TEXT,
    seq INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_readings_device_created
ON readings (device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    location TEXT,
    firmware_version TEXT,
    last_seen TEXT,
    online INTEGER NOT NULL DEFAULT 0,
    last_rssi INTEGER,
    last_status TEXT,
    last_seq INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def record_telemetry(conn: sqlite3.Connection, payload: dict) -> None:
    device_id = str(payload["deviceId"])
    location = payload.get("location")
    firmware_version = payload.get("firmwareVersion")
    sensor_type = payload.get("sensorType")
    reading_time = str(payload["datetime"])
    temperature = float(payload["temperature"])
    humidity = float(payload["humidity"])
    rssi = payload.get("rssi")
    status = payload.get("status", "OK")
    seq = payload.get("seq")

    with conn:
        conn.execute(
            """
            INSERT INTO readings (
                device_id, location, sensor_type, temperature, humidity,
                datetime, rssi, status, seq
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                location,
                sensor_type,
                temperature,
                humidity,
                reading_time,
                rssi,
                status,
                seq,
            ),
        )
        conn.execute(
            """
            INSERT INTO devices (
                device_id, location, firmware_version, last_seen, online,
                last_rssi, last_status, last_seq, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                location = excluded.location,
                firmware_version = excluded.firmware_version,
                last_seen = excluded.last_seen,
                online = 1,
                last_rssi = excluded.last_rssi,
                last_status = excluded.last_status,
                last_seq = excluded.last_seq,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                device_id,
                location,
                firmware_version,
                reading_time,
                rssi,
                status,
                seq,
            ),
        )


def record_status(conn: sqlite3.Connection, payload: dict) -> None:
    device_id = str(payload["deviceId"])
    status = str(payload.get("status", "unknown"))
    online = 1 if status == "online" else 0
    firmware_version = payload.get("firmwareVersion")
    status_time = payload.get("datetime")

    with conn:
        conn.execute(
            """
            INSERT INTO devices (
                device_id, firmware_version, last_seen, online,
                last_status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                firmware_version = COALESCE(excluded.firmware_version, devices.firmware_version),
                last_seen = COALESCE(excluded.last_seen, devices.last_seen),
                online = excluded.online,
                last_status = excluded.last_status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (device_id, firmware_version, status_time, online, status),
        )


def latest_readings(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            d.device_id,
            d.location,
            d.firmware_version,
            d.last_seen,
            d.online,
            d.last_rssi,
            d.last_status,
            d.updated_at,
            r.temperature,
            r.humidity,
            r.sensor_type,
            r.seq,
            r.created_at
        FROM devices d
        LEFT JOIN readings r ON r.id = (
            SELECT id
            FROM readings
            WHERE device_id = d.device_id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        )
        ORDER BY COALESCE(d.location, d.device_id)
        """
    ).fetchall()


def reading_history(
    conn: sqlite3.Connection, hours: int = 24, limit: int = 500
) -> list[sqlite3.Row]:
    safe_hours = max(1, min(int(hours), 168))
    safe_limit = max(1, min(int(limit), 2000))
    return conn.execute(
        """
        SELECT
            r.device_id,
            COALESCE(d.location, r.location, r.device_id) AS location,
            r.temperature,
            r.humidity,
            r.rssi,
            r.status,
            r.seq,
            r.datetime,
            r.created_at
        FROM readings r
        LEFT JOIN devices d ON d.device_id = r.device_id
        WHERE r.created_at >= datetime('now', ?)
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT ?
        """,
        (f"-{safe_hours} hours", safe_limit),
    ).fetchall()
