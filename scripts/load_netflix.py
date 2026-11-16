"""Load Netflix titles into the `netflix` schema (titles + 4 bridge tables).

Run from the project root:  python -m scripts.load_netflix
Expects data/raw/netflix/netflix_titles.csv (Kaggle "Netflix Movies and TV Shows").
"""
from pathlib import Path

import pandas as pd

from scripts._loader_utils import RAW_DIR, load_tables, null_report, read_csv, rows_report

CSV_NAME = "netflix_titles.csv"
TITLE_COLS = ["show_id", "type", "title", "date_added", "release_year", "rating",
              "duration_minutes", "seasons", "description"]
# bridge table -> (raw list column, value column name)
BRIDGES = {
    "netflix.title_directors": ("director", "director"),
    "netflix.title_cast": ("cast", "actor"),
    "netflix.title_countries": ("country", "country"),
    "netflix.title_genres": ("listed_in", "genre"),
}


def fix_misplaced_duration(df: pd.DataFrame) -> pd.DataFrame:
    """A few rows have the duration ('74 min') in `rating`; move it and blank the rating."""
    out = df.copy()
    wrong = out["rating"].fillna("").str.fullmatch(r"\d+ min")
    out.loc[wrong & out["duration"].isna(), "duration"] = out.loc[wrong, "rating"]
    out.loc[wrong, "rating"] = None
    print(f"    [rating] moved {int(wrong.sum())} durations out of the rating column")
    return out


def split_duration(duration: pd.Series) -> tuple[pd.Series, pd.Series]:
    """'90 min' -> minutes 90; '2 Seasons' -> seasons 2."""
    minutes = duration.str.extract(r"^(\d+) min$")[0]
    seasons = duration.str.extract(r"^(\d+) Seasons?$")[0]
    return pd.to_numeric(minutes).astype("Int64"), pd.to_numeric(seasons).astype("Int64")


def clean_titles(raw: pd.DataFrame) -> pd.DataFrame:
    """Typed titles table (dates, durations, release year)."""
    df = fix_misplaced_duration(raw)
    df["date_added"] = pd.to_datetime(df["date_added"].str.strip(), format="%B %d, %Y").dt.date
    df["release_year"] = df["release_year"].astype(int)
    df["duration_minutes"], df["seasons"] = split_duration(df["duration"])
    return df[TITLE_COLS]


def explode_list(raw: pd.DataFrame, list_col: str, value_col: str) -> pd.DataFrame:
    """'A, B, C' in one cell -> three (show_id, value) rows; items trimmed, blanks and repeats dropped."""
    pairs = raw[["show_id", list_col]].dropna()
    pairs = pairs.assign(**{value_col: pairs[list_col].str.split(",")}).explode(value_col)
    pairs[value_col] = pairs[value_col].str.strip()
    pairs = pairs[pairs[value_col] != ""]
    return pairs[["show_id", value_col]].drop_duplicates()


def main(raw_dir: Path = RAW_DIR / "netflix") -> None:
    print("Loading Netflix ...")
    raw = read_csv(raw_dir / CSV_NAME)
    titles = clean_titles(raw)
    rows_report("titles", len(raw), len(titles))
    null_report(titles, "titles")
    bridges = [(table, explode_list(raw, list_col, value_col))
               for table, (list_col, value_col) in BRIDGES.items()]
    load_tables("netflix.sql", [("netflix.titles", titles), *bridges])


if __name__ == "__main__":
    main()
