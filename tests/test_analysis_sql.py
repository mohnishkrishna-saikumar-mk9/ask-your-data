"""Every hand-written analysis query must have the header format and run without error."""
from pathlib import Path

import pytest

from src.db import run_query
from src.sql_library import QueryInfo, list_queries

ANALYSIS = Path(__file__).resolve().parents[1] / "sql" / "analysis"
ALL_QUERIES = [q for ds in ("ipl", "ecommerce", "placements") for q in list_queries(ds)]


def test_query_counts() -> None:
    counts = {ds: len(list_queries(ds)) for ds in ("ipl", "ecommerce", "placements")}
    assert counts == {"ipl": 20, "ecommerce": 10, "placements": 10}


@pytest.mark.parametrize("q", ALL_QUERIES, ids=lambda q: q.path.name)
def test_header_format(q: QueryInfo) -> None:
    assert q.question and q.concepts and q.result_shape


@pytest.mark.db
@pytest.mark.parametrize("q", ALL_QUERIES, ids=lambda q: q.path.name)
def test_query_runs(q: QueryInfo, loaded_db: None) -> None:
    run_query(q.sql, schema=q.dataset)
