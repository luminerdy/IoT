from __future__ import annotations

import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACL_PATH = PROJECT_ROOT / "deploy/mosquitto/iot-home-per-device.acl"
BROKER_BIN = shutil.which("mosquitto")
PASSWD_BIN = shutil.which("mosquitto_passwd")

DEVICE_A = "esp32-device-a"
DEVICE_B = "esp32-device-b"
COLLECTOR = "iot-collector"
ADMIN = "iot-admin"
PASSWORDS = {
    DEVICE_A: "test-password-a",
    DEVICE_B: "test-password-b",
    COLLECTOR: "test-password-collector",
    ADMIN: "test-password-admin",
}
TOPICS = [
    (device, kind, f"home/sensors/{device}/{suffix}")
    for device in (DEVICE_A, DEVICE_B)
    for kind, suffix in (
        ("telemetry", "telemetry"),
        ("status", "status"),
        ("response", "response"),
        ("ota-status", "ota/status"),
        ("config", "config"),
        ("command", "command"),
    )
]


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.fixture
def isolated_broker(tmp_path):
    if not BROKER_BIN or not PASSWD_BIN:
        pytest.skip("Mosquitto broker and password utility are required for the ACL matrix")

    password_path = tmp_path / "passwords"
    for index, (username, password) in enumerate(PASSWORDS.items()):
        command = [PASSWD_BIN, "-b"]
        if index == 0:
            command.append("-c")
        command.extend([str(password_path), username, password])
        subprocess.run(command, check=True, capture_output=True, text=True)

    port = _free_port()
    config_path = tmp_path / "mosquitto.conf"
    config_path.write_text(
        "\n".join(
            [
                f"listener {port} 127.0.0.1",
                "allow_anonymous false",
                f"password_file {password_path}",
                f"acl_file {ACL_PATH}",
                "persistence false",
                "log_dest stdout",
                "",
            ]
        ),
        encoding="utf-8",
    )
    broker = subprocess.Popen(
        [BROKER_BIN, "-c", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if broker.poll() is not None:
            output = broker.stdout.read() if broker.stdout else ""
            pytest.fail(f"isolated Mosquitto exited during startup:\n{output}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.05)
    else:
        broker.terminate()
        pytest.fail("isolated Mosquitto did not start within 5 seconds")

    try:
        yield port
    finally:
        broker.terminate()
        try:
            broker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            broker.kill()
            broker.wait(timeout=5)


class MqttTestClient:
    def __init__(self, username: str, port: int):
        self.username = username
        self.messages: set[str] = set()
        self.suback_codes: dict[int, list] = {}
        self.condition = threading.Condition()
        self.connected = threading.Event()
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"acl-matrix-{username}",
            protocol=mqtt.MQTTv5,
        )
        self.client.username_pw_set(username, PASSWORDS[username])
        self.client.on_connect = self._on_connect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message
        self.client.connect("127.0.0.1", port, keepalive=10)
        self.client.loop_start()
        assert self.connected.wait(3), f"{username} did not connect to isolated Mosquitto"

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        assert not reason_code.is_failure
        self.connected.set()

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        with self.condition:
            self.suback_codes[mid] = reason_codes
            self.condition.notify_all()

    def _on_message(self, client, userdata, message):
        with self.condition:
            self.messages.add(message.payload.decode("utf-8"))
            self.condition.notify_all()

    def subscribe(self, topic: str) -> bool:
        result, mid = self.client.subscribe(topic, qos=1)
        assert result == mqtt.MQTT_ERR_SUCCESS
        with self.condition:
            assert self.condition.wait_for(lambda: mid in self.suback_codes, timeout=3)
            reason_codes = self.suback_codes.pop(mid)
        return len(reason_codes) == 1 and not reason_codes[0].is_failure

    def publish(self, topic: str, payload: str) -> None:
        result = self.client.publish(topic, payload, qos=1, retain=False)
        result.wait_for_publish(timeout=3)

    def close(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()


def _read_allowed(username: str, device: str, kind: str) -> bool:
    if username == ADMIN:
        return True
    if username == COLLECTOR:
        return kind in {"telemetry", "status"}
    return username == device and kind in {"config", "command"}


def _write_allowed(username: str, device: str, kind: str) -> bool:
    if username == ADMIN:
        return True
    return username == device and kind in {"telemetry", "status", "response", "ota-status"}


def test_tls_installer_uses_tested_acl_without_replacing_interim_acl():
    script = (PROJECT_ROOT / "scripts/configure_mosquitto_tls_acl.sh").read_text(encoding="utf-8")

    assert 'acl_path="/etc/mosquitto/iot-home-per-device.acl"' in script
    assert 'acl_source="${script_dir}/../deploy/mosquitto/iot-home-per-device.acl"' in script
    assert "per_listener_settings true" in script


def test_broker_acl_matrix_enforces_device_collector_and_admin_roles(isolated_broker):
    clients = {
        username: MqttTestClient(username, isolated_broker)
        for username in (DEVICE_A, DEVICE_B, COLLECTOR, ADMIN)
    }
    try:
        for client in clients.values():
            for _, _, topic in TOPICS:
                client.subscribe(topic)
        assert clients[COLLECTOR].subscribe("home/sensors/+/telemetry") is True
        assert clients[COLLECTOR].subscribe("home/sensors/+/status") is True

        for client in clients.values():
            client.messages.clear()
        admin = clients[ADMIN]
        expected_reads = {username: set() for username in clients}
        for index, (device, kind, topic) in enumerate(TOPICS):
            payload = f"acl-read:{index}"
            admin.publish(topic, payload)
            for username in clients:
                if _read_allowed(username, device, kind):
                    expected_reads[username].add(payload)
        for username, client in clients.items():
            with client.condition:
                assert client.condition.wait_for(
                    lambda: expected_reads[username].issubset(client.messages), timeout=5
                )
            assert client.messages == expected_reads[username], (
                f"unexpected read delivery for {username}"
            )

        monitor = admin
        assert monitor.subscribe("home/#") is True
        monitor.messages.clear()
        expected_messages = set()
        for username, client in clients.items():
            for index, (device, kind, topic) in enumerate(TOPICS):
                payload = f"acl-matrix:{username}:{index}"
                client.publish(topic, payload)
                if _write_allowed(username, device, kind):
                    expected_messages.add(payload)

        with monitor.condition:
            assert monitor.condition.wait_for(
                lambda: expected_messages.issubset(monitor.messages), timeout=5
            )
        assert monitor.messages == expected_messages
    finally:
        for client in clients.values():
            client.close()
