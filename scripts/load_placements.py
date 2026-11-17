"""Load the campus recruitment data into the `placements` schema.

Run from the project root:  python -m scripts.load_placements
Expects data/raw/placements/Placement_Data_Full_Class.csv (Kaggle "Campus Recruitment").
"""
from pathlib import Path

import pandas as pd

from scripts._loader_utils import RAW_DIR, load_tables, null_report, read_csv, to_bool
from src.db import run_query

CSV_NAME = "Placement_Data_Full_Class.csv"

RENAMES = {
    "sl_no": "student_id",
    "ssc_p": "ssc_percent",
    "ssc_b": "ssc_board",
    "hsc_p": "hsc_percent",
    "hsc_b": "hsc_board",
    "hsc_s": "hsc_stream",
    "degree_p": "degree_percent",
    "degree_t": "degree_field",
    "workex": "has_work_experience",
    "etest_p": "employability_test_percent",
    "specialisation": "mba_specialisation",
    "mba_p": "mba_percent",
    "status": "is_placed",
}
NUMERIC = ["ssc_percent", "hsc_percent", "degree_percent", "employability_test_percent",
           "mba_percent", "salary"]


def clean_students(raw: pd.DataFrame) -> pd.DataFrame:
    """Rename to readable columns, convert types, and keep salary NULL when not placed."""
    df = raw.rename(columns=RENAMES)
    df["student_id"] = df["student_id"].astype(int)
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col])
    df["has_work_experience"] = to_bool(df["has_work_experience"], {"Yes"})
    df["is_placed"] = to_bool(df["is_placed"], {"Placed"})
    df.loc[~df["is_placed"], "salary"] = None
    for col in ["ssc_board", "hsc_board", "hsc_stream", "degree_field", "mba_specialisation"]:
        df[col] = df[col].str.strip()
    return df[["student_id", "gender", *[c for c in df.columns
                                          if c not in ("student_id", "gender")]]]


def main(raw_dir: Path = RAW_DIR / "placements") -> None:
    """Read, clean and load the student table."""
    print("Loading placements ...")
    students = clean_students(read_csv(raw_dir / CSV_NAME))
    null_report(students, "students")
    load_tables("placements.sql", [("placements.students", students)])
    summary = run_query("SELECT COUNT(*) AS n, ROUND(AVG(is_placed::int), 3) AS rate "
                        "FROM placements.students")
    print(f"  Students: {summary.n[0]}, placement rate: {summary.rate[0]}")


if __name__ == "__main__":
    main()
