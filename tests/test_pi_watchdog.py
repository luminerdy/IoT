from tools import pi_watchdog


def test_first_recovery_is_not_blocked_by_startup_uptime():
    assert pi_watchdog.recovery_cooldown_elapsed(None, 30.0)


def test_repeated_recovery_waits_for_cooldown(monkeypatch):
    monkeypatch.setattr(pi_watchdog, "RECOVERY_COOLDOWN_SECONDS", 3600)

    assert not pi_watchdog.recovery_cooldown_elapsed(100.0, 3699.0)
    assert pi_watchdog.recovery_cooldown_elapsed(100.0, 3700.0)
