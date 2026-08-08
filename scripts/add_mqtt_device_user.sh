#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <device-id-or-admin-user>" >&2
  exit 2
fi

username="$1"

if [[ ! -f /etc/mosquitto/passwd ]]; then
  sudo install -o root -g mosquitto -m 0640 /dev/null /etc/mosquitto/passwd
fi

# Let mosquitto_passwd read the password directly from the terminal. Do not use
# batch mode: it places the plaintext password in the process argument list.
sudo mosquitto_passwd /etc/mosquitto/passwd "${username}"
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo chmod 0640 /etc/mosquitto/passwd
sudo systemctl reload mosquitto

echo "MQTT user added or updated: ${username}"
