import base64
import json
import threading
from contextlib import closing
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from iot_home.dashboard import Handler, basic_request_authorized, firmware_request_authorized, page
from iot_home.db import connect, init_db
from iot_home.locations import load_locations


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
        for url in (base_url, f"{base_url}?key=wrong-key", f"{base_url}?key=correct-key&key=duplicate"):
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

    handler.log_message('%s %s %s', "request with secret", "200", "-")

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
            body = json.dumps({"deviceId": device_id, "location": f"Location {device_id}"}).encode("utf-8")
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

        workers = [threading.Thread(target=save, args=(f"esp32-{index:012x}",)) for index in range(8)]
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
