import sys
from pathlib import Path

# let this file run directly (e.g. VS Code's Run button) as well as with -m
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import get_connection  # noqa: E402

SQL_DIR = Path(__file__).parent

# order matters: table -> aggregates -> policies
SQL_FILES = [
    "schema.sql",
    "continuous_aggregate.sql",
    "one_minute_aggregate.sql",
    "refresh_policy.sql",
]


def split_statements(sql_text):
    statements = []
    for chunk in sql_text.split(";"):
        code_lines = [
            line for line in chunk.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if code_lines:
            statements.append(chunk.strip())
    return statements


def init_db():
    conn = get_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for name in SQL_FILES:
                sql_text = (SQL_DIR / name).read_text(encoding="utf-8")
                for statement in split_statements(sql_text):
                    cur.execute(statement)
                print(f"OK  {name}")
    finally:
        conn.close()
    print("Database setup complete.")


if __name__ == "__main__":
    init_db()