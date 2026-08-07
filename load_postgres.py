#!/usr/bin/env python
"""Optional extra credit (per the assignment FAQ): load
data/output/all_stars_2024_2026.csv into Postgres. CSV remains the required,
authoritative deliverable -- this is purely additive.

Usage:
    pip install -r requirements-postgres.txt
    docker run -d --name blitz-postgres -e POSTGRES_PASSWORD=postgres \\
        -p 5432:5432 postgres:16
    python load_postgres.py
    # or: DATABASE_URL=postgresql://user:pass@host:port/db python load_postgres.py

Idempotent: re-running upserts on the same (player_id, season_id, stat_type,
team_id) primary key as the CSV, so it's safe to run after every rebuild.
"""
import csv
import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    sys.exit(
        "psycopg2 not installed. Run: pip install -r requirements-postgres.txt"
    )

sys.path.insert(0, str(Path(__file__).parent))
from src import models

CSV_PATH = Path(__file__).parent / "data" / "output" / "all_stars_2024_2026.csv"
SCHEMA_PATH = Path(__file__).parent / "postgres" / "schema.sql"
DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/blitz_allstars"

BOOLEAN_COLUMNS = {"is_all_star", "is_show_top100"}
BLANK_VALUES = {"", "—"}  # "" and the — placeholder used for empty stat lines


def pg_column(csv_column: str) -> str:
    return csv_column.lower()


def clean_value(column: str, raw: str):
    if raw is None or raw in BLANK_VALUES:
        return None
    if column in BOOLEAN_COLUMNS:
        return raw in ("True", "true", "1")
    return raw


def main():
    if not CSV_PATH.exists():
        sys.exit(f"{CSV_PATH} not found -- run `python build.py` first.")

    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()

        rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
        pg_columns = [pg_column(c) for c in models.ALL_COLUMNS]
        placeholders = ", ".join(["%s"] * len(pg_columns))
        update_clause = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in pg_columns
            if c not in ("player_id", "season_id", "stat_type", "team_id")
        )
        insert_sql = f"""
            INSERT INTO all_stars ({', '.join(pg_columns)})
            VALUES ({placeholders})
            ON CONFLICT (player_id, season_id, stat_type, team_id)
            DO UPDATE SET {update_clause}
        """

        with conn.cursor() as cur:
            for row in rows:
                values = [clean_value(col, row.get(col)) for col in models.ALL_COLUMNS]
                cur.execute(insert_sql, values)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT player_id) FROM all_stars")
            total_rows, unique_players = cur.fetchone()
        print(f"Loaded {len(rows)} CSV rows. Table now has {total_rows} rows, "
              f"{unique_players} unique players.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
