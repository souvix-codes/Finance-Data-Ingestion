"""Live market-data ingestion entry point.

This script connects to Tiger Cloud and subscribes to Twelve Data price events.
It intentionally avoids the stale imports that were pointing to modules that do
not exist in the current project layout.
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from twelvedata import TDClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


API_KEY = os.getenv("TWELVE_DATA_API_KEY")
SYMBOLS = ["BTC/USD", "ETH/USD", "MSFT", "AAPL"]
DB_TABLE = "crypto_ticks"


def _is_valid_price_event(event):
    return event.get("event") == "price" and event.get("symbol") and event.get("price") is not None


def _insert_event(conn, event):
    if not _is_valid_price_event(event):
        return

    timestamp = datetime.fromtimestamp(event["timestamp"], tz=timezone.utc)
    symbol = event["symbol"]
    price = float(event["price"])
    day_volume = event.get("day_volume")

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {DB_TABLE} (time, symbol, price, day_volume)
            VALUES (%s, %s, %s, %s)
            """,
            (timestamp, symbol, price, day_volume),
        )
    conn.commit()


def main():
    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing from the project .env file.")

    conn = get_connection()

    def on_event(event):
        try:
            _insert_event(conn, event)
        except Exception as exc:  # pragma: no cover - operational safety net
            print(f"Failed to write event: {exc}")

    client = TDClient(apikey=API_KEY)
    ws = client.websocket(on_event=on_event)
    ws.subscribe(SYMBOLS)
    print("Connecting to Twelve Data websocket...")
    ws.connect()

    try:
        while True:
            ws.heartbeat()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ingestion...")
    finally:
        conn.close()


if __name__ == "__main__":
    main()