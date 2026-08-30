import sqlite3
from contextlib import closing

from iot_home import post_reboot_check
from iot_home.db import connect, init_db, latest_monitoring_events
from iot_home.post_reboot_check import CheckResult


def test_parse_watchdog_relay_events() -> None:
    text = """
Aug 08 21:52:37 pi-watchdog pi-watchdog[4390]: 2026-08-08 21:52:37,249 CRITICAL Activating GPIO17 to remove target power
Aug 08 21:52:52 pi-watchdog pi-watchdog[4390]: 2026-08-08 21:52:52,264 CRITICAL Target power restored after 15s
Aug 08 21:53:31 pi-watchdog pi-watchdog[4390]: 2026-08-08 21:53:31,142 INFO Healthy: 23/23 devices fresh, newest 1s old
"""

    events = post_reboot_check.parse_watchdog_relay_events(text)

    assert [event["message"] for event in events] == [
        "Activating GPIO17 to remove target power",
        "Target power restored after 15s",
    ]
    assert events[0]["created_at"] == "2026-08-08 21:52:37"


def test_record_post_reboot_check_records_overall_result(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "iot.db"
    backup_dir = tmp_path / "backups"
    with closing(connect(db_path)) as conn:
        init_db(conn)

    monkeypatch.setattr(
        post_reboot_check,
        "check_services",
        lambda services: CheckResult("services", True, "services ok", {"services": services}),
    )
    monkeypatch.setattr(
        post_reboot_check,
        "check_dashboard",
        lambda url: CheckResult("dashboard_api", True, "dashboard ok", {"url": url}),
    )
    monkeypatch.setattr(
        post_reboot_check,
        "check_database",
        lambda db: CheckResult("database", True, "database ok", {"db": str(db)}),
    )
    monkeypatch.setattr(
        post_reboot_check,
        "check_latest_backup",
        lambda path: CheckResult("latest_backup", True, "backup ok", {"backup_dir": str(path)}),
    )
    monkeypatch.setattr(
        post_reboot_check,
        "check_db_maintenance",
        lambda: CheckResult("db_maintenance", True, "maintenance ok", {}),
    )

    post_reboot_check.record_post_reboot_check(
        db_path,
        backup_dir=backup_dir,
        dashboard_url="http://127.0.0.1:8000/api/latest",
        services=("mosquitto.service",),
    )

    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        event = latest_monitoring_events(conn, event_type="post_reboot_check")[0]

    assert event["status"] == "ok"
    assert event["message"] == "post-reboot verification passed"
    assert "dashboard ok" in event["details_json"]


def test_import_watchdog_events_records_relay_events(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)

    class Result:
        returncode = 0
        stderr = ""
        stdout = (
            "Aug 08 21:52:37 pi-watchdog pi-watchdog[4390]: "
            "2026-08-08 21:52:37,249 CRITICAL Activating GPIO17 to remove target power\n"
        )

    monkeypatch.setattr(post_reboot_check, "run_command", lambda command, timeout=20: Result())

    imported = post_reboot_check.import_watchdog_events(
        db_path, ssh_target="pi-watchdog", since="24 hours ago"
    )

    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        event = latest_monitoring_events(conn, event_type="watchdog_relay")[0]

    assert imported == 1
    assert event["source"] == "pi-watchdog"
    assert event["message"] == "Activating GPIO17 to remove target power"
