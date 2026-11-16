"""Comparator tests (execution accuracy) + benchmark file checks."""
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from eval.compare import has_order_by, normalise_value, results_match
from eval.run_eval import load_questions
from src.db import run_query
from src.glossary import load_few_shots

QUESTIONS = load_questions()


def df(**cols: list) -> pd.DataFrame:
    return pd.DataFrame(cols)


def test_normalise_value() -> None:
    assert normalise_value(Decimal("5.000")) == normalise_value(5) == 5.0
    assert normalise_value(3.14159) == 3.14
    assert normalise_value("  x ") == "x"
    assert normalise_value(None) is None and normalise_value(float("nan")) is None


def test_row_order_ignored_without_order_by() -> None:
    assert results_match(df(a=[1, 2]), df(a=[2, 1]))


def test_row_order_required_with_order_by() -> None:
    assert not results_match(df(a=[1, 2]), df(a=[2, 1]), ordered=True)
    assert results_match(df(a=[1, 2]), df(a=[1, 2]), ordered=True)


def test_column_order_and_names_ignored() -> None:
    assert results_match(df(team=["A", "B"], wins=[3, 1]), df(n=[3, 1], name=["A", "B"]))


def test_rounding_and_types() -> None:
    assert results_match(df(sr=[Decimal("135.456")]), df(x=[135.4612]))


def test_extra_predicted_column_allowed() -> None:
    assert results_match(df(team=["A", "B"]), df(team=["A", "B"], wins=[3, 1]))


def test_different_values_fail() -> None:
    assert not results_match(df(a=[1, 2]), df(a=[1, 3]))
    assert not results_match(df(a=[1, 2]), df(a=[1]))
    assert not results_match(df(a=[1], b=[2]), df(a=[1]))


def test_duplicates_count() -> None:
    assert not results_match(df(a=[1, 1, 2]), df(a=[1, 2, 2]))


def test_has_order_by() -> None:
    assert has_order_by("SELECT a FROM t ORDER BY a")
    assert not has_order_by("SELECT a FROM (SELECT a FROM t ORDER BY a) s")


def test_benchmark_size_and_mix() -> None:
    counts = pd.Series([q["dataset"] for q in QUESTIONS]).value_counts().to_dict()
    assert counts == {"ipl": 50, "ecommerce": 25, "placements": 25}
    assert len({q["id"] for q in QUESTIONS}) == 100
    assert {q["difficulty"] for q in QUESTIONS} == {"easy", "medium", "hard"}


def test_eval_questions_not_in_few_shots() -> None:
    for ds in ("ipl", "ecommerce", "placements"):
        shots = {ex["question"].lower().strip() for ex in load_few_shots(ds)}
        assert not shots & {q["question"].lower().strip() for q in QUESTIONS if q["dataset"] == ds}


def test_jsonl_is_valid() -> None:
    for path in Path("eval/questions").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert set(json.loads(line)) == {"id", "dataset", "difficulty", "question", "gold_sql"}


@pytest.mark.db
@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_gold_sql_runs(q: dict, loaded_db: None) -> None:
    run_query(q["gold_sql"], schema=q["dataset"])


@pytest.mark.db
def test_eval_pipeline_with_perfect_fake_model(loaded_db: None, tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """A fake model that returns the gold SQL must score 100%; summarize must build tables."""
    from eval import run_eval, summarize

    sample = [q for q in QUESTIONS if q["difficulty"] == "medium"][:6]
    gold_by_question = {q["question"]: q["gold_sql"] for q in sample}

    def perfect_llm(messages: list[dict], model: str) -> tuple[str, float]:
        question = messages[-1]["content"].rsplit("QUESTION: ", 1)[1]
        return f"```sql\n{gold_by_question[question]}\n```", 10.0

    rows = [run_eval.evaluate_one(q, "fake:perfect", "full", llm=perfect_llm) for q in sample]
    assert all(r["correct"] for r in rows)

    monkeypatch.setattr(summarize, "RESULTS_DIR", tmp_path)
    pd.DataFrame(rows).to_csv(tmp_path / "20260101_000000_fake_full.csv", index=False)
    summarize.main()
    assert "| fake:perfect | full |" in (tmp_path / "summary.md").read_text(encoding="utf-8")
