ALTER TABLE readings
ADD COLUMN num_read_errors INTEGER;

ALTER TABLE readings
ADD COLUMN num_filtered_readings INTEGER;

ALTER TABLE devices
ADD COLUMN last_num_read_errors INTEGER;

ALTER TABLE devices
ADD COLUMN last_num_filtered_readings INTEGER;
