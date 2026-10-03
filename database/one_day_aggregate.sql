CREATE MATERIALIZED VIEW one_day_candle
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    first(price, time) AS open,
    max(price) AS high,
    min(price) AS low,
    last(price, time) AS close
FROM crypto_ticks
GROUP BY bucket, symbol;