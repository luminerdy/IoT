#!/usr/bin/env bash
set -euo pipefail

db_path="${1:-data/iot.db}"
backup_dir="${BACKUP_DIR:-data/backups}"
s3_uri="${S3_URI:-}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
db_name="$(basename "${db_path}")"
backup_path="${backup_dir}/${db_name%.db}-${timestamp}.sqlite"

if [[ ! -f "${db_path}" ]]; then
  echo "Database not found: ${db_path}" >&2
  exit 1
fi

mkdir -p "${backup_dir}"
sqlite3 "${db_path}" ".backup '${backup_path}'"
sqlite3 "${backup_path}" "PRAGMA integrity_check;" | grep -qx "ok"
gzip -9 "${backup_path}"
archive_path="${backup_path}.gz"

echo "Created backup: ${archive_path}"

if [[ -n "${s3_uri}" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "AWS CLI not found; install/configure awscli before S3 upload." >&2
    exit 1
  fi
  aws s3 cp "${archive_path}" "${s3_uri%/}/"
  echo "Uploaded backup to: ${s3_uri%/}/$(basename "${archive_path}")"
fi
