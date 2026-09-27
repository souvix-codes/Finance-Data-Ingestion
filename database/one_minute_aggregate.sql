SELECT * FROM one_minute_candle
WHERE symbol = 'BTC/USD' AND bucket >= NOW() - INTERVAL '1 hour'
ORDER BY bucket;