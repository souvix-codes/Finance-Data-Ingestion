import os
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from twelvedata import TDClient
from psycopg2.extras import execute_values

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_PATH)

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

DB_NAME = os.getenv("TIGERDB_DATABASE", "tsdb")
DB_HOST = os.getenv("TIGERDB_HOST")
DB_USER = os.getenv("TIGERDB_USER", "tsdbadmin")
DB_PASSWORD = os.getenv("TIGERDB_PASSWORD")
DB_PORT = int(os.getenv("TIGERDB_PORT", "31241"))

# BASIC CONFIGURATION CHECK

if not TWELVE_DATA_API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY is missing from .env"
    )

if not DB_HOST:
    raise RuntimeError(
        "TIGERDB_HOST is missing from .env"
    )

if not DB_PASSWORD:
    raise RuntimeError(
        "TIGERDB_PASSWORD is missing from .env"
    )

# WEBSOCKET PIPELINE

class WebsocketPipeline:

    DB_TABLE = "crypto_ticks"

    DB_COLUMNS = [
        "time",
        "symbol",
        "price",
        "day_volume"
    ]

    # Insert immediately after this many records
    MAX_BATCH_SIZE = 100

    # Even if 100 records haven't arrived,
    # insert whatever we have after this many seconds.
    MAX_BATCH_WAIT = 2

    def __init__(self, conn):

        self.conn = conn

        self.current_batch = []

        self.insert_counter = 0
        self.last_insert_time = time.time()

    # DATABASE INSERT

    def _insert_values(self, data):

        if not data:
            return

        try:

            with self.conn.cursor() as cursor:

                sql = f"""
                    INSERT INTO {self.DB_TABLE}
                    ({','.join(self.DB_COLUMNS)})
                    VALUES %s;
                """

                execute_values(
                    cursor,
                    sql,
                    data
                )

            self.conn.commit()

            self.insert_counter += 1

            print(
                f" Batch #{self.insert_counter} inserted "
                f"({len(data)} rows)"
            )

            self.last_insert_time = time.time()

        except Exception as e:

            self.conn.rollback()

            print("Database insert failed:")
            print(e)


    def _flush_batch(self):

        if not self.current_batch:
            return

        batch = self.current_batch

        # Clear the batch first
        self.current_batch = []

        self._insert_values(batch)

    def _on_event(self, event):

        # We only want price events
        if event.get("event") != "price":
            return

        try:

            # Twelve Data timestamp -> timezone-aware UTC datetime
            timestamp = datetime.fromtimestamp(
                event["timestamp"],
                tz=timezone.utc
            )

            symbol = event["symbol"]
            price = event["price"]
            day_volume = event.get("day_volume")

            data = (
                timestamp,
                symbol,
                price,
                day_volume
            )

            # Add event to batch
            self.current_batch.append(data)

            print(
                f" {symbol} | "
                f"price={price} | "
                f"time={timestamp.isoformat()} | "
                f"batch={len(self.current_batch)}"
            )

            # Insert immediately when batch reaches 100
            if len(self.current_batch) >= self.MAX_BATCH_SIZE:

                self._flush_batch()

        except Exception as e:

            print(" Error processing WebSocket event:")
            print(e)

    # START WEBSOCKET

    def start(self, symbols):

        td = TDClient(
            apikey=TWELVE_DATA_API_KEY
        )

        ws = td.websocket(
            on_event=self._on_event
        )

        print("Subscribing to:")
        print(symbols)

        ws.subscribe(symbols)

        print("🔌 Connecting to Twelve Data WebSocket...")

        ws.connect()

        print("WebSocket connected")

        try:

            while True:
                # PERIODIC FLUSH
                # If we have some records but haven't reached
                # 100 records, don't keep them in memory forever.
                #

                if (
                    self.current_batch
                    and
                    time.time() - self.last_insert_time
                    >= self.MAX_BATCH_WAIT
                ):

                    print(
                        f"Flushing small batch "
                        f"({len(self.current_batch)} rows)"
                    )

                    self._flush_batch()

                # Keep WebSocket alive
                ws.heartbeat()

                time.sleep(1)

        except KeyboardInterrupt:

            print("\n Stopping WebSocket...")

            # Insert anything still waiting in memory
            self._flush_batch()

            print("Remaining data flushed")

            self.conn.close()

            print(" Database connection closed")


# DATABASE CONNECTION

print("Connecting to Tiger Cloud...")

conn = psycopg2.connect(
    database=DB_NAME,
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    port=DB_PORT
)

print("Database connection successful")

# SYMBOLS
symbols = [
    "BTC/USD",
    "ETH/USD",
    "MSFT",
    "AAPL"
]

# START PIPELINE

websocket = WebsocketPipeline(conn)

websocket.start(
    symbols=symbols
)