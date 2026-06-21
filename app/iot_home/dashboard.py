from __future__ import annotations

import argparse
import json
import mimetypes
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import UTC, datetime
from urllib.parse import parse_qs, unquote, urlparse

from iot_home.db import DEFAULT_DB_PATH, connect, init_db, latest_readings, reading_history
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
        default=1200,
        help="Mark online devices stale when last_seen is older than this many seconds.",
    )
    parser.add_argument(
        "--firmware-dir",
        type=Path,
        default=Path("data/firmware"),
        help="Directory served under /firmware/ for local OTA downloads.",
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


def history_row_to_dict(row) -> dict:
    return {
        "deviceId": row["device_id"],
        "location": row["location"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "rssi": row["rssi"],
        "status": row["status"],
        "seq": row["seq"],
        "datetime": row["datetime"],
        "createdAt": row["created_at"],
    }


def query_int(query: dict[str, list[str]], name: str, default: int) -> int:
    try:
        return int(query.get(name, [str(default)])[0])
    except (TypeError, ValueError):
        return default


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
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f6f8;
      color: #17202a;
      --panel: #ffffff;
      --ink-soft: #53616f;
      --line: #dbe2ea;
      --green: #16803f;
      --amber: #b7791f;
      --red: #b42318;
      --blue: #1f6feb;
      --teal: #0f766e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
    }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 32px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0;
      font-size: 30px;
      line-height: 1.1;
      font-weight: 750;
      letter-spacing: 0;
    }
    .muted {
      color: var(--ink-soft);
      font-size: 14px;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: #24313d;
      font-size: 13px;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      gap: 14px;
    }
    .summary {
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 18px;
    }
    .stat, .device, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
    }
    .stat {
      padding: 14px;
      min-height: 92px;
    }
    .label {
      color: var(--ink-soft);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .value {
      margin-top: 8px;
      font-size: 30px;
      line-height: 1;
      font-weight: 760;
    }
    .subvalue {
      margin-top: 8px;
      color: var(--ink-soft);
      font-size: 13px;
    }
    .devices {
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      margin-bottom: 18px;
    }
    .device {
      padding: 14px;
      min-height: 170px;
    }
    .device-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 14px;
    }
    .device h2 {
      margin: 0;
      font-size: 17px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .metrics {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .metric {
      min-height: 58px;
      padding: 10px;
      border: 1px solid #e5ebf2;
      border-radius: 6px;
      background: #f8fafc;
    }
    .metric strong {
      display: block;
      margin-top: 4px;
      font-size: 20px;
      line-height: 1.1;
    }
    .panel {
      overflow: hidden;
      margin-top: 18px;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px;
      border-bottom: 1px solid var(--line);
    }
    .panel-head h2 {
      margin: 0;
      font-size: 16px;
      letter-spacing: 0;
    }
    .chart-wrap {
      min-height: 220px;
      padding: 14px;
    }
    #trend {
      width: 100%;
      height: 210px;
      display: block;
    }
    .axis {
      stroke: #d8e0e8;
      stroke-width: 1;
    }
    .temp-line {
      fill: none;
      stroke: var(--red);
      stroke-width: 3;
    }
    .humidity-line {
      fill: none;
      stroke: var(--teal);
      stroke-width: 3;
    }
    .legend {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      color: var(--ink-soft);
      font-size: 13px;
    }
    .key {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .swatch {
      width: 18px;
      height: 3px;
      border-radius: 999px;
      background: currentColor;
    }
    .temp-key { color: var(--red); }
    .humidity-key { color: var(--teal); }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid #e7ebf0;
      text-align: left;
      white-space: nowrap;
    }
    th {
      background: #f0f4f8;
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
      flex: 0 0 auto;
    }
    .online .dot { background: var(--green); }
    .offline .dot { background: var(--red); }
    .stale .dot { background: var(--amber); }
    .empty {
      padding: 28px 14px;
      color: var(--ink-soft);
      text-align: center;
    }
    .table-wrap {
      overflow-x: auto;
    }
    .error {
      border-color: #f0b4ad;
      background: #fff7f5;
      color: #8f1d13;
    }
    @media (max-width: 860px) {
      header {
        align-items: flex-start;
        flex-direction: column;
      }
      .toolbar {
        justify-content: flex-start;
      }
      .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 560px) {
      main {
        width: min(100% - 20px, 1180px);
        padding-top: 14px;
      }
      h1 {
        font-size: 25px;
      }
      .summary, .metrics {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>IoT Home Monitor</h1>
        <div class="muted">Live local readings from MQTT and SQLite</div>
      </div>
      <div class="toolbar">
        <span class="pill" id="connection"><span class="dot"></span> Connecting</span>
        <span class="pill" id="last-refresh">Waiting for data</span>
      </div>
    </header>
    <section class="grid summary" aria-label="Dashboard summary">
      <div class="stat">
        <div class="label">Devices</div>
        <div class="value" id="device-count">0</div>
        <div class="subvalue" id="online-count">0 online</div>
      </div>
      <div class="stat">
        <div class="label">Average Temp</div>
        <div class="value" id="avg-temp">--</div>
        <div class="subvalue">Latest device readings</div>
      </div>
      <div class="stat">
        <div class="label">Average Humidity</div>
        <div class="value" id="avg-humidity">--</div>
        <div class="subvalue">Latest device readings</div>
      </div>
      <div class="stat">
        <div class="label">Signal</div>
        <div class="value" id="avg-rssi">--</div>
        <div class="subvalue">Average RSSI</div>
      </div>
    </section>

    <section class="grid devices" id="devices" aria-label="Devices"></section>

    <section class="panel" aria-label="24 hour trend">
      <div class="panel-head">
        <h2>24 Hour Trend</h2>
        <div class="legend">
          <span class="key temp-key"><span class="swatch"></span>Temperature</span>
          <span class="key humidity-key"><span class="swatch"></span>Humidity</span>
        </div>
      </div>
      <div class="chart-wrap">
        <svg id="trend" viewBox="0 0 900 210" role="img" aria-label="Temperature and humidity trend"></svg>
      </div>
    </section>

    <section class="panel" aria-label="Latest readings">
      <div class="panel-head">
        <h2>Latest Readings</h2>
        <span class="muted" id="history-count">No history loaded</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Location</th>
              <th>Status</th>
              <th>Temperature</th>
              <th>Humidity</th>
              <th>RSSI</th>
              <th>Last Seen</th>
              <th>Firmware</th>
              <th>Device</th>
            </tr>
          </thead>
          <tbody id="readings">
            <tr><td colspan="8" class="empty">No readings yet.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const state = {latest: [], history: []};

    function fmt(value, suffix = "") {
      if (value === null || value === undefined || Number.isNaN(value)) return "--";
      if (typeof value === "number") return `${Math.round(value * 10) / 10}${suffix}`;
      return `${value}${suffix}`;
    }

    function relativeTime(value) {
      if (!value) return "--";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
      if (seconds < 60) return `${seconds}s ago`;
      const minutes = Math.round(seconds / 60);
      if (minutes < 60) return `${minutes}m ago`;
      const hours = Math.round(minutes / 60);
      if (hours < 48) return `${hours}h ago`;
      return date.toLocaleString();
    }

    function setText(id, value) {
      document.getElementById(id).textContent = value;
    }

    function average(rows, key) {
      const values = rows.map((row) => row[key]).filter((value) => typeof value === "number");
      if (!values.length) return null;
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }

    function deviceState(row) {
      if (row.stale) return ["stale", "Stale"];
      if (row.online) return ["online", "Online"];
      return ["offline", "Offline"];
    }

    function renderSummary(rows) {
      const online = rows.filter((row) => row.online && !row.stale).length;
      const stale = rows.filter((row) => row.stale).length;
      setText("device-count", rows.length);
      setText("online-count", `${online} online${stale ? `, ${stale} stale` : ""}`);
      setText("avg-temp", average(rows, "temperature") === null ? "--" : fmt(average(rows, "temperature"), " F"));
      setText("avg-humidity", average(rows, "humidity") === null ? "--" : fmt(average(rows, "humidity"), "%"));
      setText("avg-rssi", average(rows, "rssi") === null ? "--" : fmt(average(rows, "rssi"), " dBm"));
    }

    function renderDevices(rows) {
      const devices = document.getElementById("devices");
      devices.replaceChildren();
      if (!rows.length) {
        const empty = document.createElement("div");
        empty.className = "device empty";
        empty.textContent = "No devices have reported yet.";
        devices.appendChild(empty);
        return;
      }

      for (const row of rows) {
        const [stateClass, stateText] = deviceState(row);
        const card = document.createElement("article");
        card.className = "device";

        const head = document.createElement("div");
        head.className = "device-head";
        const titleBlock = document.createElement("div");
        const title = document.createElement("h2");
        title.textContent = row.location || row.deviceId;
        const device = document.createElement("div");
        device.className = "muted";
        device.textContent = row.deviceId;
        titleBlock.append(title, device);

        const status = document.createElement("span");
        status.className = `status ${stateClass}`;
        const dot = document.createElement("span");
        dot.className = "dot";
        status.append(dot, document.createTextNode(stateText));
        head.append(titleBlock, status);

        const metrics = document.createElement("div");
        metrics.className = "metrics";
        for (const [label, value] of [
          ["Temperature", fmt(row.temperature, " F")],
          ["Humidity", fmt(row.humidity, "%")],
          ["RSSI", fmt(row.rssi, " dBm")],
          ["Seen", relativeTime(row.lastSeen)],
        ]) {
          const metric = document.createElement("div");
          metric.className = "metric";
          const metricLabel = document.createElement("div");
          metricLabel.className = "label";
          metricLabel.textContent = label;
          const metricValue = document.createElement("strong");
          metricValue.textContent = value;
          metric.append(metricLabel, metricValue);
          metrics.appendChild(metric);
        }

        card.append(head, metrics);
        devices.appendChild(card);
      }
    }

    function render(rows) {
      const body = document.getElementById("readings");
      if (!rows.length) {
        body.innerHTML = '<tr><td colspan="8" class="empty">No readings yet.</td></tr>';
        return;
      }
      body.replaceChildren();
      for (const row of rows) {
        const [stateClass, stateText] = deviceState(row);
        const tr = document.createElement("tr");
        const cells = [
          row.location || row.deviceId,
          stateText,
          fmt(row.temperature, " F"),
          fmt(row.humidity, "%"),
          fmt(row.rssi, " dBm"),
          relativeTime(row.lastSeen),
          row.firmwareVersion || "--",
          row.deviceId,
        ];
        cells.forEach((value, index) => {
          const td = document.createElement("td");
          if (index === 1) {
            const status = document.createElement("span");
            status.className = `status ${stateClass}`;
            const dot = document.createElement("span");
            dot.className = "dot";
            status.append(dot, document.createTextNode(value));
            td.appendChild(status);
          } else {
            td.textContent = value;
          }
          tr.appendChild(td);
        });
        body.appendChild(tr);
      }
    }

    function points(rows, key, min, max) {
      if (!rows.length || min === max) return "";
      const sorted = [...rows].reverse();
      const start = new Date(sorted[0].createdAt || sorted[0].datetime).getTime();
      const end = new Date(sorted[sorted.length - 1].createdAt || sorted[sorted.length - 1].datetime).getTime();
      const span = Math.max(1, end - start);
      return sorted
        .filter((row) => typeof row[key] === "number")
        .map((row) => {
          const time = new Date(row.createdAt || row.datetime).getTime();
          const x = 36 + ((time - start) / span) * 828;
          const y = 176 - ((row[key] - min) / (max - min)) * 140;
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
    }

    function renderTrend(rows) {
      const svg = document.getElementById("trend");
      svg.replaceChildren();
      const grid = document.createElementNS("http://www.w3.org/2000/svg", "path");
      grid.setAttribute("class", "axis");
      grid.setAttribute("d", "M36 36H864M36 106H864M36 176H864");
      svg.appendChild(grid);
      if (rows.length < 2) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", "450");
        text.setAttribute("y", "108");
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("fill", "#53616f");
        text.textContent = "Trend appears after more readings arrive";
        svg.appendChild(text);
        setText("history-count", `${rows.length} reading${rows.length === 1 ? "" : "s"}`);
        return;
      }
      const temps = rows.map((row) => row.temperature).filter((value) => typeof value === "number");
      const humidity = rows.map((row) => row.humidity).filter((value) => typeof value === "number");
      const min = Math.min(...temps, ...humidity);
      const max = Math.max(...temps, ...humidity);
      for (const [className, key] of [["temp-line", "temperature"], ["humidity-line", "humidity"]]) {
        const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        line.setAttribute("class", className);
        line.setAttribute("points", points(rows, key, min, max));
        svg.appendChild(line);
      }
      setText("history-count", `${rows.length} readings in 24h`);
    }

    function setConnection(ok, message) {
      const el = document.getElementById("connection");
      el.className = ok ? "pill online" : "pill offline error";
      el.replaceChildren();
      const dot = document.createElement("span");
      dot.className = "dot";
      el.append(dot, document.createTextNode(message));
    }

    async function refresh() {
      try {
        const [latestResponse, historyResponse] = await Promise.all([
          fetch("/api/latest", {cache: "no-store"}),
          fetch("/api/history?hours=24&limit=600", {cache: "no-store"}),
        ]);
        if (!latestResponse.ok || !historyResponse.ok) throw new Error("Dashboard API request failed");
        state.latest = await latestResponse.json();
        state.history = await historyResponse.json();
        renderSummary(state.latest);
        renderDevices(state.latest);
        render(state.latest);
        renderTrend(state.history);
        setConnection(true, "Live");
        document.getElementById("last-refresh").textContent = `Updated ${new Date().toLocaleTimeString()}`;
      } catch (error) {
        setConnection(false, "Disconnected");
        document.getElementById("last-refresh").textContent = error.message;
      }
    }

    refresh();
    setInterval(refresh, 3000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    db_path: Path = DEFAULT_DB_PATH
    firmware_dir: Path = Path("data/firmware")
    stale_seconds: int = 120
    locations_path: Path = DEFAULT_LOCATIONS_PATH
    locations: dict[str, str] = {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parsed_path = parsed.path

        if parsed_path == "/" or parsed_path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page())
            return

        if parsed_path.startswith("/firmware/"):
            self.serve_firmware(parsed_path)
            return

        if parsed_path == "/api/latest":
            self.locations = load_locations(self.locations_path)
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

        if parsed_path == "/api/history":
            query = parse_qs(parsed.query)
            hours = query_int(query, "hours", 24)
            limit = query_int(query, "limit", 500)
            with connect(self.db_path) as conn:
                init_db(conn)
                rows = [history_row_to_dict(row) for row in reading_history(conn, hours, limit)]
            payload = json.dumps(rows).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_error(404)

    def serve_firmware(self, parsed_path: str) -> None:
        relative = unquote(parsed_path.removeprefix("/firmware/"))
        parts = Path(relative).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            self.send_error(404)
            return

        firmware_root = self.firmware_dir.resolve()
        firmware_path = firmware_root.joinpath(*parts).resolve()
        if not firmware_path.is_relative_to(firmware_root) or not firmware_path.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(firmware_path.name)[0] or "application/octet-stream"
        content = firmware_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        safe_path = escape(self.path)
        print(f"{self.address_string()} {self.command} {safe_path} {args}")


def main() -> None:
    args = parse_args()
    with connect(args.db) as conn:
        init_db(conn)

    Handler.db_path = args.db
    Handler.firmware_dir = args.firmware_dir
    Handler.locations_path = args.locations
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
