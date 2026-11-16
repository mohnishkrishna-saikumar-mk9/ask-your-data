"""Every hand-written analysis query must have the header format and run without error;
every dataset must ship a metric glossary."""
import pytest

from src.config import DATASETS
from src.db import run_query
from src.glossary import load_glossary
from src.sql_library import QueryInfo, list_queries

ALL_QUERIES = [q for ds in DATASETS for q in list_queries(ds)]
EXPECTED_COUNTS = {"ipl": 20, "ecommerce": 10, "placements": 10, "olist": 8, "startups": 6,
                   "air_quality": 6, "netflix": 6, "chinook": 6}


def test_query_counts() -> None:
    assert {ds: len(list_queries(ds)) for ds in DATASETS} == EXPECTED_COUNTS
    assert len(ALL_QUERIES) == 72


@pytest.mark.parametrize("q", ALL_QUERIES, ids=lambda q: f"{q.dataset}/{q.path.name}")
def test_header_format(q: QueryInfo) -> None:
    assert q.question and q.concepts and q.result_shape


@pytest.mark.parametrize("q", ALL_QUERIES, ids=lambda q: f"{q.dataset}/{q.path.name}")
def test_query_only_uses_its_own_schema(q: QueryInfo) -> None:
    others = [ds for ds in DATASETS if ds != q.dataset]
    body = q.sql.lower()
    assert not [ds for ds in others if f"{ds}." in body], "query references another dataset"


@pytest.mark.parametrize("dataset", list(DATASETS))
def test_every_dataset_has_a_glossary(dataset: str) -> None:
    glossary = load_glossary(dataset)
    assert len(glossary.get("metrics", {})) >= 5


@pytest.mark.db
@pytest.mark.parametrize("q", ALL_QUERIES, ids=lambda q: f"{q.dataset}/{q.path.name}")
def test_query_runs(q: QueryInfo, loaded_db: None) -> None:
    run_query(q.sql, schema=q.dataset)
