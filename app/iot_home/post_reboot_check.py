"""Record local post-reboot and watchdog health checks."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
import subprocess
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path
from typing import NamedTuple

from .db import (
    DEFAULT_DB_PATH,
    connect,
    init_db,
    record_monitoring_event,
)

DEFAULT_BACKUP_DIR = Path("data/backups")
WATCHDOG_RELAY_RE = re.compile(
    r"^(?P<prefix>.*?)(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3} "
    r"(?P<level>\w+) (?P<message>Activating GPIO\d+ to remove target power|"
    r"Target power restored after \d+s)"
)


class CheckResult(NamedTuple):
    name: str
    ok: bool
    message: str
    details: dict


def run_command(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def check_services(services: tuple[str, ...]) -> CheckResult:
    active = run_command(["systemctl", "is-active", *services])
    enabled = run_command(["systemctl", "is-enabled", *services])
    ok = active.returncode == 0 and enabled.returncode == 0
    return CheckResult(
        "services",
        ok,
        "core services active and enabled" if ok else "one or more core services failed",
        {
            "services": list(services),
            "active_returncode": active.returncode,
            "active_stdout": active.stdout.strip().splitlines(),
            "enabled_returncode": enabled.returncode,
            "enabled_stdout": enabled.stdout.strip().splitlines(),
        },
    )


def check_dashboard(url: str) -> CheckResult:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            rows = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return CheckResult("dashboard_api", False, f"dashboard API failed: {exc}", {"url": url})
    if not isinstance(rows, list):
        return CheckResult(
            "dashboard_api", False, "dashboard API did not return a list", {"url": url}
        )
    stale = [row.get("location") or row.get("deviceId") for row in rows if row.get("stale")]
    offline = [row.get("location") or row.get("deviceId") for row in rows if not row.get("online")]
    return CheckResult(
        "dashboard_api",
        True,
        f"dashboard API returned {len(rows)} device records",
        {"url": url, "total": len(rows), "stale": stale, "offline": offline},
    )


def check_database(db_path: Path) -> CheckResult:
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    except sqlite3.Error as exc:
        return CheckResult("database", False, f"database check failed: {exc}", {"db": str(db_path)})
    return CheckResult(
        "database",
        integrity == "ok",
        f"database integrity {integrity}",
        {"db": str(db_path), "user_version": user_version, "integrity": integrity},
    )


def check_latest_backup(backup_dir: Path) -> CheckResult:
    backups = sorted(backup_dir.glob("iot-*.sqlite.gz"), key=lambda path: path.stat().st_mtime)
    if not backups:
        return CheckResult(
            "latest_backup", False, "no SQLite backups found", {"backup_dir": str(backup_dir)}
        )
    latest = backups[-1]
    try:
        with gzip.open(latest, "rb") as handle:
            header = handle.read(100)
    except OSError as exc:
        return CheckResult(
            "latest_backup",
            False,
            f"latest backup could not be read: {exc}",
            {"backup": str(latest)},
        )
    return CheckResult(
        "latest_backup",
        bool(header),
        f"latest backup readable: {latest.name}",
        {"backup": str(latest), "bytes": latest.stat().st_size},
    )


def check_db_maintenance() -> CheckResult:
    result = run_command(
        [
            "systemctl",
            "is-active",
            "iot-home-db-maintenance.timer",
            "iot-home-db-maintenance.service",
        ]
    )
    ok = result.returncode in {0, 3} and "failed" not in result.stdout
    return CheckResult(
        "db_maintenance",
        ok,
        "database maintenance timer checked" if ok else "database maintenance status needs review",
        {"returncode": result.returncode, "stdout": result.stdout.strip().splitlines()},
    )


def overall_status(results: list[CheckResult]) -> str:
    return "ok" if all(result.ok for result in results) else "warn"


def record_post_reboot_check(
    db_path: Path,
    *,
    backup_dir: Path,
    dashboard_url: str,
    services: tuple[str, ...],
) -> int:
    results = [
        check_services(services),
        check_dashboard(dashboard_url),
        check_database(db_path),
        check_latest_backup(backup_dir),
        check_db_maintenance(),
    ]
    status = overall_status(results)
    with closing(connect(db_path)) as conn:
        init_db(conn)
        return record_monitoring_event(
            conn,
            source="hub",
            event_type="post_reboot_check",
            severity="info" if status == "ok" else "warning",
            status=status,
            message="post-reboot verification passed"
            if status == "ok"
            else "post-reboot verification has warnings",
            details={"checks": [result._asdict() for result in results]},
        )


def parse_watchdog_relay_events(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        match = WATCHDOG_RELAY_RE.match(line)
        if not match:
            continue
        events.append(
            {
                "created_at": match.group("stamp"),
                "level": match.group("level").lower(),
                "message": match.group("message"),
                "raw": line,
            }
        )
    return events


def import_watchdog_events(db_path: Path, *, ssh_target: str, since: str) -> int:
    command = [
        "ssh",
        ssh_target,
        f"journalctl -u pi-watchdog.service --since {since!r} --no-pager",
    ]
    result = run_command(command, timeout=30)
    if result.returncode != 0:
        with closing(connect(db_path)) as conn:
            init_db(conn)
            record_monitoring_event(
                conn,
                source=ssh_target,
                event_type="watchdog_journal_import",
                severity="warning",
                status="warn",
                message="watchdog journal import failed",
                details={"returncode": result.returncode, "stderr": result.stderr.strip()},
            )
        return 0

    count = 0
    with closing(connect(db_path)) as conn:
        init_db(conn)
        for event in parse_watchdog_relay_events(result.stdout):
            record_monitoring_event(
                conn,
                source=ssh_target,
                event_type="watchdog_relay",
                severity="critical",
                status="recovery",
                message=event["message"],
                details={"journal": event["raw"]},
                created_at=event["created_at"],
            )
            count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:8000/api/latest")
    parser.add_argument(
        "--service",
        action="append",
        default=[],
        help="Service to verify; defaults to the three core IoT services.",
    )
    parser.add_argument("--import-watchdog", action="store_true")
    parser.add_argument("--watchdog-ssh-target", default="pi-watchdog")
    parser.add_argument("--watchdog-since", default="24 hours ago")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    services = tuple(
        args.service
        or [
            "mosquitto.service",
            "iot-home-collector.service",
            "iot-home-dashboard.service",
        ]
    )
    event_id = record_post_reboot_check(
        args.db,
        backup_dir=args.backup_dir,
        dashboard_url=args.dashboard_url,
        services=services,
    )
    imported = 0
    if args.import_watchdog:
        imported = import_watchdog_events(
            args.db,
            ssh_target=args.watchdog_ssh_target,
            since=args.watchdog_since,
        )
    print(f"post_reboot_check_event={event_id} watchdog_events_imported={imported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
