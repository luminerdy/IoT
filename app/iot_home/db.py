from __future__ import annotations

import ipaddress
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

CREATE INDEX IF NOT EXISTS idx_readings_created
ON readings (created_at DESC);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    location TEXT,
    firmware_version TEXT,
    last_seen TEXT,
    online INTEGER NOT NULL DEFAULT 0,
    last_rssi INTEGER,
    last_status TEXT,
    last_seq INTEGER,
    last_ip TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deployment_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    from_version TEXT,
    to_version TEXT NOT NULL,
    observed_ip TEXT,
    status TEXT NOT NULL,
    rollout_id TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_deployment_attempts_device_created
ON deployment_attempts (device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_created
ON system_metrics (metric, created_at DESC);
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
    ensure_column(conn, "devices", "last_ip", "TEXT")
    conn.commit()


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def observed_ip(payload: dict) -> str | None:
    value = payload.get("localIp") or payload.get("ipAddress") or payload.get("ip")
    if value is None:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def telemetry_exists(conn: sqlite3.Connection, device_id: str, reading_time: str, seq: object) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM readings
            WHERE device_id = ?
              AND datetime = ?
              AND seq IS ?
            LIMIT 1
            """,
            (device_id, reading_time, seq),
        ).fetchone()
        is not None
    )


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
    ip = observed_ip(payload)

    with conn:
        if not telemetry_exists(conn, device_id, reading_time, seq):
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
                last_rssi, last_status, last_seq, last_ip, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                location = excluded.location,
                firmware_version = excluded.firmware_version,
                last_seen = excluded.last_seen,
                online = 1,
                last_rssi = excluded.last_rssi,
                last_status = excluded.last_status,
                last_seq = excluded.last_seq,
                last_ip = COALESCE(excluded.last_ip, devices.last_ip),
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
                ip,
            ),
        )


def record_status(conn: sqlite3.Connection, payload: dict) -> None:
    device_id = str(payload["deviceId"])
    status = str(payload.get("status", "unknown"))
    online = 1 if status == "online" else 0
    firmware_version = payload.get("firmwareVersion")
    status_time = payload.get("datetime")
    ip = observed_ip(payload)

    with conn:
        conn.execute(
            """
            INSERT INTO devices (
                device_id, firmware_version, last_seen, online,
                last_status, last_ip, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                firmware_version = COALESCE(excluded.firmware_version, devices.firmware_version),
                last_seen = COALESCE(excluded.last_seen, devices.last_seen),
                online = excluded.online,
                last_status = excluded.last_status,
                last_ip = COALESCE(excluded.last_ip, devices.last_ip),
                updated_at = CURRENT_TIMESTAMP
            """,
            (device_id, firmware_version, status_time, online, status, ip),
        )


def recent_deployment_attempt_exists(
    conn: sqlite3.Connection,
    device_id: str,
    to_version: str,
    cooldown_seconds: int,
) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM deployment_attempts
            WHERE device_id = ?
              AND to_version = ?
              AND created_at >= datetime('now', ?)
            LIMIT 1
            """,
            (device_id, to_version, f"-{max(0, int(cooldown_seconds))} seconds"),
        ).fetchone()
        is not None
    )


def record_deployment_attempt(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    from_version: str | None,
    to_version: str,
    observed_ip: str | None = None,
    status: str = "detected",
    rollout_id: str | None = None,
    message: str | None = None,
) -> int:
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO deployment_attempts (
                device_id, from_version, to_version, observed_ip,
                status, rollout_id, message, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (device_id, from_version, to_version, observed_ip, status, rollout_id, message),
        )
        return int(cursor.lastrowid)


def update_deployment_attempt(
    conn: sqlite3.Connection,
    attempt_id: int,
    *,
    status: str,
    rollout_id: str | None = None,
    message: str | None = None,
) -> None:
    with conn:
        conn.execute(
            """
            UPDATE deployment_attempts
            SET status = ?,
                rollout_id = COALESCE(?, rollout_id),
                message = COALESCE(?, message),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, rollout_id, message, attempt_id),
        )


def record_system_metric(conn: sqlite3.Connection, metric: str, value: float) -> None:
    with conn:
        conn.execute(
            "INSERT INTO system_metrics (metric, value) VALUES (?, ?)",
            (metric, float(value)),
        )


def latest_system_metric(conn: sqlite3.Connection, metric: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT metric, value, created_at
        FROM system_metrics
        WHERE metric = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (metric,),
    ).fetchone()


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
            d.last_ip,
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
    safe_limit = max(1, min(int(limit), 50000))
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
