from __future__ import annotations

import ipaddress
import json
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

MONITORING_EVENT_COLUMNS = {
    "id",
    "source",
    "event_type",
    "severity",
    "status",
    "message",
    "details_json",
    "created_at",
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
    if version >= 3:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(monitoring_events)").fetchall()
        }
        missing = MONITORING_EVENT_COLUMNS - columns
        if missing:
            raise RuntimeError(
                f"database table monitoring_events is missing columns: {sorted(missing)}"
            )
    if version >= 4:
        table_columns = {
            table: {
                str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for table in ("readings", "devices")
        }
        expected = {
            "readings": {"num_read_errors", "num_filtered_readings"},
            "devices": {"last_num_read_errors", "last_num_filtered_readings"},
        }
        for table, required_columns in expected.items():
            missing = required_columns - table_columns[table]
            if missing:
                raise RuntimeError(f"database table {table} is missing columns: {sorted(missing)}")
        for index_name in (
            "idx_monitoring_events_created",
            "idx_monitoring_events_type_created",
        ):
            index = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
                (index_name,),
            ).fetchone()
            if index is None:
                raise RuntimeError(f"database is missing monitoring index: {index_name}")


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
            locked_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if locked_version > CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"database schema {locked_version} is newer than supported "
                    f"{CURRENT_SCHEMA_VERSION}"
                )
            if locked_version >= version:
                conn.commit()
                current_version = locked_version
                continue
            if locked_version != version - 1:
                raise RuntimeError(
                    f"database schema changed unexpectedly from {current_version} "
                    f"to {locked_version} before migration {version}"
                )
            sql = path.read_text(encoding="utf-8")
            for statement in migration_statements(sql):
                conn.execute(statement)
            validate_schema(conn, version)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
            current_version = version
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
    num_read_errors = payload.get("numReadErrors")
    num_filtered_readings = payload.get("numFilteredReadings")
    ip = observed_ip(payload)

    with conn:
        conn.execute(
            """
            INSERT INTO readings (
                device_id, location, sensor_type, temperature, humidity,
                datetime, rssi, status, seq, num_read_errors, num_filtered_readings
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                num_read_errors,
                num_filtered_readings,
            ),
        )
        conn.execute(
            """
            INSERT INTO devices (
                device_id, location, firmware_version, last_seen, online,
                last_rssi, last_status, last_seq, last_ip, last_num_read_errors,
                last_num_filtered_readings, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                location = excluded.location,
                firmware_version = excluded.firmware_version,
                last_seen = excluded.last_seen,
                online = 1,
                last_rssi = excluded.last_rssi,
                last_status = excluded.last_status,
                last_seq = excluded.last_seq,
                last_ip = COALESCE(excluded.last_ip, devices.last_ip),
                last_num_read_errors = excluded.last_num_read_errors,
                last_num_filtered_readings = excluded.last_num_filtered_readings,
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
                num_read_errors,
                num_filtered_readings,
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


def record_monitoring_event(
    conn: sqlite3.Connection,
    *,
    source: str,
    event_type: str,
    severity: str = "info",
    status: str = "ok",
    message: str | None = None,
    details: dict | None = None,
    created_at: str | None = None,
) -> int:
    details_json = json.dumps(details or {}, sort_keys=True) if details is not None else None
    with conn:
        if created_at is None:
            cursor = conn.execute(
                """
                INSERT INTO monitoring_events (
                    source, event_type, severity, status, message, details_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source, event_type, severity, status, message, details_json),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO monitoring_events (
                    source, event_type, severity, status, message, details_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source, event_type, severity, status, message, details_json, created_at),
            )
        return int(cursor.lastrowid)


def latest_monitoring_events(
    conn: sqlite3.Connection,
    *,
    limit: int = 10,
    event_type: str | None = None,
) -> list[sqlite3.Row]:
    safe_limit = max(1, min(int(limit), 100))
    if event_type is None:
        return conn.execute(
            """
            SELECT id, source, event_type, severity, status, message, details_json, created_at
            FROM monitoring_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return conn.execute(
        """
        SELECT id, source, event_type, severity, status, message, details_json, created_at
        FROM monitoring_events
        WHERE event_type = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (event_type, safe_limit),
    ).fetchall()


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
            d.last_num_read_errors,
            d.last_num_filtered_readings,
            d.updated_at,
            r.temperature,
            r.humidity,
            r.sensor_type,
            r.seq,
            r.num_read_errors,
            r.num_filtered_readings,
            r.created_at,
            CASE
                WHEN r.num_read_errors IS NULL THEN NULL
                WHEN previous.num_read_errors IS NULL THEN r.num_read_errors
                WHEN r.num_read_errors >= previous.num_read_errors
                    THEN r.num_read_errors - previous.num_read_errors
                ELSE r.num_read_errors
            END AS read_error_delta,
            CASE
                WHEN r.num_filtered_readings IS NULL THEN NULL
                WHEN previous.num_filtered_readings IS NULL THEN r.num_filtered_readings
                WHEN r.num_filtered_readings >= previous.num_filtered_readings
                    THEN r.num_filtered_readings - previous.num_filtered_readings
                ELSE r.num_filtered_readings
            END AS filtered_reading_delta,
            (
                SELECT COUNT(*)
                FROM readings recent
                WHERE recent.device_id = d.device_id
                  AND recent.seq <= 1
                  AND recent.created_at >= datetime('now', '-24 hours')
            ) AS recent_seq_resets
        FROM devices d
        LEFT JOIN readings r ON r.id = (
            SELECT id
            FROM readings
            WHERE device_id = d.device_id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        )
        LEFT JOIN readings previous ON previous.id = (
            SELECT id
            FROM readings
            WHERE device_id = d.device_id
              AND id < r.id
              AND (num_read_errors IS NOT NULL OR num_filtered_readings IS NOT NULL)
            ORDER BY id DESC
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
