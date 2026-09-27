import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_connection() -> psycopg.Connection:
    """Create a connection to the configured Tiger Cloud PostgreSQL database."""
    connection_string = os.getenv("TIMESCALE_SERVICE_URL")
    if connection_string:
        try:
            return psycopg.connect(connection_string)
        except Exception:
            pass

    dbname = os.getenv("TSDB_NAME") or os.getenv("TIGERDB_NAME") or "tsdb"
    host = os.getenv("TSDB_HOST") or os.getenv("TIGERDB_HOST")
    user = os.getenv("TSDB_USER") or os.getenv("TIGERDB_USER") or "tsdbadmin"
    password = os.getenv("TSDB_PASSWORD") or os.getenv("TIGERDB_PASSWORD")
    port = os.getenv("TSDB_PORT") or os.getenv("TIGERDB_PORT") or "5432"

    if not host:
        raise RuntimeError("No Tiger Cloud host is configured in the project .env file.")
    if not password:
        raise RuntimeError("No Tiger Cloud password is configured in the project .env file.")

    return psycopg.connect(
        dbname=dbname,
        host=host,
        user=user,
        password=password,
        port=int(port),
        sslmode="require",
    )
