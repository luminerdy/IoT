#!/usr/bin/env bash
set -euo pipefail

cert_dir="${1:-/etc/mosquitto/certs/iot-home}"
config_path="/etc/mosquitto/conf.d/iot-home-tls-acl.conf"
acl_path="/etc/mosquitto/aclfile"

hostname="$(hostname -f 2>/dev/null || hostname)"

echo "Configuring Mosquitto TLS listener on 8883 for host: ${hostname}"
echo "Certificate directory: ${cert_dir}"

sudo install -d -o root -g mosquitto -m 0750 "${cert_dir}"

if [[ ! -f "${cert_dir}/ca.crt" ]]; then
  sudo openssl ecparam -name prime256v1 -genkey -noout -out "${cert_dir}/ca.key"
  sudo openssl req -x509 -new -nodes \
    -key "${cert_dir}/ca.key" \
    -sha256 \
    -days 3650 \
    -subj "/CN=iot-home-local-ca" \
    -out "${cert_dir}/ca.crt"
fi

if [[ ! -f "${cert_dir}/server.crt" ]]; then
  tmp_conf="$(mktemp)"
  cat > "${tmp_conf}" <<CONFIG
[req]
distinguished_name=req_distinguished_name
req_extensions=req_ext
prompt=no

[req_distinguished_name]
CN=${hostname}

[req_ext]
subjectAltName=@alt_names

[alt_names]
DNS.1=${hostname}
DNS.2=$(hostname)
DNS.3=iot-pi.local
CONFIG

  sudo openssl ecparam -name prime256v1 -genkey -noout -out "${cert_dir}/server.key"
  sudo openssl req -new -key "${cert_dir}/server.key" -out "${cert_dir}/server.csr" -config "${tmp_conf}"
  sudo openssl x509 -req \
    -in "${cert_dir}/server.csr" \
    -CA "${cert_dir}/ca.crt" \
    -CAkey "${cert_dir}/ca.key" \
    -CAcreateserial \
    -out "${cert_dir}/server.crt" \
    -days 825 \
    -sha256 \
    -extfile "${tmp_conf}" \
    -extensions req_ext
  rm -f "${tmp_conf}"
fi

tmp_acl="$(mktemp)"
cat > "${tmp_acl}" <<'ACL'
# Device users should match their device ID, for example esp32-device-id.
pattern readwrite home/sensors/%u/telemetry
pattern readwrite home/sensors/%u/status
pattern readwrite home/sensors/%u/response
pattern readwrite home/sensors/%u/ota/status
pattern read home/sensors/%u/config
pattern read home/sensors/%u/command

user iot-admin
topic readwrite home/#

user iot-collector
topic read home/sensors/+/telemetry
topic read home/sensors/+/status
ACL

sudo install -o root -g mosquitto -m 0640 "${tmp_acl}" "${acl_path}"
rm -f "${tmp_acl}"

tmp_config="$(mktemp)"
cat > "${tmp_config}" <<CONFIG
listener 8883
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file ${acl_path}
cafile ${cert_dir}/ca.crt
certfile ${cert_dir}/server.crt
keyfile ${cert_dir}/server.key
tls_version tlsv1.2
CONFIG

sudo install -o root -g root -m 0644 "${tmp_config}" "${config_path}"
rm -f "${tmp_config}"

sudo chown root:mosquitto "${cert_dir}"/*.key "${cert_dir}"/*.crt
sudo chmod 0640 "${cert_dir}"/*.key
sudo chmod 0644 "${cert_dir}"/*.crt

sudo mosquitto -c /etc/mosquitto/mosquitto.conf -t
sudo systemctl restart mosquitto
sudo systemctl --no-pager status mosquitto

echo
echo "TLS listener configured. Copy ${cert_dir}/ca.crt into firmware/include/secrets.h as MQTT_CA_CERT before enabling MQTT_USE_TLS."
