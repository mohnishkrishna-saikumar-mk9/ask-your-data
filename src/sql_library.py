"""Reads the hand-written queries in sql/analysis and parses their header comments."""
from dataclasses import dataclass
from pathlib import Path

from src.config import ROOT

ANALYSIS_DIR = ROOT / "sql" / "analysis"


@dataclass(frozen=True)
class QueryInfo:
    """One analysis query file: its header fields and SQL text."""

    dataset: str
    path: Path
    question: str
    concepts: str
    result_shape: str
    sql: str

    @property
    def title(self) -> str:
        """'05_top_items_per_year.sql' -> '05 Top items per year'."""
        num, _, rest = self.path.stem.partition("_")
        return f"{num} {rest.replace('_', ' ').capitalize()}"


def parse_query_file(path: Path, dataset: str) -> QueryInfo:
    """Read the '-- Q:', '-- Concepts:', '-- Result:' header lines from a .sql file."""
    text = path.read_text(encoding="utf-8")
    header = {}
    for line in text.splitlines():
        if not line.startswith("--"):
            break
        key, _, value = line[2:].strip().partition(":")
        header[key.strip().lower()] = value.strip()
    return QueryInfo(dataset, path, header.get("q", ""), header.get("concepts", ""),
                     header.get("result", ""), text)


def list_queries(dataset: str) -> list[QueryInfo]:
    """All analysis queries for one dataset, sorted by file name."""
    return [parse_query_file(p, dataset)
            for p in sorted((ANALYSIS_DIR / dataset).glob("*.sql"))]


def get_query(dataset: str, prefix: str) -> QueryInfo:
    """Find a query by its number prefix, e.g. get_query(dataset, '05')."""
    for q in list_queries(dataset):
        if q.path.name.startswith(prefix):
            return q
    raise KeyError(f"No query {prefix!r} for {dataset}")
