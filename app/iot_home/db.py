from __future__ import annotations

import ipaddress
import re
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/iot.db")
PRE_NTP_SENTINEL = "1970-01-01T00:00:00Z"
MIGRATIONS_DIR = Path(__file__).with_name("migrations")
MIGRATION_FILENAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")

REQUIRED_COLUMNS = {
    "readings": {
        "id",
        "device_id",
        "location",
        "sensor_type",
        "temperature",
        "humidity",
        "datetime",
        "rssi",
        "status",
        "seq",
        "created_at",
    },
    "devices": {
        "device_id",
        "location",
        "firmware_version",
        "last_seen",
        "online",
        "last_rssi",
        "last_status",
        "last_seq",
        "last_ip",
        "updated_at",
    },
    "deployment_attempts": {
        "id",
        "device_id",
        "from_version",
        "to_version",
        "observed_ip",
        "status",
        "rollout_id",
        "message",
        "created_at",
        "updated_at",
    },
    "system_metrics": {"id", "metric", "value", "created_at"},
}


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    apply_migrations(conn)


def migration_paths() -> tuple[tuple[int, Path], ...]:
    migrations = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match:
            migrations.append((int(match.group(1)), path))
    versions = [version for version, _ in migrations]
    if versions != list(range(1, len(versions) + 1)):
        raise RuntimeError(f"database migration sequence is invalid: {versions}")
    return tuple(migrations)


MIGRATIONS = migration_paths()
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1][0]


def migration_statements(sql: str) -> tuple[str, ...]:
    statements = []
    pending = ""
    for line in sql.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statement = pending.strip()
            if statement:
                statements.append(statement)
            pending = ""
    if pending.strip():
        raise RuntimeError("database migration contains an incomplete SQL statement")
    return tuple(statements)


def validate_schema(conn: sqlite3.Connection, version: int) -> None:
    for table, required in REQUIRED_COLUMNS.items():
        columns = {
            str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        missing = required - columns
        if missing:
            raise RuntimeError(f"database table {table} is missing columns: {sorted(missing)}")
    if version >= 2:
        reading_columns = {
            str(row["name"]) for row in conn.execute("PRAGMA table_info(readings)").fetchall()
        }
        if "legacy_dedupe_exempt" not in reading_columns:
            raise RuntimeError("database table readings is missing column: legacy_dedupe_exempt")
        index = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            ("uq_readings_device_seq_datetime",),
        ).fetchone()
        if index is None:
            raise RuntimeError("database is missing the readings dedupe index")


def apply_migrations(conn: sqlite3.Connection, target_version: int | None = None) -> None:
    current_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    latest_version = CURRENT_SCHEMA_VERSION if target_version is None else int(target_version)
    if current_version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"database schema {current_version} is newer than supported {CURRENT_SCHEMA_VERSION}"
        )
    if latest_version < current_version or latest_version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"unsupported database schema transition {current_version} -> {latest_version}"
        )
    if conn.in_transaction:
        raise RuntimeError("database migrations cannot start inside an active transaction")

    for version, path in MIGRATIONS:
        if version <= current_version or version > latest_version:
            continue
        try:
            conn.execute("BEGIN IMMEDIATE")
            sql = path.read_text(encoding="utf-8")
            for statement in migration_statements(sql):
                conn.execute(statement)
            validate_schema(conn, version)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise RuntimeError(f"database migration {version} ({path.name}) failed: {exc}") from exc


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
        conn.execute(
            """
            INSERT INTO readings (
                device_id, location, sensor_type, temperature, humidity,
                datetime, rssi, status, seq
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id, seq, datetime)
            WHERE datetime <> '1970-01-01T00:00:00Z'
              AND legacy_dedupe_exempt = 0
            DO NOTHING
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
