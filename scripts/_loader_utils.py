"""Helpers shared by all loaders: read CSV, normalise blanks, bulk-load with COPY."""
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Connection, Engine

from src.config import ROOT
from src.db import get_engine, run_sql_file

RAW_DIR = ROOT / "data" / "raw"
SCHEMA_DIR = ROOT / "sql" / "schema"


NULL_TOKENS = ["", "NA", "N/A", "n/a", "nan", "NaN", "None", "null", "NULL"]


def clean_header(name: str) -> str:
    """Strip the UTF-8 BOM and surrounding whitespace, e.g. '\ufeffSr No' -> 'Sr No'."""
    return name.replace("\ufeff", "").strip()


def read_csv(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    """Read a raw CSV as text (each loader converts types explicitly).

    Headers are cleaned, `Unnamed: N` index columns dropped and NULL tokens become None.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Download it first (see docs/DATA_SOURCES.md).")
    df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False, encoding=encoding)
    df = df.rename(columns=clean_header)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed:")])
    return blanks_to_null(df)


def blanks_to_null(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and turn empty / 'NA' / 'nan' strings into real NULLs (None)."""
    out = df.copy()
    for col in out.columns:
        s = out[col].astype("string").str.strip()
        out[col] = s.mask(s.isin(NULL_TOKENS))
    return out.astype(object).where(out.notna(), None)


def to_bool(series: pd.Series, true_values: set[str]) -> pd.Series:
    """Map text like 'Y'/'True'/'1' to booleans (case-insensitive). NULL -> False."""
    lowered = {v.lower() for v in true_values}
    return series.map(lambda v: v is not None and str(v).strip().lower() in lowered)


def apply_mapping(series: pd.Series, mapping: dict[str, str], label: str) -> pd.Series:
    """Replace values using `mapping` and print how many cells each rule changed."""
    counts = series.map(mapping).dropna().groupby(series).size()
    for old, n in counts.items():
        print(f"    [{label}] {old!r} -> {mapping[old]!r} ({n} rows)")
    return series.map(lambda v: mapping.get(v, v))


def copy_df(conn: Connection, df: pd.DataFrame, table: str) -> int:
    """Bulk-insert a DataFrame with PostgreSQL COPY (much faster than INSERTs)."""
    cols = ", ".join(df.columns)
    clean = df.astype(object).where(df.notna(), None)
    cursor = conn.connection.dbapi_connection.cursor()
    with cursor.copy(f"COPY {table} ({cols}) FROM STDIN") as copy:
        for row in clean.itertuples(index=False, name=None):
            copy.write_row(row)
    return len(df)


def load_tables(schema_file: str, tables: list[tuple[str, pd.DataFrame]],
                engine: Engine | None = None) -> None:
    """Recreate a schema from its .sql file and COPY each (table, df) in order, in one transaction."""
    engine = engine or get_engine(readonly=False)
    with engine.begin() as conn:
        run_sql_file(conn, SCHEMA_DIR / schema_file)
        for table, df in tables:
            n = copy_df(conn, df, table)
            print(f"  [OK] {table}: {n:,} rows")
            conn.exec_driver_sql(f"ANALYZE {table}")  # refresh planner statistics


def rows_report(name: str, read: int, loaded: int) -> None:
    """Print rows read vs rows loaded, and why they differ if they do."""
    dropped = read - loaded
    note = f" ({dropped:,} dropped)" if dropped else ""
    print(f"  {name}: read {read:,} rows, loading {loaded:,}{note}")


def null_report(df: pd.DataFrame, name: str) -> None:
    """Print the columns that contain NULLs and how many."""
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        print(f"  NULLs in {name}: " + ", ".join(f"{c}={n:,}" for c, n in nulls.items()))
