import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_connection() -> psycopg.Connection:
    """Create a connection to the configured Tiger Cloud PostgreSQL database."""
    connection_string = os.getenv("TIMESCALE_SERVICE_URL")
    if not connection_string:
        raise RuntimeError(
            "TIMESCALE_SERVICE_URL is missing from the project .env file"
        )

    return psycopg.connect(connection_string)
