#!/usr/bin/env bash
set -euo pipefail

username="${1:-iot}"

echo "Configuring Mosquitto LAN listener on port 1883 for user: ${username}"
read -rsp "MQTT password: " password
echo

tmp_config="$(mktemp)"
cat > "${tmp_config}" <<'CONFIG'
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
CONFIG

sudo install -o root -g root -m 0644 "${tmp_config}" /etc/mosquitto/conf.d/iot-local.conf
rm -f "${tmp_config}"

sudo mosquitto_passwd -b -c /etc/mosquitto/passwd "${username}" "${password}"
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo chmod 0640 /etc/mosquitto/passwd

sudo systemctl restart mosquitto
sudo systemctl --no-pager status mosquitto

echo
echo "Mosquitto LAN listener configured."
