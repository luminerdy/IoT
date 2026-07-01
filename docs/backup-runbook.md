# SQLite Backup Runbook

Phase 5 backup target: local verified SQLite backups, then S3 copy after AWS credentials and bucket policy are ready.

## Local Backup

```sh
scripts/backup_sqlite.sh
```

The script uses SQLite's online `.backup` command, runs `PRAGMA integrity_check`, then writes a gzipped archive under `data/backups/`.

To back up a specific database:

```sh
scripts/backup_sqlite.sh data/iot.db
```

## S3 Copy

After AWS CLI is installed and configured on the Pi:

```sh
S3_URI=s3://your-iot-backup-bucket/sqlite scripts/backup_sqlite.sh data/iot.db
```

Use a dedicated IAM principal with write-only access to the backup prefix if practical. Enable bucket versioning or object lock before relying on S3 as the recovery copy.

## Restore Check

```sh
gunzip -c data/backups/iot-YYYYMMDDTHHMMSSZ.sqlite.gz > /tmp/iot-restore-check.sqlite
sqlite3 /tmp/iot-restore-check.sqlite "PRAGMA integrity_check;"
```

Expected output:

```text
ok
```
