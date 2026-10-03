<h1 align="center">Finance Data Ingestion</h1>

<h3 align="center">Real-time market data ingestion, storage, and visualization on TimescaleDB and Grafana</h3>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="TimescaleDB" src="https://img.shields.io/badge/TimescaleDB-Tiger%20Cloud-FDB515.svg">
  <img alt="Grafana" src="https://img.shields.io/badge/Grafana-dashboard-F46800.svg">
  <img alt="Data source" src="https://img.shields.io/badge/data-Twelve%20Data%20WebSocket-informational.svg">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg">
</p>

<p align="center">
  <img src="docs/images/grafana-candlestick.png" alt="Real-time OHLCV candlestick dashboard in Grafana" width="900">
</p>

Finance Data Ingestion is an end-to-end time-series pipeline for live market data. It subscribes to the [Twelve Data](https://twelvedata.com/) WebSocket API, validates and normalizes each incoming price tick, and writes it to a [TimescaleDB](https://www.tigerdata.com/) hypertable hosted on Tiger Cloud. Continuous aggregates roll raw ticks up into OHLCV (open, high, low, close, volume) candles, which are served to a real-time candlestick dashboard in [Grafana](https://grafana.com/).

The project builds on the Tiger Data tutorial [Ingest real-time financial data](https://www.tigerdata.com/docs/learn/tutorials/ingest-real-time-financial-data) and extends it with a modular ingestion layer, a validation stage, and multiple aggregation intervals.

## Architecture

```mermaid
flowchart LR
    A["Twelve Data<br/>WebSocket API"] -->|"live price ticks"| B["WebSocket client"]
    B --> C["Normalizer"]
    C --> D["Validator"]
    D -->|"INSERT"| E[("crypto_ticks<br/>hypertable<br/>Tiger Cloud")]
    E --> F["Continuous aggregates<br/>OHLCV candles"]
    G["Refresh policy"] -.->|"scheduled refresh"| F
    F -->|"SQL"| H["Grafana<br/>candlestick dashboard"]
```

The pipeline is split into four layers, each with a single responsibility.

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Ingestion | WebSocket client | Holds the connection open, subscribes to symbols, and receives price messages |
| Processing | Normalizer and validator | Maps raw payloads to a fixed schema and rejects malformed or invalid ticks before they reach the database |
| Storage | TimescaleDB hypertable on Tiger Cloud | Stores raw ticks in time-partitioned chunks for fast inserts and range queries |
| Serving | Continuous aggregates and Grafana | Pre-computes OHLCV candles, keeps them fresh with a refresh policy, and renders them as live charts |

### Data flow

1. **Subscribe.** The client opens a WebSocket connection to Twelve Data and subscribes to the configured symbols (for example `BTC/USD`).
2. **Receive.** Each message carries a symbol, a price, and a timestamp. Messages arrive continuously, typically several per second per symbol.
3. **Normalize.** The normalizer converts the raw payload into the `crypto_ticks` schema, including converting the epoch timestamp to a timezone-aware `TIMESTAMPTZ`.
4. **Validate.** The validator drops ticks with missing fields, non-numeric values, or non-positive prices.
5. **Store.** Valid ticks are inserted into the `crypto_ticks` hypertable.
6. **Aggregate.** Continuous aggregates group ticks into time buckets and compute open, high, low, close, and volume per symbol.
7. **Visualize.** Grafana queries the aggregates on a short refresh interval and draws candlestick and volume panels.

## Database layer

All database access goes through a single connection module that reads one `TIMESCALE_SERVICE_URL` from the environment. The SQL that defines the schema, aggregates, and policies lives under `database/` so it can be reviewed and re-run independently of the Python code.

| File | Purpose |
|------|---------|
| `database/connection.py` | Creates the database connection from `TIMESCALE_SERVICE_URL` |
| `database/init_db.py` | Applies the schema, aggregates, and policies in order |
| `database/schema.sql` | Defines the `crypto_ticks` table and converts it to a hypertable |
| `database/continuous_aggregate.sql` | Defines the base continuous aggregate for OHLCV candles |
| `database/one_minute_aggregate.sql` | Defines the 1-minute candle aggregate |
| `database/refresh_policy.sql` | Schedules automatic refresh of the continuous aggregates |
| `database/querys.sql` | Sample queries for inspecting data |

## TimescaleDB on Tiger Cloud

Market ticks are an append-heavy, time-ordered workload, which is what TimescaleDB is built for. The project uses three of its features.

**Hypertables.** `crypto_ticks` is a regular PostgreSQL table that TimescaleDB automatically partitions by time into chunks. Inserts stay fast as the table grows, and queries over a time range only touch the relevant chunks.

```sql
CREATE TABLE crypto_ticks (
    time    TIMESTAMPTZ      NOT NULL,
    symbol  TEXT             NOT NULL,
    price   DOUBLE PRECISION NOT NULL,
    volume  DOUBLE PRECISION
);

SELECT create_hypertable('crypto_ticks', 'time');
```

**Continuous aggregates.** Instead of recomputing candles from raw ticks on every dashboard refresh, a continuous aggregate materializes them incrementally.

```sql
CREATE MATERIALIZED VIEW one_minute_candle
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    first(price, time) AS open,
    max(price)         AS high,
    min(price)         AS low,
    last(price, time)  AS close,
    sum(volume)        AS volume
FROM crypto_ticks
GROUP BY bucket, symbol;
```

**Refresh policies.** A policy refreshes the aggregate on a schedule so the dashboard always reads up-to-date candles without a manual job.

```sql
SELECT add_continuous_aggregate_policy('one_minute_candle',
    start_offset      => INTERVAL '1 hour',
    end_offset        => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');
```

The statements above illustrate the design. The exact definitions used by this project are in the `database/` folder.

## Installation

The project works with Python 3.10+ and requires a Tiger Cloud service and a Twelve Data API key with WebSocket access.

Create and activate a virtual environment.

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Clone the repository and install the dependencies.

```bash
git clone https://github.com/souvix-codes/Finance-Data-Ingestion.git
cd Finance-Data-Ingestion
pip install -r requirements.txt
```

## Configuration

Copy the example environment file and fill in your credentials.

```bash
cp .env.example .env
```

```env
TIMESCALE_SERVICE_URL=postgres://user:password@host:port/dbname?sslmode=require
TWELVE_DATA_API_KEY=your_api_key_here
```

Your Tiger Cloud connection string is available from the service overview page in the Tiger Cloud console. The `.env` file is listed in `.gitignore`, so your credentials are not committed.

## Quickstart

Initialize the database. This creates the hypertable, the continuous aggregates, and the refresh policy.

```bash
python database/init_db.py
```

Start the ingestion pipeline.

```bash
python main.py
```

Confirm that ticks are arriving.

```sql
SELECT symbol, COUNT(*) AS ticks, MAX(time) AS latest
FROM crypto_ticks
GROUP BY symbol;
```

## Grafana dashboard

The dashboard reads directly from the continuous aggregate, so every refresh is a cheap lookup of pre-computed candles.

1. In Grafana, open **Connections > Data sources > Add data source** and choose **PostgreSQL**.
2. Enter the Tiger Cloud host, database, user, and password. Set **TLS/SSL Mode** to `require` and enable the **TimescaleDB** option.
3. Create a dashboard and add a **Candlestick** panel.
4. Use the query below and map the returned fields to open, high, low, close, and volume.
5. Set the dashboard auto-refresh (for example, `5s`) to get the live view.

```sql
SELECT
  bucket AS "time",
  open, high, low, close, volume
FROM one_minute_candle
WHERE symbol = 'BTC/USD'
  AND $__timeFilter(bucket)
ORDER BY bucket;
```

## Why use this project?

1. Built for time-series workloads:
   - Hypertables keep inserts fast as data grows.
   - Continuous aggregates remove the need for manual batch jobs.
   - Dashboards query pre-computed candles, not raw ticks.

2. Clear separation of concerns:
   - Ingestion, processing, storage, and visualization are independent layers.
   - Validation happens before any write, so the database only holds clean data.

3. Reproducible setup:
   - All schema and policy definitions are plain SQL in `database/`.
   - Configuration is handled through a single `.env` file.

4. Easy to extend:
   - Add symbols by changing the subscription list.
   - Add candle intervals by defining another continuous aggregate.

## When should I not use this project?

- This is a learning and prototyping pipeline, not a production trading system. It does not include order execution, backtesting, or guaranteed-delivery semantics.
- Data quality depends on the upstream Twelve Data feed and your plan's WebSocket limits. Ticks missed during a disconnect are not backfilled.
- Volume values depend on what the upstream feed provides for each symbol and may not be available for every instrument.

## Project structure

```text
Finance-Data-Ingestion/
├── database/
│   ├── connection.py
│   ├── init_db.py
│   ├── schema.sql
│   ├── continuous_aggregate.sql
│   ├── one_minute_aggregate.sql
│   ├── refresh_policy.sql
│   └── querys.sql
├── ingestion/
│   └── websocket_server/     # WebSocket client, normalizer, validator
├── docs/
│   └── images/
│       └── grafana-candlestick.png
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## References

- [Tiger Cloud documentation](https://www.tigerdata.com/docs): service setup, hypertables, continuous aggregates, and policies
- [Tutorial: Ingest real-time financial data](https://www.tigerdata.com/docs/learn/tutorials/ingest-real-time-financial-data): the reference implementation this project is based on
- [Twelve Data WebSocket documentation](https://twelvedata.com/docs): real-time price streaming API
- [Grafana PostgreSQL data source](https://grafana.com/docs/grafana/latest/datasources/postgres/): connecting Grafana to TimescaleDB

## Acknowledgements

- [Tiger Data](https://www.tigerdata.com/docs/learn/tutorials/ingest-real-time-financial-data) for the tutorial this project builds on
- [Twelve Data](https://twelvedata.com/) for the real-time market data API
- [Grafana](https://grafana.com/) for the dashboarding platform

## License

This project is released under the MIT License.

</div>