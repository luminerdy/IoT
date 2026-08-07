CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    location TEXT,
    sensor_type TEXT,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    datetime TEXT NOT NULL,
    rssi INTEGER,
    status TEXT,
    seq INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_readings_device_created
ON readings (device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_readings_created
ON readings (created_at DESC);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    location TEXT,
    firmware_version TEXT,
    last_seen TEXT,
    online INTEGER NOT NULL DEFAULT 0,
    last_rssi INTEGER,
    last_status TEXT,
    last_seq INTEGER,
    last_ip TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deployment_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    from_version TEXT,
    to_version TEXT NOT NULL,
    observed_ip TEXT,
    status TEXT NOT NULL,
    rollout_id TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_deployment_attempts_device_created
ON deployment_attempts (device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_created
ON system_metrics (metric, created_at DESC);
