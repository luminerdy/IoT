"""Lossless SQLite integrity, backup, and capacity maintenance."""

from __future__ import annotations

import argparse
import gzip
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

PRESERVED_TABLES = ("readings", "deployment_attempts", "system_metrics")


@dataclass(frozen=True)
class MaintenanceResult:
    row_counts: dict[str, int]
    database_bytes: int
    wal_bytes: int
    free_bytes: int
    free_percent: float
    backup_path: Path
    backup_age_hours: float
    alerts: tuple[str, ...]


def _integrity_check(path: Path) -> str:
    uri = f"file:{path.resolve()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
    return "\n".join(str(row[0]) for row in rows)


def _row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    existing = {
        str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing = set(PRESERVED_TABLES) - existing
    if missing:
        raise RuntimeError(f"missing preserved tables: {', '.join(sorted(missing))}")
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in PRESERVED_TABLES
    }


def _newest_backup(backup_dir: Path) -> Path:
    backups = list(backup_dir.glob("iot-*.sqlite.gz"))
    if not backups:
        raise RuntimeError(f"no SQLite backups found in {backup_dir}")
    return max(backups, key=lambda path: path.stat().st_mtime)


def _check_compressed_backup(backup_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="iot-db-maintenance-") as temp_dir:
        restored_path = Path(temp_dir) / "restored.sqlite"
        with gzip.open(backup_path, "rb") as source, restored_path.open("wb") as target:
            shutil.copyfileobj(source, target)
        result = _integrity_check(restored_path)
        if result != "ok":
            raise RuntimeError(f"backup integrity check failed: {result}")


def maintain_database(
    db_path: Path,
    backup_dir: Path,
    *,
    max_backup_age_hours: float = 30.0,
    min_free_bytes: int = 10 * 1024**3,
    min_free_percent: float = 10.0,
    max_database_bytes: int = 10 * 1024**3,
    now: float | None = None,
) -> MaintenanceResult:
    """Inspect and optimize the database without removing historical rows."""
    db_path = db_path.resolve()
    backup_dir = backup_dir.resolve()
    if not db_path.is_file():
        raise RuntimeError(f"database not found: {db_path}")

    integrity = _integrity_check(db_path)
    if integrity != "ok":
        raise RuntimeError(f"database integrity check failed: {integrity}")

    with closing(sqlite3.connect(db_path)) as conn:
        before = _row_counts(conn)
        conn.execute("PRAGMA optimize")
        after = _row_counts(conn)
    if after != before:
        raise RuntimeError(f"historical row counts changed: before={before}, after={after}")

    backup_path = _newest_backup(backup_dir)
    _check_compressed_backup(backup_path)
    current_time = time.time() if now is None else now
    backup_age_hours = max(0.0, (current_time - backup_path.stat().st_mtime) / 3600)

    usage = shutil.disk_usage(db_path.parent)
    free_percent = 100.0 * usage.free / usage.total
    database_bytes = db_path.stat().st_size
    wal_path = Path(f"{db_path}-wal")
    wal_bytes = wal_path.stat().st_size if wal_path.exists() else 0

    alerts: list[str] = []
    if backup_age_hours > max_backup_age_hours:
        alerts.append(
            f"newest backup is {backup_age_hours:.1f}h old (limit {max_backup_age_hours:.1f}h)"
        )
    if usage.free < min_free_bytes:
        alerts.append(f"free space is {usage.free} bytes (minimum {min_free_bytes})")
    if free_percent < min_free_percent:
        alerts.append(f"free space is {free_percent:.1f}% (minimum {min_free_percent:.1f}%)")
    if database_bytes > max_database_bytes:
        alerts.append(f"database is {database_bytes} bytes (maximum {max_database_bytes})")

    return MaintenanceResult(
        row_counts=after,
        database_bytes=database_bytes,
        wal_bytes=wal_bytes,
        free_bytes=usage.free,
        free_percent=free_percent,
        backup_path=backup_path,
        backup_age_hours=backup_age_hours,
        alerts=tuple(alerts),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/iot.db"))
    parser.add_argument("--backup-dir", type=Path, default=Path("data/backups"))
    parser.add_argument("--max-backup-age-hours", type=float, default=30.0)
    parser.add_argument("--min-free-gib", type=float, default=10.0)
    parser.add_argument("--min-free-percent", type=float, default=10.0)
    parser.add_argument("--max-database-gib", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = maintain_database(
            args.db,
            args.backup_dir,
            max_backup_age_hours=args.max_backup_age_hours,
            min_free_bytes=int(args.min_free_gib * 1024**3),
            min_free_percent=args.min_free_percent,
            max_database_bytes=int(args.max_database_gib * 1024**3),
        )
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        print(f"CRITICAL: {exc}", file=sys.stderr)
        return 2

    counts = " ".join(f"{table}={count}" for table, count in result.row_counts.items())
    print(f"integrity=ok backup_integrity=ok {counts}")
    print(
        f"database_bytes={result.database_bytes} wal_bytes={result.wal_bytes} "
        f"free_bytes={result.free_bytes} free_percent={result.free_percent:.1f}"
    )
    print(f"backup={result.backup_path} backup_age_hours={result.backup_age_hours:.1f}")
    if result.alerts:
        for alert in result.alerts:
            print(f"ALERT: {alert}", file=sys.stderr)
        return 1
    print("maintenance_status=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
