"""SQL extraction from messy LLM replies (FR-10) and prompt variants."""
import pytest

from src.llm.prompts import build_messages, build_retry_messages, extract_sql

CASES = [
    ("```sql\nSELECT 1;\n```", "SELECT 1"),
    ("Here you go:\n```sql\nSELECT a FROM t\n```\nHope this helps!", "SELECT a FROM t"),
    ("```SQL\nselect 2\n```", "select 2"),
    ("```\nSELECT 3\n```", "SELECT 3"),
    ("```postgresql\nSELECT 4\n```", "SELECT 4"),
    ("SELECT 5;", "SELECT 5"),
    ("Sure! The query is: SELECT 6 FROM t;", "SELECT 6 FROM t"),
    ("<think>maybe SELECT 0</think>\n```sql\nSELECT 7\n```", "SELECT 7"),
    ("First try:\n```sql\nSELECT 8\n```\nBetter:\n```sql\nSELECT 9\n```", "SELECT 9"),
    ("```sql\nWITH x AS (SELECT 1) SELECT * FROM x\n```", "WITH x AS (SELECT 1) SELECT * FROM x"),
    ("", ""),
]


@pytest.mark.parametrize(("raw", "expected"), CASES)
def test_extract_sql(raw: str, expected: str) -> None:
    assert extract_sql(raw) == expected


def test_variants_differ() -> None:
    schema = "TABLE ipl.matches\n    season SMALLINT"
    zero = build_messages("q?", "ipl", schema, "zero_shot")[1]["content"]
    few = build_messages("q?", "ipl", schema, "few_shot")[1]["content"]
    full = build_messages("q?", "ipl", schema, "full")[1]["content"]
    assert "EXAMPLES" not in zero and "METRIC" not in zero
    assert "EXAMPLES" in few and "METRIC" not in few
    assert "EXAMPLES" in full and "METRIC DEFINITIONS" in full
    assert full.endswith("QUESTION: q?")


def test_bad_variant() -> None:
    with pytest.raises(ValueError):
        build_messages("q", "ipl", "", "nonsense")


def test_retry_messages_include_error() -> None:
    msgs = build_retry_messages([{"role": "user", "content": "q"}], "SELECT x", "column x missing")
    assert msgs[-1]["role"] == "user" and "column x missing" in msgs[-1]["content"]
    assert msgs[-2]["role"] == "assistant"
