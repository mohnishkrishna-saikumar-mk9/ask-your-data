"""Load IPL matches + deliveries into the `ipl` schema.

Run from the project root:  python -m scripts.load_ipl
Expects data/raw/ipl/matches.csv and data/raw/ipl/deliveries.csv (Kaggle "IPL Complete Dataset").
"""
from pathlib import Path

import pandas as pd

from scripts._loader_utils import (
    RAW_DIR,
    apply_mapping,
    load_tables,
    null_report,
    read_csv,
    rows_report,
    to_bool,
)
from src.db import run_query

# Renamed franchises -> current name. Deccan Chargers and Sunrisers are NOT merged.
TEAM_RENAMES = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
}
TEAM_COLS_MATCHES = ["team1", "team2", "toss_winner", "winner"]
TEAM_COLS_DELIVERIES = ["batting_team", "bowling_team"]

# Same ground, different spellings / old names (applied after dropping the ", City" suffix).
VENUE_ALIASES = {
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    "Feroz Shah Kotla": "Arun Jaitley Stadium",
    "Feroz Shah Kotla Ground": "Arun Jaitley Stadium",
    "Sardar Patel Stadium": "Narendra Modi Stadium",
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium",
    "Zayed Cricket Stadium": "Sheikh Zayed Stadium",
    "Rajiv Gandhi Intl. Cricket Stadium": "Rajiv Gandhi International Stadium",
    "Punjab Cricket Association Stadium": "Punjab Cricket Association IS Bindra Stadium",
}

MATCH_COLS = ["match_id", "season", "match_date", "city", "venue", "match_type", "team1", "team2",
              "toss_winner", "toss_decision", "winner", "result", "result_margin", "target_runs",
              "target_overs", "super_over", "method", "player_of_match"]
DELIVERY_COLS = ["match_id", "inning", "over_no", "ball", "phase", "batting_team", "bowling_team",
                 "batter", "bowler", "non_striker", "batter_runs", "extra_runs", "total_runs",
                 "extras_type", "is_wicket", "player_dismissed", "dismissal_kind", "fielder"]


def normalise_venue(venue: str | None) -> str | None:
    """'Wankhede Stadium, Mumbai' -> 'Wankhede Stadium'; then apply known aliases."""
    if venue is None:
        return None
    base = venue.split(",")[0].strip()
    return VENUE_ALIASES.get(base, base)


def over_to_phase(over_no: int) -> str:
    """0-5 powerplay, 6-14 middle, 15-19 death (overs are 0-based)."""
    if over_no <= 5:
        return "powerplay"
    return "middle" if over_no <= 14 else "death"


def clean_matches(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply the Section 7.1 cleaning rules to matches.csv."""
    df = raw.rename(columns={"id": "match_id", "date": "match_date"})
    df["match_date"] = pd.to_datetime(df["match_date"]).dt.date
    # '2007/08' style seasons are ambiguous; the match date's year is the source of truth.
    df["season"] = pd.to_datetime(df["match_date"]).dt.year
    df["match_id"] = df["match_id"].astype(int)
    for col in TEAM_COLS_MATCHES:
        df[col] = apply_mapping(df[col], TEAM_RENAMES, "team")
    new_venue = df["venue"].map(normalise_venue)
    changed = (new_venue != df["venue"]) & df["venue"].notna()
    print(f"    [venue] normalised {changed.sum()} rows into {new_venue.nunique()} venues")
    df["venue"] = new_venue
    for col in ["result_margin", "target_runs", "target_overs"]:
        df[col] = pd.to_numeric(df[col])
    df["super_over"] = to_bool(df["super_over"], {"Y", "True", "1"})
    return df[MATCH_COLS]


def clean_deliveries(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply the Section 7.1 cleaning rules to deliveries.csv."""
    df = raw.rename(columns={"over": "over_no", "batsman_runs": "batter_runs"})
    for col in ["match_id", "inning", "over_no", "ball", "batter_runs", "extra_runs", "total_runs"]:
        df[col] = df[col].astype(int)
    if df["over_no"].min() == 1 and df["over_no"].max() == 20:  # some versions are 1-based
        df["over_no"] -= 1
    df["phase"] = df["over_no"].map(over_to_phase)
    df["is_wicket"] = to_bool(df["is_wicket"], {"1", "True", "Y"})
    for col in TEAM_COLS_DELIVERIES:
        df[col] = apply_mapping(df[col], TEAM_RENAMES, "team")
    return df[DELIVERY_COLS]


def sanity_checks() -> None:
    """Print a few numbers a human can eyeball against known IPL facts."""
    per_season = run_query("SELECT season, COUNT(*) AS matches FROM ipl.matches GROUP BY 1 ORDER BY 1")
    print("  Matches per season:", dict(zip(per_season.season, per_season.matches, strict=True)))
    orphans = run_query(
        "SELECT COUNT(*) AS n FROM ipl.deliveries d "
        "LEFT JOIN ipl.matches m USING (match_id) WHERE m.match_id IS NULL"
    )["n"][0]
    print(f"  Orphan deliveries (should be 0): {orphans}")


def main(raw_dir: Path = RAW_DIR / "ipl") -> None:
    print("Loading IPL ...")
    raw_matches = read_csv(raw_dir / "matches.csv")
    raw_deliveries = read_csv(raw_dir / "deliveries.csv")
    matches = clean_matches(raw_matches)
    deliveries = clean_deliveries(raw_deliveries)
    # Every ball must belong to a known match (the FK would reject orphans anyway).
    deliveries = deliveries[deliveries["match_id"].isin(matches["match_id"])]
    rows_report("matches", len(raw_matches), len(matches))
    rows_report("deliveries", len(raw_deliveries), len(deliveries))
    null_report(matches, "matches")
    null_report(deliveries, "deliveries")
    load_tables("ipl.sql", [("ipl.matches", matches), ("ipl.deliveries", deliveries)])
    sanity_checks()


if __name__ == "__main__":
    main()
