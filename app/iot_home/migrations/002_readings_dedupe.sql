ALTER TABLE readings
ADD COLUMN legacy_dedupe_exempt INTEGER NOT NULL DEFAULT 0
CHECK (legacy_dedupe_exempt IN (0, 1));

WITH ranked_readings AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY device_id, seq, datetime
            ORDER BY id
        ) AS duplicate_rank
    FROM readings
    WHERE seq IS NOT NULL
      AND datetime <> '1970-01-01T00:00:00Z'
)
UPDATE readings
SET legacy_dedupe_exempt = 1
WHERE id IN (
    SELECT id
    FROM ranked_readings
    WHERE duplicate_rank > 1
);

CREATE UNIQUE INDEX uq_readings_device_seq_datetime
ON readings (device_id, seq, datetime)
WHERE datetime <> '1970-01-01T00:00:00Z'
  AND legacy_dedupe_exempt = 0;
