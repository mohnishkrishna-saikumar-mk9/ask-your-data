"""Loader tests: pure cleaning functions (no DB) + full loads into PostgreSQL (db marker)."""
import pandas as pd
import pytest

from scripts import (
    load_air_quality,
    load_chinook,
    load_ecommerce,
    load_ipl,
    load_netflix,
    load_olist,
    load_placements,
    load_startups,
)
from scripts._loader_utils import blanks_to_null, clean_header, read_csv
from src.config import DATASETS
from src.db import run_query
from tests.conftest import FIXTURES

# ---------------- shared helpers ----------------


def test_blanks_become_null() -> None:
    df = blanks_to_null(pd.DataFrame({"a": [" x ", "", "NA", "N/A"]}))
    assert df["a"].tolist() == ["x", None, None, None]


def test_clean_header() -> None:
    assert clean_header("﻿Sr No") == "Sr No"
    assert clean_header("Sales Channel ") == "Sales Channel"


def test_read_csv_drops_unnamed(tmp_path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("﻿a,Unnamed: 1, b \n1,,N/A\n", encoding="utf-8")
    df = read_csv(path)
    assert list(df.columns) == ["a", "b"] and df["b"].tolist() == [None]


# ---------------- IPL ----------------


@pytest.mark.parametrize(("over", "phase"), [(0, "powerplay"), (5, "powerplay"), (6, "middle"),
                                             (14, "middle"), (15, "death"), (19, "death")])
def test_over_to_phase(over: int, phase: str) -> None:
    assert load_ipl.over_to_phase(over) == phase


def test_venue_normalisation() -> None:
    assert load_ipl.normalise_venue("Wankhede Stadium, Mumbai") == "Wankhede Stadium"
    assert load_ipl.normalise_venue("Feroz Shah Kotla") == "Arun Jaitley Stadium"
    assert load_ipl.normalise_venue(None) is None


def test_clean_matches_rules() -> None:
    m = load_ipl.clean_matches(read_csv(FIXTURES / "ipl" / "matches.csv"))
    assert set(m["season"]) == {2008, 2020, 2023}  # season comes from the date, not '2007/08'
    teams = set(m["team1"]) | set(m["team2"]) | set(m["winner"].dropna())
    assert "Delhi Daredevils" not in teams and "Delhi Capitals" in teams
    assert "Kings XI Punjab" not in teams
    assert m["super_over"].dtype == bool


def test_clean_deliveries_rules() -> None:
    d = load_ipl.clean_deliveries(read_csv(FIXTURES / "ipl" / "deliveries.csv"))
    assert d["over_no"].between(0, 19).all()
    assert set(d["phase"]) <= {"powerplay", "middle", "death"}
    assert d["is_wicket"].dtype == bool


# ---------------- Placements ----------------


def test_clean_students_rules() -> None:
    s = load_placements.clean_students(
        read_csv(FIXTURES / "placements" / "Placement_Data_Full_Class.csv"))
    assert s.loc[~s["is_placed"], "salary"].isna().all()
    assert s["has_work_experience"].dtype == bool


# ---------------- Netflix ----------------


def test_netflix_misplaced_duration_moved() -> None:
    raw = pd.DataFrame({"rating": ["74 min", "PG"], "duration": [None, "90 min"]})
    out = load_netflix.fix_misplaced_duration(raw)
    assert pd.isna(out["rating"][0]) and out["rating"][1] == "PG"
    assert out["duration"].tolist() == ["74 min", "90 min"]


def test_netflix_split_duration() -> None:
    minutes, seasons = load_netflix.split_duration(pd.Series(["90 min", "1 Season", "3 Seasons"]))
    assert minutes[0] == 90 and pd.isna(minutes[1])
    assert seasons.tolist()[1:] == [1, 3]


def test_netflix_explode_list_trims_and_dedupes() -> None:
    raw = pd.DataFrame({"show_id": ["s1", "s2"], "cast": [" A, B ,A,", None]})
    assert load_netflix.explode_list(raw, "cast", "actor")["actor"].tolist() == ["A", "B"]


def test_netflix_titles_fixture() -> None:
    titles = load_netflix.clean_titles(read_csv(FIXTURES / "netflix" / "netflix_titles.csv"))
    assert not titles["rating"].fillna("").str.contains("min").any()
    movies = titles[titles["type"] == "Movie"]
    assert movies["duration_minutes"].notna().all() and movies["seasons"].isna().all()


# ---------------- Startups ----------------


@pytest.mark.parametrize(("raw", "expected"), [
    ("09/01/2020", "2020-01-09"), ("12/05.2015", "2015-05-12"), ("22/01//2015", "2015-01-22"),
    ("05/072018", "2018-07-05"), ("01/07/015", "2015-07-01"), ("31/02/2016", None), (None, None),
])
def test_startups_parse_date(raw: str | None, expected: str | None) -> None:
    result = load_startups.parse_date(raw)
    assert (result.isoformat() if result else None) == expected


@pytest.mark.parametrize(("raw", "expected"), [
    ("20,00,00,000", 200_000_000.0), ("14,342,000+", 14_342_000.0), ("undisclosed", None),
    ("N/A", None), (None, None), (float("nan"), None),
])
def test_startups_parse_amount(raw: object, expected: float | None) -> None:
    assert load_startups.parse_amount(raw) == expected


def test_startups_clean_text_removes_literal_escapes() -> None:
    # The raw file contains the characters backslash, backslash, x, c, 2 ... written out as text.
    assert load_startups.clean_text(r"\\xc2\\xa0Gurgaon") == "Gurgaon"
    assert load_startups.clean_text(r"Seed\\nFunding") == "Seed Funding"
    assert load_startups.clean_text("  ") is None


def test_startups_investment_type_and_city() -> None:
    assert load_startups.normalise_investment_type("Seed/ Angel Funding") == "Seed / Angel"
    assert load_startups.normalise_investment_type("PrivateEquity") == "Private Equity"
    assert load_startups.normalise_investment_type("Debt-Funding") == "Debt Funding"
    assert load_startups.normalise_investment_type("Series B") == "Series B"
    assert load_startups.first_city("Bangalore / USA") == "Bengaluru"
    assert load_startups.first_city("New Delhi") == "Delhi"


def test_startups_fixture_rules() -> None:
    rounds = load_startups.clean_rounds(read_csv(FIXTURES / "startups" / "startup_funding.csv"))
    assert rounds["funding_date"].notna().all()  # every typo date in the fixture is parsed
    assert rounds.loc[rounds["round_id"] == 61, "amount_usd"].isna().all()  # known bad amount
    assert "Rapido Bike Taxi" not in set(rounds["startup_name"])
    text = rounds.select_dtypes(exclude="number").astype(str)
    assert not text.apply(lambda col: col.str.contains("\\", regex=False)).any().any()
    investors = load_startups.split_investors(rounds)
    assert not investors.duplicated().any() and (investors["investor_name"] != "").all()


# ---------------- Air quality ----------------


def test_air_quality_clean_daily() -> None:
    df = load_air_quality.clean_daily(read_csv(FIXTURES / "air_quality" / "city_day.csv"),
                                      "City", "city")
    assert list(df.columns[:3]) == ["city", "obs_date", "pm25"]
    assert pd.api.types.is_float_dtype(df["aqi"])


# ---------------- E-commerce ----------------


def test_clean_sales_rules() -> None:
    df = load_ecommerce.clean_sales(read_csv(FIXTURES / "ecommerce" / "Amazon Sale Report.csv"))
    assert {"Puducherry", "Rajasthan", "Delhi"} <= set(df["ship_state"])
    assert "PONDICHERRY" not in set(df["ship_state"])
    assert df["has_promotion"].any()
    assert df.loc[df["amount_missing"], "amount"].isna().all()
    products, orders, items = load_ecommerce.split_tables(df)
    assert orders["order_id"].is_unique and products["sku"].is_unique
    assert "promotion_ids" not in orders.columns  # raw id list is dropped
    assert len(items) == len(df)


def test_snake_case() -> None:
    assert load_ecommerce.snake_case("Sales Channel ") == "sales_channel"
    assert load_ecommerce.snake_case("ship-service-level") == "ship_service_level"


def test_international_keeps_only_well_formed_rows() -> None:
    raw = read_csv(FIXTURES / "ecommerce" / "International sale Report.csv")
    df = load_ecommerce.clean_international(raw)
    assert len(df) == 14  # shifted duplicate rows and stock-list rows are dropped
    assert df["sale_date"].notna().all() and df["gross_amount"].notna().all()


def test_inventory_unique_skus() -> None:
    raw = read_csv(FIXTURES / "ecommerce" / "Sale Report.csv")
    df = load_ecommerce.clean_inventory(raw)
    assert df["sku"].is_unique and df["sku"].notna().all() and len(df) < len(raw)
    assert not df["category"].fillna("").str.startswith("AN :").any()


# ---------------- Olist ----------------


def test_olist_products_renamed_and_translated() -> None:
    trans = read_csv(FIXTURES / "olist" / "product_category_name_translation.csv")
    assert "product_category_name" in trans.columns  # BOM stripped from the header
    raw = read_csv(FIXTURES / "olist" / "olist_products_dataset.csv")
    df = load_olist.clean_products(raw, trans)
    assert "name_length" in df.columns and "product_name_lenght" not in df.columns
    assert df.loc[df["category"] == "pc_gamer", "category_english"].tolist() == ["pc_gamer"]


def test_olist_zip_locations_one_row_per_prefix() -> None:
    geo = read_csv(FIXTURES / "olist" / "olist_geolocation_dataset.csv")
    zips = load_olist.build_zip_locations(geo)
    assert zips["zip_code_prefix"].is_unique
    assert len(zips) == geo["geolocation_zip_code_prefix"].nunique()


# ---------------- Chinook ----------------


def test_chinook_strips_only_database_statements() -> None:
    script = (
        "/****\n   Drop database if it exists\n****/\nDROP DATABASE IF EXISTS chinook;\n"
        "/****\n   Create database\n****/\nCREATE DATABASE chinook;\n\\c chinook;\n"
        "CREATE TABLE a (x INT);\n"
    )
    out = load_chinook.prepare_script(script)
    assert "DROP DATABASE IF" not in out and "CREATE DATABASE chinook" not in out
    assert "\\c" not in out
    assert out.count("****/") == 2  # banner comments still closed (regression test)
    assert "CREATE TABLE a" in out


# ---------------- Integration (PostgreSQL) ----------------


@pytest.mark.db
def test_loaded_row_counts(loaded_db: None) -> None:
    expected = {
        "ipl.matches": 5, "ipl.deliveries": 50, "ecommerce.orders": 20,
        "ecommerce.international_sales": 14, "placements.students": 30, "netflix.titles": 40,
        "startups.funding_rounds": 50, "air_quality.city_daily": 24, "olist.orders": 12,
        "chinook.invoice": 2,
    }
    for table, n in expected.items():
        assert run_query(f"SELECT COUNT(*) AS n FROM {table}")["n"][0] == n, table


@pytest.mark.db
def test_every_dataset_has_expected_tables(loaded_db: None) -> None:
    tables = run_query("SELECT table_schema, COUNT(*) AS n FROM information_schema.tables "
                       "WHERE table_schema = ANY(:s) GROUP BY 1", {"s": list(DATASETS)})
    counts = dict(zip(tables["table_schema"], tables["n"], strict=True))
    assert counts == {"placements": 1, "netflix": 5, "startups": 2, "air_quality": 3,
                      "ecommerce": 5, "ipl": 4, "olist": 8, "chinook": 11}


@pytest.mark.db
def test_views_and_comments_exist(loaded_db: None) -> None:
    df = run_query("SELECT COUNT(*) AS n FROM ipl.batting_innings WHERE is_out IS NULL")
    assert df["n"][0] == 0
    regclass = "(quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass"
    missing_cols = run_query(
        "SELECT c.table_schema, c.table_name, c.column_name FROM information_schema.columns c "
        f"WHERE c.table_schema = ANY(:s) AND col_description({regclass}, c.ordinal_position) IS NULL",
        {"s": list(DATASETS)})
    assert missing_cols.empty, f"columns without COMMENT: {missing_cols.values.tolist()}"
    missing_tables = run_query(
        "SELECT c.table_schema, c.table_name FROM information_schema.tables c "
        f"WHERE c.table_schema = ANY(:s) AND obj_description({regclass}) IS NULL",
        {"s": list(DATASETS)})
    assert missing_tables.empty, f"tables without COMMENT: {missing_tables.values.tolist()}"


@pytest.mark.db
def test_loaders_are_idempotent(loaded_db: None) -> None:
    load_placements.main(FIXTURES / "placements")
    assert run_query("SELECT COUNT(*) AS n FROM placements.students")["n"][0] == 30
    load_chinook.main(FIXTURES / "chinook")  # SQL-script loader drops tables, not the schema
    assert run_query("SELECT COUNT(*) AS n FROM chinook.track")["n"][0] == 3


@pytest.mark.db
def test_run_query_refuses_writes(loaded_db: None) -> None:
    with pytest.raises(Exception, match="read-only"):
        run_query("DELETE FROM placements.students")
