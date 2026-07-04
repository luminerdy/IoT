#!/usr/bin/env bash
set -euo pipefail

device_user="${1:-iot}"
admin_user="${2:-iot-admin}"
acl_path="/etc/mosquitto/aclfile"

echo "Configuring Mosquitto LAN listener on port 1883"
echo "Fleet/collector user: ${device_user}"
echo "Admin publisher user: ${admin_user}"
read -rsp "MQTT password for ${device_user}: " device_password
echo
read -rsp "MQTT password for ${admin_user}: " admin_password
echo

tmp_config="$(mktemp)"
cat > "${tmp_config}" <<CONFIG
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file ${acl_path}
CONFIG

sudo install -o root -g root -m 0644 "${tmp_config}" /etc/mosquitto/conf.d/iot-local.conf
rm -f "${tmp_config}"

tmp_acl="$(mktemp)"
cat > "${tmp_acl}" <<ACL
# Shared current-fleet user. Allows telemetry/status flow but blocks publishing
# retained runtime config and OTA commands.
user ${device_user}
topic readwrite home/sensors/+/telemetry
topic readwrite home/sensors/+/status
topic readwrite home/sensors/+/response
topic readwrite home/sensors/+/ota/status
topic read home/sensors/+/config
topic read home/sensors/+/command

# Pi-side operator tools use this account for config and OTA commands.
user ${admin_user}
topic readwrite home/#
ACL

sudo install -o root -g mosquitto -m 0640 "${tmp_acl}" "${acl_path}"
rm -f "${tmp_acl}"

sudo mosquitto_passwd -b -c /etc/mosquitto/passwd "${device_user}" "${device_password}"
sudo mosquitto_passwd -b /etc/mosquitto/passwd "${admin_user}" "${admin_password}"
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo chmod 0640 /etc/mosquitto/passwd

sudo mosquitto -c /etc/mosquitto/mosquitto.conf -t
sudo systemctl restart mosquitto
sudo systemctl --no-pager status mosquitto

echo
echo "Mosquitto LAN listener configured with ACL protection."
