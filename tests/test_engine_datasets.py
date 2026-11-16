"""The engine works the same way on every dataset (dataset-agnostic design, SPEC 9).

No real LLM is called: a fake model answers with that dataset's own few-shot SQL.
"""
from pathlib import Path

import pytest

from src import cache
from src.config import DATASETS
from src.db import run_query
from src.glossary import load_example_questions, load_few_shots
from src.guardrails import validate_sql
from src.text_to_sql import answer_question

SHOTS = [(ds, ex) for ds in DATASETS for ex in load_few_shots(ds)]


@pytest.mark.parametrize("dataset", list(DATASETS))
def test_knowledge_files_complete(dataset: str) -> None:
    assert 5 <= len(load_few_shots(dataset)) <= 8
    assert len(load_example_questions(dataset)) == 5


@pytest.mark.parametrize(("dataset", "example"), SHOTS,
                         ids=[f"{ds}:{ex['question'][:40]}" for ds, ex in SHOTS])
def test_few_shot_sql_passes_guardrails(dataset: str, example: dict) -> None:
    validate_sql(example["sql"], dataset)  # a bad example would teach the model bad SQL


@pytest.mark.db
@pytest.mark.parametrize(("dataset", "example"), SHOTS,
                         ids=[f"{ds}:{ex['question'][:40]}" for ds, ex in SHOTS])
def test_few_shot_sql_runs(dataset: str, example: dict, loaded_db: None) -> None:
    run_query(validate_sql(example["sql"], dataset), schema=dataset)


@pytest.fixture
def temp_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cache.get, "__defaults__", (tmp_path,))
    monkeypatch.setattr(cache.put, "__defaults__", (tmp_path,))


@pytest.mark.db
@pytest.mark.parametrize("dataset", list(DATASETS))
def test_end_to_end_on_every_dataset(dataset: str, loaded_db: None, temp_cache: None) -> None:
    example = load_few_shots(dataset)[0]
    prompts: list[str] = []

    def fake_llm(messages: list[dict], model: str) -> tuple[str, float]:
        prompts.append(messages[-1]["content"])
        return f"```sql\n{example['sql']}\n```", 1.0

    ans = answer_question("any question", dataset, "fake:model", "full", llm=fake_llm,
                          fallback=False)
    assert ans.ok, ans.error
    assert ans.attempts == 1 and "LIMIT" in ans.sql.upper().split()  # guardrails always leave a LIMIT
    prompt = prompts[0]
    assert f"SCHEMA ({dataset})" in prompt and "METRIC DEFINITIONS" in prompt and "EXAMPLES" in prompt
    # The model only ever sees the selected dataset's tables.
    others = [ds for ds in DATASETS if ds != dataset and f"TABLE {ds}." in prompt]
    assert not others


@pytest.mark.db
def test_guardrail_rewrite_preserves_results(loaded_db: None) -> None:
    """Guardrails re-render SQL with sqlglot and we run *that* text, so the rewrite must never
    change an answer. Checked on all 72 hand-written analysis queries."""
    from eval.compare import has_order_by, results_match
    from src.sql_library import list_queries

    for ds in DATASETS:
        for q in list_queries(ds):
            raw = run_query(q.sql, schema=ds)
            new = run_query(validate_sql(q.sql, ds), schema=ds)
            assert list(raw.columns) == list(new.columns), q.path.name
            assert results_match(raw.head(len(new)), new, ordered=has_order_by(q.sql)), q.path.name
