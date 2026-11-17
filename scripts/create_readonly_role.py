"""Create/refresh the read-only `ayd_reader` role.

Run from the project root (as the admin DATABASE_URL):  python -m scripts.create_readonly_role
Needs READONLY_PASSWORD in .env. Afterwards set READONLY_DATABASE_URL to use that role.
"""
import os

from sqlalchemy import text

from src.config import ROOT
from src.db import get_engine, run_sql_file


def main() -> None:
    """Create or refresh the read-only role using READONLY_PASSWORD."""
    password = os.getenv("READONLY_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Set READONLY_PASSWORD (12+ characters) in .env first.")
    with get_engine(readonly=False).begin() as conn:
        conn.execute(text("SELECT set_config('ayd.pw', :pw, true)"), {"pw": password})
        run_sql_file(conn, ROOT / "scripts" / "create_readonly_role.sql")
    print("[OK] Role ayd_reader ready. Set READONLY_DATABASE_URL to connect as it.")


if __name__ == "__main__":
    main()
