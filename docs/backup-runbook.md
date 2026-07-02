# Backup Runbook

Phase 5 backup target: encrypted restic repository in S3 for project recovery, plus local verified SQLite backups when database-only exports are useful.

## Restic S3 Backup

The Pi is configured to back up the IoT project to an encrypted restic repository in S3.

Repository:

```sh
s3:s3.amazonaws.com/jsmoelling-home-iot-backup-674620572451-us-east-1-an/restic/iot
```

Local private files used by the scheduled job:

```text
~/config/backup.env
~/config/restic-excludes.txt
~/.config/restic/iot-password
~/logs/restic-iot-backup.log
```

Do not commit these files. They contain local credentials, generated passwords, or machine-specific state.

The backup currently includes:

```text
~/IoT
~/config
~/.config/restic
```

The exclude file omits generated dependency and cache folders such as `.venv`, `.pytest_cache`, `__pycache__`, `node_modules`, `dist`, and `build`.

The checked-in script template is:

```sh
scripts/restic_iot_backup.sh
```

The live cron-installed copy is:

```sh
~/scripts/restic-iot-backup.sh
```

Cron schedule:

```cron
15 2 * * * /home/scotty/scripts/restic-iot-backup.sh
```

Retention policy:

```text
14 daily snapshots
8 weekly snapshots
12 monthly snapshots
```

### Manual Backup

```sh
source ~/config/backup.env
restic backup ~/IoT ~/config ~/.config/restic --exclude-file ~/config/restic-excludes.txt
```

### Verify Snapshots

```sh
source ~/config/backup.env
restic snapshots
```

Known successful snapshots from initial setup:

```text
c0a264e6
7ef0b89d
```

### Restore Test

Restore into a scratch directory:

```sh
rm -rf ~/restore-test
mkdir -p ~/restore-test
source ~/config/backup.env
restic restore latest --target ~/restore-test
```

Expected restored roots:

```text
~/restore-test/home/scotty/IoT
~/restore-test/home/scotty/config
~/restore-test/home/scotty/.config/restic
```

After inspection:

```sh
rm -rf ~/restore-test
```

### Scheduled Backup Logs

```sh
tail -80 ~/logs/restic-iot-backup.log
```

### Security Notes

- Restic encrypts backup contents before writing to S3.
- The restic password is required for restore; losing it makes the backup unrecoverable.
- AWS access keys should be rotated if exposed and should have the narrowest practical S3 permissions.
- Never commit `backup.env`, restic password files, restored backup trees, or local logs.

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
