#!/usr/bin/env bash
set -euo pipefail

project_dir="/home/scotty/IoT"
unit_dir="${project_dir}/deploy/systemd"

sudo install -o root -g root -m 0644 \
  "${unit_dir}/iot-home-db-maintenance.service" \
  /etc/systemd/system/iot-home-db-maintenance.service
sudo install -o root -g root -m 0644 \
  "${unit_dir}/iot-home-db-maintenance.timer" \
  /etc/systemd/system/iot-home-db-maintenance.timer
sudo systemctl daemon-reload
sudo systemctl enable --now iot-home-db-maintenance.timer
sudo systemctl start iot-home-db-maintenance.service
sudo systemctl --no-pager --full status \
  iot-home-db-maintenance.timer iot-home-db-maintenance.service
