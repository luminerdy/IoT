#!/usr/bin/env bash
set -euo pipefail

project_dir="/home/scotty/IoT"
service_dir="${project_dir}/deploy/systemd"
env_dir="/etc/iot-home"
env_file="${env_dir}/iot-home.env"

if [[ ! -d "${project_dir}" ]]; then
  echo "Project directory not found: ${project_dir}" >&2
  exit 1
fi

mqtt_username="${MQTT_USERNAME:-iot}"
mqtt_password="${MQTT_PASSWORD:-}"
dashboard_username="${DASHBOARD_USERNAME:-}"
dashboard_password="${DASHBOARD_PASSWORD:-}"

if [[ -z "${mqtt_password}" && -f "${project_dir}/firmware/include/secrets.h" ]]; then
  mqtt_password="$(
    awk -F'"' '/MQTT_PASSWORD/ {print $2; exit}' "${project_dir}/firmware/include/secrets.h"
  )"
fi

if [[ -z "${mqtt_password}" ]]; then
  echo "MQTT_PASSWORD is required. Export it or add firmware/include/secrets.h first." >&2
  exit 1
fi

sudo install -d -o root -g root -m 0755 "${env_dir}"
tmp_env="$(mktemp)"
{
  printf 'MQTT_USERNAME=%q\n' "${mqtt_username}"
  printf 'MQTT_PASSWORD=%q\n' "${mqtt_password}"
  if [[ -n "${dashboard_username}" || -n "${dashboard_password}" ]]; then
    if [[ -z "${dashboard_username}" || -z "${dashboard_password}" ]]; then
      echo "DASHBOARD_USERNAME and DASHBOARD_PASSWORD must be set together." >&2
      exit 1
    fi
    printf 'DASHBOARD_USERNAME=%q\n' "${dashboard_username}"
    printf 'DASHBOARD_PASSWORD=%q\n' "${dashboard_password}"
  fi
} > "${tmp_env}"
sudo install -o root -g root -m 0600 "${tmp_env}" "${env_file}"
rm -f "${tmp_env}"

sudo install -o root -g root -m 0644 \
  "${service_dir}/iot-home-collector.service" \
  /etc/systemd/system/iot-home-collector.service
sudo install -o root -g root -m 0644 \
  "${service_dir}/iot-home-dashboard.service" \
  /etc/systemd/system/iot-home-dashboard.service

sudo systemctl daemon-reload
sudo systemctl enable --now iot-home-collector.service iot-home-dashboard.service

sudo systemctl --no-pager --full status iot-home-collector.service iot-home-dashboard.service
