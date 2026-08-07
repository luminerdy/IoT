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
firmware_download_key="${FIRMWARE_DOWNLOAD_KEY:-}"
dashboard_username="${DASHBOARD_USERNAME:-}"
dashboard_password="${DASHBOARD_PASSWORD:-}"

if [[ -z "${firmware_download_key}" && -f "${env_file}" ]]; then
  firmware_download_key="$(sudo sed -n 's/^FIRMWARE_DOWNLOAD_KEY=//p' "${env_file}" | head -n 1)"
fi

if [[ -f "${env_file}" ]]; then
  if [[ -z "${dashboard_username}" ]]; then
    dashboard_username="$(sudo sed -n 's/^DASHBOARD_USERNAME=//p' "${env_file}" | head -n 1)"
  fi
  if [[ -z "${dashboard_password}" ]]; then
    dashboard_password="$(sudo sed -n 's/^DASHBOARD_PASSWORD=//p' "${env_file}" | head -n 1)"
  fi
fi

if [[ -z "${firmware_download_key}" ]]; then
  firmware_download_key="$(openssl rand -hex 32)"
fi

if [[ -z "${dashboard_username}" ]]; then
  dashboard_username="iot-dashboard"
fi

if [[ -z "${dashboard_password}" ]]; then
  dashboard_password="$(openssl rand -hex 24)"
fi

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
  printf 'FIRMWARE_DOWNLOAD_KEY=%q\n' "${firmware_download_key}"
  printf 'DASHBOARD_USERNAME=%q\n' "${dashboard_username}"
  printf 'DASHBOARD_PASSWORD=%q\n' "${dashboard_password}"
} > "${tmp_env}"
sudo install -o root -g root -m 0600 "${tmp_env}" "${env_file}"

dashboard_credentials_dir="/home/scotty/.config/iot-home"
dashboard_credentials_file="${dashboard_credentials_dir}/dashboard-credentials.env"
sudo install -d -o scotty -g scotty -m 0700 "${dashboard_credentials_dir}"
tmp_dashboard_credentials="$(mktemp)"
{
  printf 'DASHBOARD_USERNAME=%q\n' "${dashboard_username}"
  printf 'DASHBOARD_PASSWORD=%q\n' "${dashboard_password}"
} > "${tmp_dashboard_credentials}"
sudo install -o scotty -g scotty -m 0600 "${tmp_dashboard_credentials}" "${dashboard_credentials_file}"
rm -f "${tmp_dashboard_credentials}"
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
