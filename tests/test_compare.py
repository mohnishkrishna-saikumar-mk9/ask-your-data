"""Comparator tests (execution accuracy) + benchmark file checks."""
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from eval.compare import has_order_by, normalise_value, order_columns, results_match
from eval.run_eval import load_questions
from src.config import DATASETS
from src.db import run_query
from src.glossary import load_few_shots
from src.guardrails import validate_sql

QUESTIONS = load_questions()


def df(**cols: list) -> pd.DataFrame:
    return pd.DataFrame(cols)


def test_normalise_value() -> None:
    assert normalise_value(Decimal("5.000")) == normalise_value(5) == normalise_value(5.0)
    assert normalise_value(0.1 + 0.2) == Decimal("0.3")  # binary float noise removed
    assert normalise_value("  x ") == "x"
    assert normalise_value(None) is None and normalise_value(float("nan")) is None


@pytest.mark.parametrize(("gold", "pred", "same"), [
    (Decimal("12.5"), 12.4637, True),     # gold rounded to 1 dp, model did not round
    (Decimal("12.5"), 12.46, True),
    (12.4637, Decimal("12.5"), True),     # gold unrounded, model rounded to 1 dp
    (Decimal("12.5"), 12.4, False),       # different at the shared precision
    (Decimal("12.5"), 0.125, False),      # fraction vs percentage is a different answer
    (1046, 1047, False),                  # whole numbers (counts) must match exactly
    (Decimal("288655"), 288654.7, True),  # gold rounded to 0 dp
    (Decimal("135.456"), 135.4612, False),
])
def test_precision_aware_numbers(gold: object, pred: object, same: bool) -> None:
    assert results_match(df(x=[gold]), df(y=[pred])) is same


def test_row_order_ignored_without_order_by() -> None:
    assert results_match(df(a=[1, 2]), df(a=[2, 1]))


def test_row_order_required_with_order_by() -> None:
    assert not results_match(df(a=[1, 2]), df(a=[2, 1]), ordered=True)
    assert results_match(df(a=[1, 2]), df(a=[1, 2]), ordered=True)


def test_column_order_and_names_ignored() -> None:
    assert results_match(df(team=["A", "B"], wins=[3, 1]), df(n=[3, 1], name=["A", "B"]))


def test_types_mixed_int_float_decimal() -> None:
    assert results_match(df(n=[3, 1]), df(n=[Decimal("3.00"), 1.0]))
    assert results_match(df(d=[pd.Timestamp("2022-04-01")]), df(d=["2022-04-01"]))


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
    """20 questions per dataset (FR-17), unique ids, ~30% easy / 45% medium / 25% hard."""
    counts = pd.Series([q["dataset"] for q in QUESTIONS]).value_counts().to_dict()
    assert counts == {ds: 20 for ds in DATASETS}
    assert len({q["id"] for q in QUESTIONS}) == 160
    for ds in DATASETS:
        mix = pd.Series([q["difficulty"] for q in QUESTIONS if q["dataset"] == ds]).value_counts()
        assert mix.to_dict() == {"easy": 6, "medium": 9, "hard": 5}, ds


def test_eval_questions_not_in_few_shots() -> None:
    """No leakage: a few-shot example in the prompt must never be a benchmark question."""
    for ds in DATASETS:
        shots = {ex["question"].lower().strip() for ex in load_few_shots(ds)}
        assert not shots & {q["question"].lower().strip() for q in QUESTIONS if q["dataset"] == ds}


def test_jsonl_is_valid() -> None:
    for path in Path("eval/questions").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert set(json.loads(line)) == {"id", "dataset", "difficulty", "question", "gold_sql"}


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_gold_sql_passes_guardrails(q: dict) -> None:
    """A model that wrote exactly the gold SQL must not be rejected (e.g. reserved-word aliases)."""
    validate_sql(q["gold_sql"], q["dataset"])


@pytest.mark.db
@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_gold_sql_runs(q: dict, loaded_db: None) -> None:
    run_query(q["gold_sql"], schema=q["dataset"])


@pytest.mark.db
def test_perfect_model_full_run_and_summary(loaded_db: None, tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Every question is answerable through the full pipeline (100%), and summarize publishes
    only complete runs - a partial smoke run must never replace a full one."""
    from eval import run_eval, summarize

    gold = {q["question"]: q["gold_sql"] for q in QUESTIONS}

    def perfect_llm(messages: list[dict], model: str) -> tuple[str, float]:
        question = messages[-1]["content"].rsplit("QUESTION: ", 1)[1]
        return f"```sql\n{gold[question]}\n```", 10.0

    rows = pd.DataFrame([run_eval.evaluate_one(q, "fake:perfect", "full", llm=perfect_llm)
                         for q in QUESTIONS])
    assert rows["correct"].all(), rows.loc[~rows["correct"], "id"].tolist()
    assert rows["n_tables"].notna().all()

    monkeypatch.setattr(summarize, "RESULTS_DIR", tmp_path)
    rows.to_csv(tmp_path / "20260101_000000_fake-perfect_full.csv", index=False)
    rows.head(10).assign(correct=False).to_csv(tmp_path / "20260102_000000_fake-perfect_full.csv",
                                               index=False)  # later, partial, all wrong
    summarize.main()
    md = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| fake:perfect | full |" in md and "100%" in md and "Accuracy vs number of tables" in md
    assert "skipped partial run 20260102" in capsys.readouterr().out


def test_ties_on_sort_key_may_appear_in_any_order() -> None:
    gold = df(city=["A", "B", "C"], pct=[50, 50, 10])  # A and B tie on the sort key
    swapped = df(city=["B", "A", "C"], pct=[50, 50, 10])
    keys = order_columns("SELECT city, pct FROM t ORDER BY pct DESC", gold)
    assert keys == [1]
    assert results_match(gold, swapped, ordered=True, sort_keys=keys)
    assert not results_match(gold, df(city=["C", "A", "B"], pct=[10, 50, 50]), ordered=True,
                             sort_keys=keys)  # wrongly sorted
    assert not results_match(gold, swapped, ordered=True)  # strict full-row order still available


def test_order_columns() -> None:
    result = df(a=[1], b=[2])
    assert order_columns("SELECT a, b FROM t ORDER BY 2, a", result) == [1, 0]
    assert order_columns("SELECT a, b FROM t ORDER BY c", result) is None  # key not in output
    assert order_columns("SELECT a, b FROM t", result) is None
