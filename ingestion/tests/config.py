"""Project-wide settings. Secrets come from a .env file in the project root."""
import os

from dotenv import load_dotenv

load_dotenv()  # reads .env next to main.py


def _require(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file.")
    return value


# --- Twelve Data ---
API_KEY = _require("TWELVE_DATA_API_KEY")

# Keep at least one crypto pair: crypto trades 24/7, stocks only in market hours.
SYMBOLS = ["BTC/USD", "ETH/USD", "MSFT", "AAPL"]

# --- Tiger Cloud / TimescaleDB ---
DB_CONFIG = dict(
    database=os.getenv("TSDB_NAME", "tsdb"),
    host=_require("TSDB_HOST"),
    user=os.getenv("TSDB_USER", "tsdbadmin"),
    password=_require("TSDB_PASSWORD"),
    port=_require("TSDB_PORT"),
)

# --- Batching ---
MAX_BATCH_SIZE = 10   # small while testing; raise to 100-1000 later
FLUSH_INTERVAL = 5    # seconds; also flush on a timer so quiet feeds still land