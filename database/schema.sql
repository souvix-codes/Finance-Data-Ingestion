
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'crypto_ticks'
ORDER BY ordinal_position;
SELECT hypertable_schema, hypertable_name
FROM timescaledb_information.hypertables
WHERE hypertable_name = 'crypto_ticks';
CREATE TABLE crypto_assets (
    symbol TEXT UNIQUE,
    "name" TEXT
);
SELECT COUNT(*) AS total_rows
FROM crypto_ticks;