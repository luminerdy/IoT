#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${LOG_FILE:-$HOME/logs/restic-iot-backup.log}"
BACKUP_ENV="${BACKUP_ENV:-$HOME/config/backup.env}"
EXCLUDE_FILE="${EXCLUDE_FILE:-$HOME/config/restic-excludes.txt}"

{
  echo "[$(date --iso-8601=seconds)] starting restic IoT backup"

  source "$BACKUP_ENV"

  restic backup \
    "$HOME/IoT" \
    "$HOME/config" \
    "$HOME/.config/restic" \
    --exclude-file "$EXCLUDE_FILE"

  restic forget \
    --keep-daily 14 \
    --keep-weekly 8 \
    --keep-monthly 12 \
    --prune

  echo "[$(date --iso-8601=seconds)] finished restic IoT backup"
} >> "$LOG_FILE" 2>&1
