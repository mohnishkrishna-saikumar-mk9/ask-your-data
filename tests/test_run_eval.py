"""Benchmark runner: resume after interruption, retries, and stopping on a daily quota.

No database or model is used: evaluate_one is replaced by a fake.
"""
from pathlib import Path

import pandas as pd
import pytest

from eval import run_eval

QUESTIONS = [{"id": f"q{i}", "dataset": "placements", "difficulty": "easy", "question": f"Q{i}?",
              "gold_sql": "SELECT 1"} for i in range(1, 6)]
TPD_ERROR = "Error code: 429 - Rate limit reached on tokens per day (TPD): Limit 200000"
TPM_ERROR = "Error code: 429 - Rate limit reached on tokens per minute"


def row(q: dict, error: str = "") -> dict:
    return {"id": q["id"], "dataset": q["dataset"], "n_tables": 1, "difficulty": "easy",
            "model": "fake:m", "variant": "full", "correct": not error, "valid_sql": not error,
            "guardrail_rejected": False, "llm_error": bool(error), "attempts": 1, "llm_ms": 1,
            "db_ms": 1, "latency_ms": 2, "error": error, "pred_sql": "SELECT 1"}


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    """Fake environment: 5 questions, results in tmp_path, no waiting, scripted answers."""
    script: dict[str, list[str]] = {}  # question id -> errors to return, in order ("" = answer)
    calls: list[str] = []

    def fake_evaluate(q: dict, model: str, variant: str) -> dict:
        calls.append(q["id"])
        errors = script.get(q["id"], [])
        return row(q, errors.pop(0) if errors else "")

    monkeypatch.setattr(run_eval, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(run_eval, "load_questions", lambda dataset=None: QUESTIONS)
    monkeypatch.setattr(run_eval, "evaluate_one", fake_evaluate)
    monkeypatch.setattr(run_eval, "RATE_LIMIT_WAITS", (0, 0, 0))
    monkeypatch.setattr(run_eval.time, "sleep", lambda s: None)
    return {"script": script, "calls": calls, "dir": tmp_path}


def test_per_minute_limit_is_retried(runner: dict) -> None:
    runner["script"]["q2"] = [TPM_ERROR, TPM_ERROR]  # fails twice, then answers
    out = run_eval.run("fake:m", "full")
    df = pd.read_csv(out)
    assert len(df) == 5 and df["correct"].all()
    assert runner["calls"].count("q2") == 3


def test_daily_quota_stops_run_and_resume_finishes_it(runner: dict) -> None:
    runner["script"]["q3"] = [TPD_ERROR]
    with pytest.raises(run_eval.DailyQuotaExhausted):
        run_eval.run("fake:m", "full", resume=True)
    first = run_eval.run_file("fake:m", "full")
    assert pd.read_csv(first)["id"].tolist() == ["q1", "q2"]  # progress saved before stopping

    runner["calls"].clear()
    out = run_eval.run("fake:m", "full", resume=True)  # "the next day"
    assert out == first                                  # same file, continued
    assert runner["calls"] == ["q3", "q4", "q5"]         # answered questions are not asked again
    assert pd.read_csv(out)["id"].tolist() == ["q1", "q2", "q3", "q4", "q5"]


def test_resume_redoes_rate_limited_rows(runner: dict) -> None:
    path = runner["dir"] / "20260101_000000_fake-m_full.csv"
    pd.DataFrame([row(QUESTIONS[0]), row(QUESTIONS[1], TPM_ERROR)]).to_csv(path, index=False)
    run_eval.run("fake:m", "full", resume=True)
    assert runner["calls"] == ["q2", "q3", "q4", "q5"]
    assert pd.read_csv(path)["correct"].all()


def test_without_resume_a_new_file_is_started(runner: dict) -> None:
    path = runner["dir"] / "20260101_000000_fake-m_full.csv"
    pd.DataFrame([row(QUESTIONS[0])]).to_csv(path, index=False)
    out = run_eval.run("fake:m", "full")
    assert out != path and len(runner["calls"]) == 5
