"""Loader tests: pure cleaning functions (no DB) + full loads into PostgreSQL (db marker)."""
import pandas as pd
import pytest

from scripts import load_ecommerce, load_ipl, load_placements
from scripts._loader_utils import blanks_to_null, clean_header, read_csv
from src.db import run_query
from tests.conftest import FIXTURES


def test_blanks_become_null() -> None:
    df = blanks_to_null(pd.DataFrame({"a": [" x ", "", "NA", "N/A"]}))
    assert df["a"].tolist() == ["x", None, None, None]


def test_clean_header() -> None:
    assert clean_header("\ufeffSr No") == "Sr No"
    assert clean_header("Sales Channel ") == "Sales Channel"


def test_read_csv_drops_unnamed(tmp_path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("\ufeffa,Unnamed: 1, b \n1,,N/A\n", encoding="utf-8")
    df = read_csv(path)
    assert list(df.columns) == ["a", "b"] and df["b"].tolist() == [None]


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


def test_clean_students_rules() -> None:
    s = load_placements.clean_students(
        read_csv(FIXTURES / "placements" / "Placement_Data_Full_Class.csv"))
    assert s.loc[~s["is_placed"], "salary"].isna().all()
    assert s["has_work_experience"].dtype == bool


@pytest.mark.db
def test_loaded_row_counts(loaded_db: None) -> None:
    assert run_query("SELECT COUNT(*) AS n FROM ipl.matches")["n"][0] == 5
    assert run_query("SELECT COUNT(*) AS n FROM ipl.deliveries")["n"][0] == 50
    assert run_query("SELECT COUNT(*) AS n FROM ecommerce.orders")["n"][0] == 20
    assert run_query("SELECT COUNT(*) AS n FROM placements.students")["n"][0] == 30


@pytest.mark.db
def test_views_and_comments_exist(loaded_db: None) -> None:
    df = run_query("SELECT COUNT(*) AS n FROM ipl.batting_innings WHERE is_out IS NULL")
    assert df["n"][0] == 0
    missing = run_query(
        "SELECT c.table_schema, c.table_name, c.column_name FROM information_schema.columns c "
        "WHERE c.table_schema IN ('ipl','ecommerce','placements') AND col_description("
        "(quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass, "
        "c.ordinal_position) IS NULL")
    assert missing.empty, f"columns without COMMENT: {missing.values.tolist()}"


@pytest.mark.db
def test_loader_is_idempotent(loaded_db: None) -> None:
    load_placements.main(FIXTURES / "placements")
    assert run_query("SELECT COUNT(*) AS n FROM placements.students")["n"][0] == 30


@pytest.mark.db
def test_run_query_refuses_writes(loaded_db: None) -> None:
    with pytest.raises(Exception, match="read-only"):
        run_query("DELETE FROM placements.students")
