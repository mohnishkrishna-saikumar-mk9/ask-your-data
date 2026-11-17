"""Load the Chinook sample database into the `chinook` schema - the classic benchmark DB.

Run from the project root:  python -m scripts.load_chinook
Expects data/raw/chinook/Chinook_PostgreSql.sql (github.com/lerocha/chinook-database, MIT licence).

The official script creates its own database (`DROP/CREATE DATABASE chinook` + psql's `\\c`).
We strip those lines and run the rest inside our database with search_path = chinook.
"""
import re
from pathlib import Path

from scripts._loader_utils import RAW_DIR, SCHEMA_DIR
from src.db import get_engine, run_query, run_sql_file

SCRIPT_NAME = "Chinook_PostgreSql.sql"
TABLES = ["album", "artist", "customer", "employee", "genre", "invoice", "invoice_line",
          "media_type", "playlist", "playlist_track", "track"]
# Lines that only make sense when the script owns a whole database.
# One whole line each. Note [^;\n]: a plain [^;] would also match newlines and could run on
# from the words "Drop database" in a /* banner comment and swallow the comment's closing */.
DATABASE_LEVEL = re.compile(
    r"^[ \t]*(?:DROP DATABASE[^;\n]*;|CREATE DATABASE[^;\n]*;|\\c[ \t]+\w+;?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def prepare_script(text: str) -> str:
    """Remove database-level statements so the script can run inside an existing schema."""
    removed = DATABASE_LEVEL.findall(text)
    print(f"    [script] stripped {len(removed)} database-level lines")
    return DATABASE_LEVEL.sub("", text)


def main(raw_dir: Path = RAW_DIR / "chinook") -> None:
    """Run the vendor SQL script inside schema chinook, then add comments."""
    print("Loading Chinook ...")
    path = raw_dir / SCRIPT_NAME
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Download it first (see docs/DATA_SOURCES.md).")
    script = prepare_script(path.read_text(encoding="utf-8-sig"))
    with get_engine(readonly=False).begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS chinook")
        # Drop tables (not the schema) so the read-only role's default privileges survive.
        conn.exec_driver_sql("DROP TABLE IF EXISTS "
                             + ", ".join(f"chinook.{t}" for t in TABLES) + " CASCADE")
        conn.exec_driver_sql("SET LOCAL search_path TO chinook")
        conn.exec_driver_sql(script.replace("%", "%%"))
        run_sql_file(conn, SCHEMA_DIR / "chinook.sql")
        for table in TABLES:
            conn.exec_driver_sql(f"ANALYZE chinook.{table}")
    counts = run_query(" UNION ALL ".join(
        f"SELECT '{t}' AS tbl, COUNT(*) AS n FROM chinook.{t}" for t in TABLES))
    for row in counts.itertuples():
        print(f"  [OK] chinook.{row.tbl}: {row.n:,} rows")


if __name__ == "__main__":
    main()
