#!/usr/bin/env bash
set -euo pipefail

cert_dir="${1:-/etc/mosquitto/certs/iot-home}"
config_path="/etc/mosquitto/conf.d/iot-home-tls-acl.conf"
acl_path="/etc/mosquitto/iot-home-per-device.acl"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
acl_source="${script_dir}/../deploy/mosquitto/iot-home-per-device.acl"

hostname="$(hostname -f 2>/dev/null || hostname)"
short_hostname="$(hostname)"
mdns_hostname="${short_hostname}.local"
lower_mdns_hostname="$(printf '%s' "${mdns_hostname}" | tr '[:upper:]' '[:lower:]')"

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

regenerate_server_cert=0
if ! sudo test -f "${cert_dir}/server.crt"; then
  regenerate_server_cert=1
elif ! sudo openssl verify -CAfile "${cert_dir}/ca.crt" "${cert_dir}/server.crt" >/dev/null; then
  regenerate_server_cert=1
elif ! sudo openssl x509 -in "${cert_dir}/server.crt" -noout -ext subjectAltName \
  | grep -Fq "DNS:${mdns_hostname}"; then
  regenerate_server_cert=1
fi

if [[ "${regenerate_server_cert}" -eq 1 ]]; then
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
DNS.2=${short_hostname}
DNS.3=${mdns_hostname}
DNS.4=${lower_mdns_hostname}
DNS.5=iot-pi.local
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

sudo install -o root -g mosquitto -m 0640 "${acl_source}" "${acl_path}"

tmp_config="$(mktemp)"
cat > "${tmp_config}" <<CONFIG
per_listener_settings true
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

sudo find "${cert_dir}" -maxdepth 1 -type f \( -name "*.key" -o -name "*.crt" \) \
  -exec chown root:mosquitto {} +
sudo find "${cert_dir}" -maxdepth 1 -type f -name "*.key" -exec chmod 0640 {} +
sudo find "${cert_dir}" -maxdepth 1 -type f -name "*.crt" -exec chmod 0644 {} +

if mosquitto -h 2>&1 | grep -q -- " -t "; then
  sudo mosquitto -c /etc/mosquitto/mosquitto.conf -t
else
  echo "Installed mosquitto does not support -t config testing; relying on systemd restart." >&2
fi
sudo systemctl restart mosquitto
sudo systemctl --no-pager status mosquitto

echo
echo "TLS listener configured. Copy ${cert_dir}/ca.crt into firmware/include/secrets.h as MQTT_CA_CERT before enabling MQTT_USE_TLS."
