#!/usr/bin/env bash
set -u

report="/home/scotty/IoT/data/watchdog-morning-check-2026-08-05.txt"
{
  echo "Watchdog morning check"
  date --iso-8601=seconds
  echo
  echo "PiServer"
  hostname
  uptime -s
  systemctl is-active mosquitto.service iot-home-collector.service iot-home-dashboard.service
  curl -fsS --max-time 10 http://127.0.0.1:8000/api/latest >/dev/null \
    && echo "dashboard_api=healthy" \
    || echo "dashboard_api=unhealthy"
  echo
  echo "Pi3 monitor"
  ssh -o BatchMode=yes -o ConnectTimeout=10 pi-watchdog '
    hostname
    uptime -s
    systemctl is-enabled pi-watchdog.service
    systemctl is-active pi-watchdog.service
    (command -v pinctrl >/dev/null && pinctrl get 17) || (command -v raspi-gpio >/dev/null && raspi-gpio get 17) || true
    journalctl -u pi-watchdog.service --no-pager --since "2026-08-04 21:00:00" | grep -E "Watching|Failed check|Activating GPIO|Target power restored|Target recovered|Healthy" || true
  '
} >"$report" 2>&1
