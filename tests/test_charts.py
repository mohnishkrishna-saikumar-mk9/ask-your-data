"""Auto-chart picker rules (SPEC 9.5)."""
from decimal import Decimal

import pandas as pd

from src.charts import make_figure, pick_chart


def test_single_value_is_kpi() -> None:
    assert pick_chart(pd.DataFrame({"n": [42]})).kind == "kpi"


def test_time_series_is_line() -> None:
    df = pd.DataFrame({"season": [2020, 2021, 2022], "runs": [1, 2, 3]})
    spec = pick_chart(df)
    assert (spec.kind, spec.x, spec.y) == ("line", "season", "runs")
    assert make_figure(df, spec) is not None


def test_month_dates_line() -> None:
    df = pd.DataFrame({"month": pd.to_datetime(["2022-04-01", "2022-05-01"]),
                       "revenue": [Decimal("10.5"), Decimal("20.1")]})
    assert pick_chart(df).kind == "line"


def test_category_numeric_is_bar() -> None:
    df = pd.DataFrame({"team": ["A", "B", "C"], "wins": [3, 1, 2]})
    spec = pick_chart(df)
    assert (spec.kind, spec.x, spec.y) == ("bar", "wins", "team")
    assert make_figure(df, spec) is not None


def test_decimal_values_count_as_numeric() -> None:
    df = pd.DataFrame({"state": ["X", "Y"], "revenue": [Decimal("1.5"), Decimal("2.5")]})
    assert pick_chart(df).kind == "bar"


def test_too_many_categories_is_table() -> None:
    df = pd.DataFrame({"name": [f"p{i}" for i in range(30)], "v": range(30)})
    assert pick_chart(df).kind == "table"


def test_two_numeric_is_scatter() -> None:
    df = pd.DataFrame({"etest": [60.0, 70.0], "salary": [2e5, 3e5]})
    assert pick_chart(df).kind == "scatter"


def test_empty_and_wide_are_table() -> None:
    assert pick_chart(pd.DataFrame()).kind == "table"
    wide = pd.DataFrame({"a": ["x"], "b": ["y"], "c": ["z"]})
    assert pick_chart(wide).kind == "table"
