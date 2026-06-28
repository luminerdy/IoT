#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <device-id-or-admin-user>" >&2
  exit 2
fi

username="$1"

read -rsp "MQTT password for ${username}: " password
echo

if [[ ! -f /etc/mosquitto/passwd ]]; then
  sudo install -o root -g mosquitto -m 0640 /dev/null /etc/mosquitto/passwd
fi

sudo mosquitto_passwd -b /etc/mosquitto/passwd "${username}" "${password}"
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo chmod 0640 /etc/mosquitto/passwd
sudo systemctl reload mosquitto

echo "MQTT user added or updated: ${username}"
