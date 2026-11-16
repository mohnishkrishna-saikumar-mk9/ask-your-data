"""Load Indian startup funding into the `startups` schema - the dirty-data test.

Run from the project root:  python -m scripts.load_startups
Expects data/raw/startups/startup_funding.csv (Kaggle "Indian Startup Funding").
"""
import datetime as dt
import re
from pathlib import Path

import pandas as pd

from scripts._loader_utils import (
    RAW_DIR,
    apply_mapping,
    load_tables,
    null_report,
    read_csv,
    rows_report,
)

CSV_NAME = "startup_funding.csv"
RENAMES = {
    "Sr No": "round_id", "Date dd/mm/yyyy": "funding_date", "Startup Name": "startup_name",
    "Industry Vertical": "industry_vertical", "SubVertical": "sub_vertical",
    "City  Location": "city", "Investors Name": "investors", "InvestmentnType": "investment_type",
    "Amount in USD": "amount_usd", "Remarks": "remarks",
}
ROUND_COLS = ["round_id", "funding_date", "startup_name", "industry_vertical", "sub_vertical",
              "city", "investment_type", "amount_usd", "remarks"]

# The raw text contains escape sequences written out literally, e.g. "\\xc2\\xa0N/A", "Seed\\nFunding".
ESCAPE_ARTEFACT = re.compile(r"(?:\\+x[0-9a-fA-F]{2})+")
LITERAL_NEWLINE = re.compile(r"\\+n")

# Keyed by the type with everything except letters removed and lower-cased.
INVESTMENT_TYPES = {
    "seedangelfunding": "Seed / Angel", "seedanglefunding": "Seed / Angel",
    "angelseedfunding": "Seed / Angel", "seedfunding": "Seed / Angel", "seed": "Seed / Angel",
    "seedround": "Seed / Angel", "seedfundinground": "Seed / Angel", "angel": "Seed / Angel",
    "angelround": "Seed / Angel", "angelfunding": "Seed / Angel",
    "privateequity": "Private Equity", "privateequityround": "Private Equity",
    "debtfunding": "Debt Funding", "debt": "Debt Funding",
    "preseriesa": "Pre-Series A", "crowdfunding": "Crowd Funding",
}
CITIES = {"Bangalore": "Bengaluru", "Gurgaon": "Gurugram", "New Delhi": "Delhi"}
STARTUP_NAMES = {
    "Ola Cabs": "Ola", "Olacabs": "Ola", "Flipkart.com": "Flipkart", "Paytm Marketplace": "Paytm",
    "Oyo": "OYO", "OYO Rooms": "OYO", "Oyo Rooms": "OYO", "OyoRooms": "OYO", "Oyorooms": "OYO",
    "Rapido Bike Taxi": "Rapido",
}
# Amounts verified as wrong in the source. We blank them rather than guess an exchange rate.
KNOWN_BAD_AMOUNTS = {
    61: "Rapido Aug 2019 Series B: '3,90,00,00,000' is Rs 390 crore entered as USD (70x too big)",
}


def is_missing(value: object) -> bool:
    """None or NaN (pandas turns None into NaN inside .map())."""
    return value is None or (isinstance(value, float) and value != value)


def clean_text(value: str | None) -> str | None:
    """Remove literal escape artefacts and non-breaking spaces; empty -> None."""
    if is_missing(value):
        return None
    text = ESCAPE_ARTEFACT.sub(" ", value)
    text = LITERAL_NEWLINE.sub(" ", text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_date(value: str | None) -> dt.date | None:
    """Tolerant dd/mm/yyyy parser: handles '12/05.2015', '22/01//2015', '05/072018', '01/07/015'."""
    if is_missing(value):
        return None
    match = re.fullmatch(r"(\d{1,2})\D+(\d{1,2})\D*(\d{3,4})", value)
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    year = year + 2000 if year < 1000 else year  # '015' -> 2015
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def parse_amount(value: str | None) -> float | None:
    """'20,00,00,000' -> 200000000; '14,342,000+' -> 14342000; undisclosed / unknown -> None."""
    if is_missing(value):
        return None
    digits = value.replace(",", "").rstrip("+").strip()
    return float(digits) if re.fullmatch(r"\d+(\.\d+)?", digits) else None


def normalise_investment_type(value: str | None) -> str | None:
    """Map spelling variants to one label; unknown types are kept as written."""
    if is_missing(value):
        return None
    key = re.sub(r"[^a-z]", "", value.lower())
    return INVESTMENT_TYPES.get(key, value)


def first_city(value: str | None) -> str | None:
    """'Pune / US' -> 'Pune'; then merge old/new city names."""
    if is_missing(value):
        return None
    city = re.split(r"[/,&]", value)[0].strip()
    return CITIES.get(city, city) or None


def clean_rounds(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply the Section 7.5 rules and report how many values each one changed."""
    df = raw.rename(columns=RENAMES)
    for col in df.columns:
        df[col] = df[col].map(clean_text)
    df["round_id"] = df["round_id"].astype(int)
    parsed = df["funding_date"].map(parse_date)
    print(f"    [date] unparseable -> NULL: {df.loc[parsed.isna(), 'funding_date'].tolist()}")
    df["funding_date"] = parsed
    df["amount_usd"] = df["amount_usd"].map(parse_amount)
    print(f"    [amount] undisclosed -> NULL: {int(df['amount_usd'].isna().sum())} rounds")
    for round_id, reason in KNOWN_BAD_AMOUNTS.items():
        df.loc[df["round_id"] == round_id, "amount_usd"] = None
        print(f"    [amount] round {round_id} -> NULL: {reason}")
    df["investment_type"] = df["investment_type"].map(normalise_investment_type)
    df["city"] = df["city"].map(first_city)
    df["startup_name"] = apply_mapping(df["startup_name"], STARTUP_NAMES, "name")
    return df


def split_investors(rounds: pd.DataFrame) -> pd.DataFrame:
    """'Sequoia, Accel Partners' -> one (round_id, investor_name) row per investor."""
    pairs = rounds[["round_id", "investors"]].dropna()
    pairs = pairs.assign(investor_name=pairs["investors"].str.split(",")).explode("investor_name")
    pairs["investor_name"] = pairs["investor_name"].str.strip()
    pairs = pairs[pairs["investor_name"] != ""]
    return pairs[["round_id", "investor_name"]].drop_duplicates()


def main(raw_dir: Path = RAW_DIR / "startups") -> None:
    print("Loading startups ...")
    raw = read_csv(raw_dir / CSV_NAME)
    rounds = clean_rounds(raw)
    investors = split_investors(rounds)
    rows_report("funding_rounds", len(raw), len(rounds))
    print(f"  investment types: {rounds['investment_type'].value_counts().head(8).to_dict()}")
    null_report(rounds[ROUND_COLS], "funding_rounds")
    load_tables("startups.sql", [("startups.funding_rounds", rounds[ROUND_COLS]),
                                 ("startups.round_investors", investors)])


if __name__ == "__main__":
    main()
