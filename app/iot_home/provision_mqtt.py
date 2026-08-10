from __future__ import annotations

import argparse
import base64
import binascii
import getpass
import ipaddress
import json
import os
import re
import select
import ssl
import stat
import termios
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

DEVICE_ID_RE = re.compile(r"^esp32-[0-9a-f]{12}$")
HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
MIN_PASSWORD_LENGTH = 16
MAX_PASSWORD_LENGTH = 128
MAX_CA_CERT_LENGTH = 3072
MAX_PROFILE_JSON_LENGTH = 3900
USB_WRITE_CHUNK_SIZE = 64
USB_WRITE_PAUSE_SECONDS = 0.02
PROVISION_PREFIX = b"IOT_MQTT_PROVISION "
STATUS_COMMAND = b"IOT_MQTT_STATUS\n"
CLEAR_COMMAND = b"IOT_MQTT_CLEAR\n"
STATUS_MARKER = b"MQTT provisioning status:"
APPLIED_MARKER = b"MQTT provisioning applied; restarting"
REJECTED_MARKER = b"MQTT provisioning rejected:"
CLEARED_MARKER = b"MQTT provisioning cleared; restarting"
CLEAR_FAILED_MARKER = b"MQTT provisioning clear failed"


@dataclass(frozen=True)
class MqttProfile:
    device_id: str
    connect_host: str
    tls_hostname: str
    port: int
    password: str = field(repr=False)
    ca_cert: str = field(repr=False)

    def as_json(self) -> str:
        payload = json.dumps(
            {
                "schemaVersion": 2,
                "mqttConnectHost": self.connect_host,
                "mqttTlsHostname": self.tls_hostname,
                "mqttPort": self.port,
                "mqttUsername": self.device_id,
                "mqttPassword": self.password,
                "mqttUseTls": True,
                "mqttCaCert": self.ca_cert,
            },
            separators=(",", ":"),
        )
        if len(payload.encode("utf-8")) > MAX_PROFILE_JSON_LENGTH:
            raise ValueError("provisioning profile is too large")
        return payload


class SerialChannel(Protocol):
    def write(self, payload: bytes) -> None: ...

    def wait_for(self, markers: tuple[bytes, ...], timeout: float) -> bytes: ...


class UsbSerialChannel:
    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None
        self.buffer = b""

    def __enter__(self) -> UsbSerialChannel:
        self.fd = os.open(self.path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attributes = termios.tcgetattr(self.fd)
        attributes[0] = 0
        attributes[1] = 0
        attributes[2] = termios.CLOCAL | termios.CREAD | termios.CS8
        attributes[3] = 0
        attributes[4] = termios.B115200
        attributes[5] = termios.B115200
        attributes[6][termios.VMIN] = 0
        attributes[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
        termios.tcflush(self.fd, termios.TCIFLUSH)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def write(self, payload: bytes) -> None:
        if self.fd is None:
            raise RuntimeError("serial channel is not open")
        view = memoryview(payload)
        while view:
            written = os.write(self.fd, view[:USB_WRITE_CHUNK_SIZE])
            view = view[written:]
            termios.tcdrain(self.fd)
            if view:
                time.sleep(USB_WRITE_PAUSE_SECONDS)

    def wait_for(self, markers: tuple[bytes, ...], timeout: float) -> bytes:
        if self.fd is None:
            raise RuntimeError("serial channel is not open")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            readable, _, _ = select.select([self.fd], [], [], min(0.2, remaining))
            if readable:
                chunk = os.read(self.fd, 4096)
                self.buffer = (self.buffer + chunk)[-16384:]
                for marker in markers:
                    if marker in self.buffer:
                        return marker
        raise TimeoutError("timed out waiting for the USB provisioning response")


def normalize_ca_certificate(value: str) -> str:
    normalized = value.replace("\r\n", "\n").rstrip("\n") + "\n"
    if len(normalized.encode("utf-8")) > MAX_CA_CERT_LENGTH:
        raise ValueError("CA certificate is too large")
    if not normalized.startswith("-----BEGIN CERTIFICATE-----\n") or not normalized.endswith(
        "\n-----END CERTIFICATE-----\n"
    ):
        raise ValueError("CA certificate must be one PEM certificate")
    body = "".join(normalized.splitlines()[1:-1])
    try:
        decoded = base64.b64decode(body, validate=True)
        ssl.PEM_cert_to_DER_cert(normalized)
    except (binascii.Error, ValueError) as error:
        raise ValueError("CA certificate PEM is invalid") from error
    if not decoded:
        raise ValueError("CA certificate PEM is invalid")
    return normalized


def read_password_file(path: Path) -> str:
    file_stat = path.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("password path must be a regular file")
    if file_stat.st_mode & 0o077:
        raise ValueError("password file permissions must be 0600 or stricter")
    password = path.read_text(encoding="utf-8").rstrip("\r\n")
    return validate_password(password)


def validate_password(password: str) -> str:
    if "\n" in password or "\r" in password:
        raise ValueError("MQTT password must be a single line")
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("MQTT password must be 16 to 128 characters")
    if any(ord(character) < 33 or ord(character) > 126 for character in password):
        raise ValueError("MQTT password must contain printable ASCII without spaces")
    return password


def validate_connect_host(host: str) -> str:
    if not HOST_RE.fullmatch(host):
        raise ValueError("MQTT connect host must be a hostname or IP address without a scheme")
    return host


def validate_tls_hostname(hostname: str) -> str:
    if not HOST_RE.fullmatch(hostname):
        raise ValueError("MQTT TLS hostname must be a DNS hostname without a scheme")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("MQTT TLS hostname must be a DNS hostname for certificate validation")
    if "." not in hostname or not any(character.isalpha() for character in hostname):
        raise ValueError("MQTT TLS hostname must be a DNS hostname for certificate validation")
    return hostname


def build_profile(
    *,
    device_id: str,
    connect_host: str,
    tls_hostname: str,
    port: int,
    password: str,
    ca_cert: str,
) -> MqttProfile:
    if not DEVICE_ID_RE.fullmatch(device_id):
        raise ValueError("device ID must match esp32- followed by 12 lowercase hex characters")
    if not 1 <= port <= 65535:
        raise ValueError("MQTT port must be between 1 and 65535")
    return MqttProfile(
        device_id=device_id,
        connect_host=validate_connect_host(connect_host),
        tls_hostname=validate_tls_hostname(tls_hostname),
        port=port,
        password=validate_password(password),
        ca_cert=normalize_ca_certificate(ca_cert),
    )


def wait_until_ready(channel: SerialChannel, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        channel.write(STATUS_COMMAND)
        try:
            channel.wait_for((STATUS_MARKER,), min(1.0, max(0.1, deadline - time.monotonic())))
            return
        except TimeoutError:
            continue
    raise TimeoutError("USB device did not expose the MQTT provisioning channel")


def provision(channel: SerialChannel, profile: MqttProfile, timeout: float) -> None:
    wait_until_ready(channel, timeout)
    command = PROVISION_PREFIX + profile.as_json().encode("utf-8") + b"\n"
    channel.write(command)
    result = channel.wait_for((APPLIED_MARKER, REJECTED_MARKER), timeout)
    if result != APPLIED_MARKER:
        raise RuntimeError("device rejected the MQTT provisioning profile")


def clear(channel: SerialChannel, timeout: float) -> None:
    wait_until_ready(channel, timeout)
    channel.write(CLEAR_COMMAND)
    result = channel.wait_for((CLEARED_MARKER, CLEAR_FAILED_MARKER), timeout)
    if result != CLEARED_MARKER:
        raise RuntimeError("device could not clear the MQTT provisioning profile")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision a per-device MQTT TLS profile into ESP32 NVS over USB."
    )
    parser.add_argument("--serial-port", type=Path, default=Path("/dev/ttyUSB0"))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--device-id")
    parser.add_argument(
        "--connect-host",
        help="Resolvable TCP endpoint for the MQTT broker; may be an IP address.",
    )
    parser.add_argument(
        "--tls-hostname",
        help="DNS name verified against the broker certificate SAN and used for TLS SNI.",
    )
    parser.add_argument("--host", help=argparse.SUPPRESS)
    parser.add_argument("--mqtt-port", type=int, default=8883)
    parser.add_argument("--ca-cert", type=Path)
    parser.add_argument(
        "--password-file",
        type=Path,
        help="Mode-0600 file containing the MQTT password; otherwise prompt securely.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.clear and args.status:
        raise SystemExit("choose only one of --clear or --status")

    with UsbSerialChannel(args.serial_port) as channel:
        if args.status:
            wait_until_ready(channel, args.timeout)
            print("MQTT provisioning channel is ready")
            return 0
        if args.clear:
            clear(channel, args.timeout)
            print("MQTT provisioning profile cleared; device is restarting")
            return 0

        connect_host = args.connect_host or args.host
        tls_hostname = args.tls_hostname or args.host
        if not args.device_id or not connect_host or not tls_hostname or not args.ca_cert:
            raise SystemExit(
                "provisioning requires --device-id, --connect-host, --tls-hostname, "
                "and --ca-cert"
            )
        password = (
            read_password_file(args.password_file)
            if args.password_file
            else validate_password(getpass.getpass("Per-device MQTT password: "))
        )
        profile = build_profile(
            device_id=args.device_id,
            connect_host=connect_host,
            tls_hostname=tls_hostname,
            port=args.mqtt_port,
            password=password,
            ca_cert=args.ca_cert.read_text(encoding="utf-8"),
        )
        provision(channel, profile, args.timeout)
        print("Per-device MQTT TLS profile stored in NVS; device is restarting")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
