#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
unit_name="iot-home-post-reboot-check.service"

sudo install -o root -g root -m 0644 \
  "${repo_dir}/deploy/${unit_name}" \
  "/etc/systemd/system/${unit_name}"

sudo systemctl daemon-reload
sudo systemctl enable "${unit_name}"
sudo systemctl start "${unit_name}"
sudo systemctl --no-pager status "${unit_name}" || true
