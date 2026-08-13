import base64
import http.client
import json
import threading
from argparse import Namespace
from contextlib import closing
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from iot_home import dashboard
from iot_home.dashboard import (
    Handler,
    basic_request_authorized,
    firmware_request_authorized,
    location_payload,
    page,
    parse_utc,
    query_int,
    valid_client_address,
)
from iot_home.db import (
    connect,
    init_db,
    latest_readings,
    record_monitoring_event,
    record_status,
    record_system_metric,
    record_telemetry,
)
from iot_home.locations import load_locations
from iot_home.retired_devices import load_retired_devices


def test_dashboard_page_keeps_attic_and_thermal_sorting_contract() -> None:
    html = page().decode("utf-8")

    assert 'key: "attic"' in html
    assert 'label: "Attic"' in html
    assert "!isAtticGraphLocation(location)" in html
    assert 'zone?.type === "attic"' in html
    assert "deviceLabel(a).localeCompare(deviceLabel(b)" in html
    assert "return bTemp - aTemp || deviceLabel(a).localeCompare(deviceLabel(b));" in html
    assert "Math.min(75," in html
    assert "Math.max(100," in html
    assert "[max, 100, 75, min]" in html
    assert 'id="pi-temperature"' in html
    assert 'id="post-reboot-status"' in html
    assert 'id="watchdog-status"' in html
    assert 'fetch("/api/system"' in html


def test_firmware_capability_key_is_required() -> None:
    assert firmware_request_authorized("correct", "correct") is True
    assert firmware_request_authorized("wrong", "correct") is False
    assert firmware_request_authorized(None, "correct") is False
    assert firmware_request_authorized("correct", None) is False


def test_basic_auth_uses_configured_credentials() -> None:
    encoded = base64.b64encode(b"admin:correct").decode("ascii")
    assert basic_request_authorized(f"Basic {encoded}", "admin", "correct") is True
    assert basic_request_authorized(f"Basic {encoded}", "admin", "wrong") is False
    assert basic_request_authorized("Basic not-base64", "admin", "correct") is False
    assert basic_request_authorized(None, "admin", "correct") is False


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer token",
        "Basic",
        "Basic bm8tY29sb24=",
        "Basic //8=",
    ],
)
def test_basic_auth_rejects_malformed_headers(authorization) -> None:
    assert basic_request_authorized(authorization, "admin", "correct") is False


def test_dashboard_helpers_normalize_dates_queries_and_addresses() -> None:
    assert parse_utc(None) is None
    assert parse_utc("not-a-date") is None
    assert parse_utc("2026-08-07T12:00:00").isoformat() == "2026-08-07T12:00:00+00:00"
    assert parse_utc("2026-08-07T12:00:00Z").isoformat() == "2026-08-07T12:00:00+00:00"
    assert query_int({}, "hours", 24) == 24
    assert query_int({"hours": ["bad"]}, "hours", 24) == 24
    assert query_int({"hours": ["12"]}, "hours", 24) == 12
    assert valid_client_address("127.0.0.1") is True
    assert valid_client_address("8.8.8.8") is False


def test_location_payload_includes_mapped_only_devices() -> None:
    payload = location_payload([], 120, {"esp32-mapped": "Mapped Room"})

    assert payload["locations"] == {"esp32-mapped": "Mapped Room"}
    assert payload["devices"][0]["status"] == "mapped only"
    assert payload["devices"][0]["online"] is False


def test_load_retired_devices_accepts_array_and_object(tmp_path) -> None:
    array_path = tmp_path / "retired-array.json"
    array_path.write_text('[" esp32-one ", ""]', encoding="utf-8")
    object_path = tmp_path / "retired-object.json"
    object_path.write_text('{"devices": ["esp32-two"]}', encoding="utf-8")

    assert load_retired_devices(array_path) == {"esp32-one"}
    assert load_retired_devices(object_path) == {"esp32-two"}


def test_firmware_route_requires_correct_capability_key(tmp_path) -> None:
    firmware_dir = tmp_path / "firmware"
    release_dir = firmware_dir / "test-release"
    release_dir.mkdir(parents=True)
    expected = b"test-firmware"
    (release_dir / "firmware.bin").write_bytes(expected)

    Handler.firmware_dir = firmware_dir
    Handler.firmware_download_key = "correct-key"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/firmware/test-release/firmware.bin"

    try:
        for url in (
            base_url,
            f"{base_url}?key=wrong-key",
            f"{base_url}?key=correct-key&key=duplicate",
        ):
            with pytest.raises(HTTPError) as exc_info:
                urlopen(url)
            assert exc_info.value.code == 401

        with closing(urlopen(f"{base_url}?key=correct-key")) as response:
            assert response.status == 200
            assert response.read() == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_dashboard_access_log_redacts_query_string(capsys) -> None:
    handler = object.__new__(Handler)
    handler.path = "/firmware/test/firmware.bin?key=do-not-log-this"
    handler.command = "GET"
    handler.address_string = lambda: "127.0.0.1"

    handler.log_message("%s %s %s", "request with secret", "200", "-")

    output = capsys.readouterr().out
    assert "do-not-log-this" not in output
    assert "/firmware/test/firmware.bin" in output
    assert "response=200" in output


def test_location_writes_require_auth_and_preserve_concurrent_updates(tmp_path) -> None:
    db_path = tmp_path / "iot.db"
    locations_path = tmp_path / "locations.json"
    with closing(connect(db_path)) as conn:
        init_db(conn)

    Handler.db_path = db_path
    Handler.locations_path = locations_path
    Handler.dashboard_username = "admin"
    Handler.dashboard_password = "correct"
    Handler.allow_unauthenticated_read = True
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/locations"
    auth = base64.b64encode(b"admin:correct").decode("ascii")
    errors = []

    def save(device_id: str) -> None:
        try:
            body = json.dumps({"deviceId": device_id, "location": f"Location {device_id}"}).encode(
                "utf-8"
            )
            request = Request(
                url,
                data=body,
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                method="POST",
            )
            with closing(urlopen(request)) as response:
                assert response.status == 200
        except Exception as exc:
            errors.append(exc)

    try:
        unauthenticated = Request(url, data=b"{}", method="POST")
        with pytest.raises(HTTPError) as exc_info:
            urlopen(unauthenticated)
        assert exc_info.value.code == 401
        assert exc_info.value.headers["WWW-Authenticate"].startswith("Basic ")

        workers = [
            threading.Thread(target=save, args=(f"esp32-{index:012x}",)) for index in range(8)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)

        assert errors == []
        locations = load_locations(locations_path)
        assert len(locations) == 8
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _configure_handler(tmp_path, *, with_metric=True, allow_read=True):
    db_path = tmp_path / "iot.db"
    locations_path = tmp_path / "locations.json"
    floorplan_path = tmp_path / "floorplan.json"
    retired_devices_path = tmp_path / "retired_devices.json"
    asset_dir = tmp_path / "assets"
    firmware_dir = tmp_path / "firmware"
    asset_dir.mkdir()
    firmware_dir.mkdir()
    (asset_dir / "house.txt").write_text("house asset", encoding="utf-8")
    locations_path.write_text(
        json.dumps({"esp32-test": "Test Room", "esp32-mapped": "Mapped Room"}),
        encoding="utf-8",
    )
    floorplan_path.write_text(
        json.dumps(
            {
                "backgroundImage": "/dashboard-assets/house.txt",
                "zones": [{"location": "Test Room", "x": 1, "y": 2, "w": 3, "h": 4}],
            }
        ),
        encoding="utf-8",
    )
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-test",
                "location": "Reported Room",
                "firmwareVersion": "1.0.0",
                "datetime": "2026-08-07T12:00:00Z",
                "temperature": 72.5,
                "humidity": 41.0,
                "rssi": -50,
                "seq": 4,
            },
        )
        if with_metric:
            record_system_metric(conn, "pi_cpu_temperature_f", 120.5)
        record_monitoring_event(
            conn,
            source="hub",
            event_type="post_reboot_check",
            status="ok",
            message="post-reboot verification passed",
            created_at="2026-08-09 12:00:00",
        )
        record_monitoring_event(
            conn,
            source="pi-watchdog",
            event_type="watchdog_relay",
            severity="critical",
            status="recovery",
            message="Target power restored after 15s",
            created_at="2026-08-09 12:05:00",
        )

    Handler.db_path = db_path
    Handler.locations_path = locations_path
    Handler.retired_devices_path = retired_devices_path
    Handler.floorplan_path = floorplan_path
    Handler.asset_dir = asset_dir
    Handler.firmware_dir = firmware_dir
    Handler.stale_seconds = 120
    Handler.dashboard_username = "admin"
    Handler.dashboard_password = "correct"
    Handler.firmware_download_key = "firmware-key"
    Handler.allow_unauthenticated_read = allow_read
    Handler.locations = load_locations(locations_path)
    Handler.retired_devices = load_retired_devices(retired_devices_path)
    return db_path, locations_path, floorplan_path


def _start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _read_json(url):
    with closing(urlopen(url)) as response:
        assert response.status == 200
        return json.loads(response.read())


def test_dashboard_read_routes_and_static_assets(tmp_path) -> None:
    _configure_handler(tmp_path)
    server, thread = _start_server()
    base = f"http://127.0.0.1:{server.server_port}"

    try:
        with closing(urlopen(f"{base}/")) as response:
            assert response.status == 200
            assert b"IoT Home Monitor" in response.read()
        with closing(urlopen(f"{base}/index.html")) as response:
            assert response.status == 200
        with closing(urlopen(f"{base}/dashboard-assets/house.txt")) as response:
            assert response.read() == b"house asset"

        latest = _read_json(f"{base}/api/latest")
        history = _read_json(f"{base}/api/history?hours=bad&limit=1")
        floorplan = _read_json(f"{base}/api/floorplan")
        system = _read_json(f"{base}/api/system")
        locations = _read_json(f"{base}/api/locations")

        assert latest[0]["location"] == "Test Room"
        assert latest[0]["stability"] == {
            "state": "stable",
            "label": "Stable",
            "detail": "No resets/24h",
        }
        assert latest[0]["recentSeqResets"] == 0
        assert history[0]["deviceId"] == "esp32-test"
        assert floorplan["zones"][0]["location"] == "Test Room"
        assert system["temperatureF"] == 120.5
        assert system["monitoring"]["latestPostReboot"]["status"] == "ok"
        assert system["monitoring"]["latestWatchdogRelay"]["message"] == (
            "Target power restored after 15s"
        )
        assert len(locations["devices"]) == 2

        for path in (
            "/missing",
            "/dashboard-assets/missing.txt",
            "/dashboard-assets/%2e%2e/secret.txt",
        ):
            with pytest.raises(HTTPError) as exc_info:
                urlopen(f"{base}{path}")
            assert exc_info.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_dashboard_read_routes_hide_retired_devices(tmp_path) -> None:
    db_path, _, _ = _configure_handler(tmp_path)
    Handler.retired_devices_path.write_text(
        '["esp32-test", "esp32-retired"]', encoding="utf-8"
    )
    with closing(connect(db_path)) as conn:
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-retired",
                "location": "UNMAPPED",
                "firmwareVersion": "1.0.0",
                "datetime": "2026-08-07T12:05:00Z",
                "temperature": 80.0,
                "humidity": 50.0,
                "rssi": -60,
                "seq": 1,
            },
        )
    server, thread = _start_server()
    base = f"http://127.0.0.1:{server.server_port}"

    try:
        latest = _read_json(f"{base}/api/latest")
        history = _read_json(f"{base}/api/history")
        locations = _read_json(f"{base}/api/locations")

        assert latest == []
        assert "esp32-test" not in {row["deviceId"] for row in history}
        assert "esp32-retired" not in {row["deviceId"] for row in history}
        assert "esp32-test" not in {row["deviceId"] for row in locations["devices"]}
        assert "esp32-retired" not in {row["deviceId"] for row in locations["devices"]}
        assert "esp32-test" not in locations["locations"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_latest_staleness_uses_telemetry_age_not_status_age(tmp_path) -> None:
    db_path = tmp_path / "iot.db"
    with closing(connect(db_path)) as conn:
        init_db(conn)
        record_telemetry(
            conn,
            {
                "deviceId": "esp32-test",
                "location": "GarageDriveway",
                "firmwareVersion": "1.0.0",
                "datetime": "2026-08-11T22:38:25Z",
                "temperature": 100.0,
                "humidity": 28.5,
                "rssi": -85,
                "status": "OK",
                "seq": 164,
            },
        )
        conn.execute(
            "UPDATE readings SET created_at = datetime('now', '-1 hour') WHERE device_id = ?",
            ("esp32-test",),
        )
        record_status(
            conn,
            {
                "deviceId": "esp32-test",
                "firmwareVersion": "1.0.0",
                "datetime": "2026-08-12T00:46:22Z",
                "status": "online",
                "ip": "203.0.113.20",
            },
        )

        latest = latest_readings(conn)[0]
        payload = dashboard.row_to_dict(latest, stale_seconds=120, locations={})

    assert payload["online"] is True
    assert payload["stale"] is True
    assert payload["seq"] == 164
    assert payload["status"] == "online"
    assert payload["ageSeconds"] > 120
    assert payload["deviceAgeSeconds"] < 120
    assert payload["observedAt"] == payload["telemetryObservedAt"]
    assert payload["observedAt"].endswith("Z")
    assert payload["updatedAt"].endswith("Z")
    assert payload["deviceObservedAt"].endswith("Z")


def test_dashboard_read_auth_floorplan_error_and_empty_system(tmp_path) -> None:
    _, _, floorplan_path = _configure_handler(tmp_path, with_metric=False, allow_read=False)
    server, thread = _start_server()
    base = f"http://127.0.0.1:{server.server_port}"
    auth = base64.b64encode(b"admin:correct").decode("ascii")

    try:
        with pytest.raises(HTTPError) as exc_info:
            urlopen(f"{base}/api/system")
        assert exc_info.value.code == 401

        request = Request(f"{base}/api/system", headers={"Authorization": f"Basic {auth}"})
        with closing(urlopen(request)) as response:
            system = json.loads(response.read())
        assert system["temperatureF"] is None
        assert system["sampledAt"] is None
        assert system["ageSeconds"] is None
        assert system["monitoring"]["latestPostReboot"]["eventType"] == "post_reboot_check"

        floorplan_path.write_text("[]", encoding="utf-8")
        request = Request(f"{base}/api/floorplan", headers={"Authorization": f"Basic {auth}"})
        with pytest.raises(HTTPError) as exc_info:
            urlopen(request)
        assert exc_info.value.code == 500
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _raw_post(server, path, body, *, content_length=None):
    auth = base64.b64encode(b"admin:correct").decode("ascii")
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    connection.putrequest("POST", path)
    connection.putheader("Authorization", f"Basic {auth}")
    connection.putheader("Content-Type", "application/json")
    connection.putheader(
        "Content-Length", str(len(body) if content_length is None else content_length)
    )
    connection.endheaders(body)
    response = connection.getresponse()
    response.read()
    status = response.status
    connection.close()
    return status


@pytest.mark.parametrize(
    ("body", "content_length"),
    [
        (b"", 0),
        (b"{}", "invalid"),
        (b"x" * 4097, 4097),
        (b"not-json", None),
        (b"[]", None),
        (b'{"deviceId":"","location":"Room"}', None),
        (json.dumps({"deviceId": "x" * 129, "location": "Room"}).encode(), None),
        (json.dumps({"deviceId": "esp32-test", "location": "x" * 81}).encode(), None),
    ],
)
def test_location_write_rejects_invalid_requests(tmp_path, body, content_length) -> None:
    _configure_handler(tmp_path)
    server, thread = _start_server()

    try:
        assert _raw_post(server, "/api/locations", body, content_length=content_length) == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_location_write_rejects_unknown_route_and_can_remove_mapping(tmp_path) -> None:
    _, locations_path, _ = _configure_handler(tmp_path)
    server, thread = _start_server()

    try:
        assert _raw_post(server, "/api/unknown", b"{}") == 404
        body = json.dumps({"deviceId": "esp32-test", "location": ""}).encode()
        assert _raw_post(server, "/api/locations", body) == 200
        assert "esp32-test" not in load_locations(locations_path)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _dashboard_args(tmp_path, **overrides):
    values = {
        "host": "127.0.0.1",
        "port": 0,
        "db": tmp_path / "iot.db",
        "firmware_dir": tmp_path / "firmware",
        "asset_dir": tmp_path / "assets",
        "floorplan": tmp_path / "floorplan.json",
        "locations": tmp_path / "locations.json",
        "retired_devices": tmp_path / "retired_devices.json",
        "stale_seconds": 120,
        "firmware_download_key": "key",
        "username": "admin",
        "password": "correct",
        "allow_unauthenticated_read": True,
    }
    values.update(overrides)
    return Namespace(**values)


def test_main_requires_firmware_key_and_admin_credentials(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        dashboard,
        "parse_args",
        lambda: _dashboard_args(tmp_path, firmware_download_key=None),
    )
    with pytest.raises(SystemExit, match="FIRMWARE_DOWNLOAD_KEY"):
        dashboard.main()

    monkeypatch.setattr(
        dashboard,
        "parse_args",
        lambda: _dashboard_args(tmp_path, username=None),
    )
    with pytest.raises(SystemExit, match="DASHBOARD_USERNAME"):
        dashboard.main()


def test_main_configures_handler_and_closes_server(monkeypatch, tmp_path, capsys) -> None:
    args = _dashboard_args(tmp_path)
    closed = []

    class FakeServer:
        def __init__(self, address, handler):
            assert address == ("127.0.0.1", 0)
            assert handler is Handler

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            closed.append(True)

    monkeypatch.setattr(dashboard, "parse_args", lambda: args)
    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", FakeServer)

    dashboard.main()

    assert Handler.db_path == args.db
    assert Handler.allow_unauthenticated_read is True
    assert closed == [True]
    output = capsys.readouterr().out
    assert "Dashboard listening" in output
    assert "Dashboard stopped" in output
