"""Database helpers: shared engines + a safe function to run SELECT queries."""
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from src.config import (
    DATABASE_URL,
    MAX_ROWS,
    QUERY_TIMEOUT_MS,
    READONLY_DATABASE_URL,
    WORK_MEM_MB,
)


@lru_cache(maxsize=2)
def get_engine(readonly: bool = True) -> Engine:
    """Create an engine once and reuse it (connection pooling = speed).

    readonly=True uses READONLY_DATABASE_URL (the `ayd_reader` role when deployed);
    readonly=False uses the admin DATABASE_URL (needed by the loaders).
    """
    url = READONLY_DATABASE_URL if readonly else DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL is missing. Copy .env.example to .env and fill it in.")
    return create_engine(url, pool_pre_ping=True)


def run_query(sql: str, params: dict | None = None, schema: str | None = None) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame (at most MAX_ROWS rows).

    - READ ONLY transaction: even if a bad query slips through, Postgres refuses writes.
    - statement_timeout: a slow query is cancelled instead of freezing the app.
    - search_path: lets queries name tables without the schema prefix.
    """
    with get_engine().connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text(f"SET LOCAL statement_timeout = {int(QUERY_TIMEOUT_MS)}"))
        # Default work_mem (4 MB) makes COUNT(DISTINCT ...) sorts spill to disk on ~130K rows.
        conn.execute(text(f"SET LOCAL work_mem = '{int(WORK_MEM_MB)}MB'"))
        if schema:
            conn.execute(text("SELECT set_config('search_path', :s, true)"), {"s": schema})
        if params:
            result = conn.execute(text(sql), params)
        else:
            # No bind parameters: send the SQL as-is so ':' or '%' inside string
            # literals (e.g. LIKE 'Cancelled%') are not mistaken for placeholders.
            result = conn.exec_driver_sql(sql.replace("%", "%%"))
        rows = result.fetchmany(MAX_ROWS)
        df = pd.DataFrame(rows, columns=list(result.keys()))
        conn.rollback()
        return df


def run_sql_file(conn: Connection, path: Path) -> None:
    """Execute a .sql file (many statements) on an open admin connection."""
    conn.exec_driver_sql(path.read_text(encoding="utf-8").replace("%", "%%"))
