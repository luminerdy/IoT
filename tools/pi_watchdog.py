#!/usr/bin/env python3
"""External health monitor for the IoT Pi with guarded relay recovery."""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime


LOG = logging.getLogger("pi-watchdog")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


TARGET_HOST = os.getenv("WATCHDOG_TARGET_HOST", "iot-pi.local")
GATEWAY_HOST = os.getenv("WATCHDOG_GATEWAY_HOST", "router.local")
DASHBOARD_URL = os.getenv("WATCHDOG_DASHBOARD_URL", f"http://{TARGET_HOST}:8000/api/latest")
CHECK_INTERVAL_SECONDS = max(15, int(os.getenv("WATCHDOG_CHECK_INTERVAL_SECONDS", "60")))
READING_MAX_AGE_SECONDS = max(60, int(os.getenv("WATCHDOG_READING_MAX_AGE_SECONDS", "1200")))
FAILURES_BEFORE_RECOVERY = max(2, int(os.getenv("WATCHDOG_FAILURES_BEFORE_RECOVERY", "10")))
RECOVERY_COOLDOWN_SECONDS = max(600, int(os.getenv("WATCHDOG_RECOVERY_COOLDOWN_SECONDS", "3600")))
RELAY_ENABLED = env_bool("WATCHDOG_RELAY_ENABLED")
RELAY_GPIO = int(os.getenv("WATCHDOG_RELAY_GPIO", "17"))
RELAY_OFF_SECONDS = max(5, int(os.getenv("WATCHDOG_RELAY_OFF_SECONDS", "15")))


def ping(host: str) -> bool:
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "2", host],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def tcp_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def dashboard_health() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(DASHBOARD_URL, timeout=5) as response:
            rows = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return False, f"dashboard request failed: {exc}"
    if not isinstance(rows, list) or not rows:
        return False, "dashboard returned no devices"
    ages = [row.get("ageSeconds") for row in rows if isinstance(row.get("ageSeconds"), int)]
    if not ages:
        return False, "dashboard returned no reading ages"
    freshest = min(ages)
    fresh_count = sum(age <= READING_MAX_AGE_SECONDS for age in ages)
    required_fresh = max(1, len(rows) // 2)
    if fresh_count < required_fresh:
        return False, f"only {fresh_count}/{len(rows)} devices have fresh readings"
    return True, f"{fresh_count}/{len(rows)} devices fresh, newest {freshest}s old"


def set_relay(active: bool) -> None:
    level = "dh" if active else "dl"
    pull = "pd" if not active else "pn"
    subprocess.run(
        ["pinctrl", "set", str(RELAY_GPIO), "op", level, pull],
        check=True,
    )


def power_cycle() -> None:
    LOG.critical("Activating GPIO%d to remove target power", RELAY_GPIO)
    set_relay(True)
    try:
        time.sleep(RELAY_OFF_SECONDS)
    finally:
        set_relay(False)
    LOG.critical("Target power restored after %ds", RELAY_OFF_SECONDS)


def recovery_cooldown_elapsed(last_recovery: float | None, now: float) -> bool:
    """Allow the first recovery immediately, then enforce the cooldown."""
    return last_recovery is None or now - last_recovery >= RECOVERY_COOLDOWN_SECONDS


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    failures = 0
    last_recovery: float | None = None
    if RELAY_ENABLED:
        set_relay(False)
    LOG.info(
        "Watching %s every %ds; relay GPIO%d enabled=%s",
        TARGET_HOST,
        CHECK_INTERVAL_SECONDS,
        RELAY_GPIO,
        RELAY_ENABLED,
    )
    while True:
        started = time.monotonic()
        gateway_ok = ping(GATEWAY_HOST)
        target_ping = ping(TARGET_HOST)
        ssh_ok = tcp_open(TARGET_HOST, 22)
        api_ok, api_detail = dashboard_health()
        healthy = gateway_ok and target_ping and ssh_ok and api_ok
        if healthy:
            if failures:
                LOG.info("Target recovered after %d failed checks", failures)
            failures = 0
            LOG.info("Healthy: %s", api_detail)
        else:
            failures += 1
            LOG.warning(
                "Failed check %d/%d: gateway=%s ping=%s ssh=%s api=%s (%s)",
                failures,
                FAILURES_BEFORE_RECOVERY,
                gateway_ok,
                target_ping,
                ssh_ok,
                api_ok,
                api_detail,
            )
            cooldown_elapsed = recovery_cooldown_elapsed(last_recovery, time.monotonic())
            if failures >= FAILURES_BEFORE_RECOVERY and gateway_ok and cooldown_elapsed:
                if RELAY_ENABLED:
                    power_cycle()
                    last_recovery = time.monotonic()
                    failures = 0
                else:
                    LOG.critical("Recovery threshold reached; relay control is disabled")
        elapsed = time.monotonic() - started
        time.sleep(max(1, CHECK_INTERVAL_SECONDS - elapsed))


if __name__ == "__main__":
    main()
