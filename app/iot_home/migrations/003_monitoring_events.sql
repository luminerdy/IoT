CREATE TABLE IF NOT EXISTS monitoring_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    status TEXT NOT NULL DEFAULT 'ok',
    message TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_monitoring_events_created
ON monitoring_events (created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_monitoring_events_type_created
ON monitoring_events (event_type, created_at DESC, id DESC);
