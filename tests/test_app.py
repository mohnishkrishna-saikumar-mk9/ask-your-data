"""Streamlit app tests: dashboard config (no DB) + pages rendered with AppTest on fixture data."""
import pytest
from streamlit.testing.v1 import AppTest

from app.dashboards import DASHBOARDS
from src.config import DATASETS, ROOT
from src.sql_library import list_queries

PAGES = ROOT / "app" / "app_pages"


@pytest.mark.parametrize("dataset", list(DATASETS))
def test_every_dataset_has_a_complete_dashboard(dataset: str) -> None:
    board = DASHBOARDS[dataset]
    assert len(board.kpi_labels) == 4
    assert len(board.charts) >= 4
    prefixes = {q.path.name[:2] for q in list_queries(dataset)}
    for chart in board.charts:
        assert (chart.query in prefixes) != (chart.sql is not None), chart.title  # exactly one source
        assert chart.kind in {"bar", "barh", "line", "pie", "scatter"}
    if board.filter:
        assert board.filter.kind in {"range", "multi"}
        params = ":lo" if board.filter.kind == "range" else ":values"
        assert params in board.kpi_sql  # the KPI query must actually use the filter


def run_page(name: str, dataset: str | None = None) -> AppTest:
    at = AppTest.from_file(str(PAGES / name), default_timeout=60)
    if dataset:
        at.session_state["dataset"] = dataset
    return at.run()


@pytest.mark.db
@pytest.mark.parametrize("dataset", list(DATASETS))
def test_dashboard_renders(dataset: str, loaded_db: None) -> None:
    at = run_page("2_Dashboard.py", dataset)
    assert not at.exception, at.exception
    assert not [w.value for w in at.warning], [w.value for w in at.warning]
    # The tiles must be this dataset's KPIs (proves the picker really switched dataset).
    assert [m.label for m in at.metric] == list(DASHBOARDS[dataset].kpi_labels.values())


@pytest.mark.db
def test_overview_renders(loaded_db: None) -> None:
    at = run_page("0_Overview.py")
    assert not at.exception and not at.error


@pytest.mark.db
@pytest.mark.parametrize("dataset", list(DATASETS))
def test_query_library_renders(dataset: str, loaded_db: None) -> None:
    at = run_page("3_Query_Library.py", dataset)
    assert not at.exception and not at.error
