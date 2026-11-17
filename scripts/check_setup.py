"""Step 1 check: can Python talk to PostgreSQL? Creates the 3 dataset schemas.

Run from the project root:  python -m scripts.check_setup
"""
from src.config import DATASETS, ROOT
from src.db import get_engine, run_query, run_sql_file


def main() -> None:
    """Check the connection, then create and verify all dataset schemas."""
    version = run_query("SELECT version() AS v")["v"][0]
    print(f"[OK] Connected to: {version.split(',')[0]}")

    with get_engine(readonly=False).begin() as conn:
        run_sql_file(conn, ROOT / "sql" / "00_create_schemas.sql")
    found = set(run_query(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = ANY(:names)",
        {"names": list(DATASETS)},
    )["schema_name"])
    missing = [name for name in DATASETS if name not in found]
    if missing:
        raise SystemExit(f"[FAIL] Missing schemas {missing}: add them to sql/00_create_schemas.sql")
    print(f"[OK] All {len(DATASETS)} schemas ready: {list(DATASETS)}")
    print("\nSetup complete - next: python -m scripts.load_all")


if __name__ == "__main__":
    main()
