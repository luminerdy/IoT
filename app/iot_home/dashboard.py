from __future__ import annotations

import argparse
import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import UTC, datetime

from iot_home.db import DEFAULT_DB_PATH, connect, init_db, latest_readings
from iot_home.locations import DEFAULT_LOCATIONS_PATH, load_locations, mapped_location


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the local IoT dashboard.")
    parser.add_argument("--host", default="localhost", help="HTTP bind host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path.")
    parser.add_argument(
        "--locations",
        type=Path,
        default=DEFAULT_LOCATIONS_PATH,
        help="JSON file mapping device IDs to display locations.",
    )
    parser.add_argument(
        "--stale-seconds",
        type=int,
        default=120,
        help="Mark online devices stale when last_seen is older than this many seconds.",
    )
    return parser.parse_args()


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def row_to_dict(row, stale_seconds: int, locations: dict[str, str]) -> dict:
    last_seen = parse_utc(row["last_seen"])
    age_seconds = None
    if last_seen:
        age_seconds = int((datetime.now(UTC) - last_seen).total_seconds())
    is_stale = bool(row["online"]) and age_seconds is not None and age_seconds > stale_seconds

    device_id = row["device_id"]

    return {
        "deviceId": device_id,
        "location": mapped_location(device_id, row["location"], locations),
        "firmwareVersion": row["firmware_version"],
        "lastSeen": row["last_seen"],
        "online": bool(row["online"]),
        "stale": is_stale,
        "ageSeconds": age_seconds,
        "rssi": row["last_rssi"],
        "status": row["last_status"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "sensorType": row["sensor_type"],
        "seq": row["seq"],
        "updatedAt": row["updated_at"],
    }


def page() -> bytes:
    return b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IoT Home Monitor</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      background: #f6f7f9;
      color: #17202a;
    }
    body {
      margin: 0;
      padding: 24px;
    }
    main {
      max-width: 1100px;
      margin: 0 auto;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 20px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
    }
    .muted {
      color: #5d6d7e;
      font-size: 14px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      border: 1px solid #d9dee5;
      border-radius: 8px;
      overflow: hidden;
    }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid #e7ebf0;
      text-align: left;
      white-space: nowrap;
    }
    th {
      background: #eef2f6;
      font-size: 13px;
      text-transform: uppercase;
      color: #4b5b6b;
    }
    tr:last-child td {
      border-bottom: 0;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 700;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #95a5a6;
    }
    .online .dot {
      background: #208a4b;
    }
    .offline .dot {
      background: #b03a2e;
    }
    .stale .dot {
      background: #b7791f;
    }
    @media (max-width: 760px) {
      body {
        padding: 12px;
      }
      header {
        display: block;
      }
      table {
        display: block;
        overflow-x: auto;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>IoT Home Monitor</h1>
        <div class="muted">Local readings from MQTT and SQLite</div>
      </div>
      <div class="muted" id="last-refresh">Waiting for data</div>
    </header>
    <table>
      <thead>
        <tr>
          <th>Location</th>
          <th>Status</th>
          <th>Temperature</th>
          <th>Humidity</th>
          <th>RSSI</th>
          <th>Last Seen</th>
          <th>Device</th>
        </tr>
      </thead>
      <tbody id="readings">
        <tr><td colspan="7">No readings yet.</td></tr>
      </tbody>
    </table>
  </main>
  <script>
    function fmt(value, suffix) {
      if (value === null || value === undefined) return "";
      return `${value}${suffix}`;
    }

    function render(rows) {
      const body = document.getElementById("readings");
      if (!rows.length) {
        body.innerHTML = '<tr><td colspan="7">No readings yet.</td></tr>';
        return;
      }
      body.innerHTML = rows.map((row) => {
        const stateClass = row.stale ? "stale" : (row.online ? "online" : "offline");
        const stateText = row.stale ? "Stale" : (row.online ? "Online" : "Offline");
        return `<tr>
          <td>${row.location}</td>
          <td><span class="status ${stateClass}"><span class="dot"></span>${stateText}</span></td>
          <td>${fmt(row.temperature, " F")}</td>
          <td>${fmt(row.humidity, "%")}</td>
          <td>${fmt(row.rssi, " dBm")}</td>
          <td>${row.lastSeen || ""}</td>
          <td>${row.deviceId}</td>
        </tr>`;
      }).join("");
    }

    async function refresh() {
      const response = await fetch("/api/latest", {cache: "no-store"});
      const rows = await response.json();
      render(rows);
      document.getElementById("last-refresh").textContent = `Updated ${new Date().toLocaleTimeString()}`;
    }

    refresh();
    setInterval(refresh, 3000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    db_path: Path = DEFAULT_DB_PATH
    stale_seconds: int = 120
    locations: dict[str, str] = {}

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page())
            return

        if self.path == "/api/latest":
            with connect(self.db_path) as conn:
                init_db(conn)
                rows = [
                    row_to_dict(row, self.stale_seconds, self.locations)
                    for row in latest_readings(conn)
                ]
            payload = json.dumps(rows).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_error(404)

    def log_message(self, format: str, *args) -> None:
        safe_path = escape(self.path)
        print(f"{self.address_string()} {self.command} {safe_path} {args}")


def main() -> None:
    args = parse_args()
    with connect(args.db) as conn:
        init_db(conn)

    Handler.db_path = args.db
    Handler.stale_seconds = args.stale_seconds
    Handler.locations = load_locations(args.locations)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Dashboard listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dashboard stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
