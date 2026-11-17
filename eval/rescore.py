"""Re-score saved benchmark runs with the current questions and comparator - no LLM calls.

    python -m eval.rescore            # every CSV in eval/results
    python -m eval.rescore FILE.csv   # just one run

Each run CSV keeps the exact SQL the model produced (`pred_sql`, already through the guardrails).
When a scoring rule or a gold answer is fixed, re-running that SQL and comparing again gives the
corrected score without asking the model anything new.
"""
import sys
from pathlib import Path

import pandas as pd

from eval.run_eval import RESULTS_DIR, answer_is_correct, load_questions
from src.db import run_query


def rescore_file(path: Path, questions: dict[str, dict]) -> tuple[int, int]:
    """Recompute `correct` for one run; returns (correct before, correct after)."""
    df = pd.read_csv(path)
    before = int(df["correct"].sum())
    gold_cache: dict[str, pd.DataFrame] = {}
    for i, row in df.iterrows():
        q = questions[row["id"]]
        if not row["valid_sql"] or not isinstance(row["pred_sql"], str):
            continue  # failed or rejected answers stay wrong
        if q["id"] not in gold_cache:
            gold_cache[q["id"]] = run_query(q["gold_sql"], schema=q["dataset"])
        try:
            pred = run_query(row["pred_sql"], schema=q["dataset"])
        except Exception:  # e.g. a timeout: keep the original verdict
            continue
        df.at[i, "correct"] = bool(answer_is_correct(q, gold_cache[q["id"]], pred))
    df.to_csv(path, index=False)
    return before, int(df["correct"].sum())


def main() -> None:
    """Re-score the CSV files given on the command line, or every saved run."""
    questions = {q["id"]: q for q in load_questions()}
    paths = [Path(p) for p in sys.argv[1:]] or sorted(RESULTS_DIR.glob("2*_*.csv"))
    for path in paths:
        before, after = rescore_file(path, questions)
        print(f"{path.name}: {before} -> {after} correct")


if __name__ == "__main__":
    main()
