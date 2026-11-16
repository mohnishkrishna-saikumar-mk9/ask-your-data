"""Run the benchmark for one model + prompt variant (FR-18).

    python -m eval.run_eval --model groq:llama-3.3-70b-versatile --prompt full
    python -m eval.run_eval --model gemini:gemini-2.0-flash --prompt zero_shot --dataset ipl --limit 10

Writes eval/results/<timestamp>_<model>_<variant>.csv (one row per question) and prints a summary.
Then run `python -m eval.summarize` to rebuild summary.md / summary.csv for all runs.
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from eval.compare import has_order_by, results_match
from src.db import run_query
from src.llm.client import CompleteFn, complete
from src.llm.prompts import VARIANTS
from src.text_to_sql import answer_question

EVAL_DIR = Path(__file__).resolve().parent
QUESTIONS_DIR = EVAL_DIR / "questions"
RESULTS_DIR = EVAL_DIR / "results"


def load_questions(dataset: str | None = None) -> list[dict]:
    """All benchmark questions, optionally for one dataset."""
    files = [QUESTIONS_DIR / f"{dataset}.jsonl"] if dataset else sorted(QUESTIONS_DIR.glob("*.jsonl"))
    questions = []
    for path in files:
        questions += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                      if line.strip()]
    return questions


def evaluate_one(q: dict, model: str, variant: str, llm: CompleteFn = complete) -> dict:
    """Ask the model one question and score it against the gold SQL."""
    gold = run_query(q["gold_sql"], schema=q["dataset"])
    ans = answer_question(q["question"], q["dataset"], model, variant, llm=llm,
                          use_cache=False, fallback=False)
    correct = ans.ok and results_match(gold, ans.df, ordered=has_order_by(q["gold_sql"]))
    return {
        "id": q["id"], "dataset": q["dataset"], "difficulty": q["difficulty"],
        "model": model, "variant": variant, "correct": bool(correct),
        "valid_sql": ans.ok, "guardrail_rejected": ans.error_kind == "guardrail",
        "llm_error": ans.error_kind == "llm", "attempts": ans.attempts,
        "llm_ms": round(ans.llm_ms), "db_ms": round(ans.db_ms),
        "latency_ms": round(ans.llm_ms + ans.db_ms),
        "error": (ans.error or "")[:300], "pred_sql": ans.sql,
    }


def print_summary(df: pd.DataFrame) -> None:
    """Accuracy and latency overall and per dataset / difficulty."""
    print(f"\nExecution accuracy: {df['correct'].mean():.1%}  "
          f"valid SQL: {df['valid_sql'].mean():.1%}  "
          f"guardrail rejections: {int(df['guardrail_rejected'].sum())}  "
          f"retries used: {int((df['attempts'] > 1).sum())}")
    print(f"Latency p50 {df['latency_ms'].quantile(0.5):,.0f} ms, "
          f"p95 {df['latency_ms'].quantile(0.95):,.0f} ms")
    for col in ("dataset", "difficulty"):
        print(df.groupby(col)["correct"].agg(["mean", "count"])
              .rename(columns={"mean": "accuracy"}).round(3).to_string(), "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True, help="provider:model_id")
    parser.add_argument("--prompt", default="full", choices=VARIANTS)
    parser.add_argument("--dataset", choices=["ipl", "ecommerce", "placements"])
    parser.add_argument("--limit", type=int, help="only the first N questions (smoke test)")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="seconds to wait between questions (free-tier rate limits)")
    args = parser.parse_args()

    questions = load_questions(args.dataset)[: args.limit]
    rows = []
    for i, q in enumerate(questions, 1):
        row = evaluate_one(q, args.model, args.prompt)
        rows.append(row)
        mark = "OK " if row["correct"] else "BAD"
        print(f"[{i:3}/{len(questions)}] {mark} {q['id']} {row['latency_ms']:6} ms  {row['error'][:60]}")
        time.sleep(args.sleep)

    df = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = re.sub(r"[^A-Za-z0-9.-]+", "-", args.model)
    out = RESULTS_DIR / f"{stamp}_{safe_model}_{args.prompt}.csv"
    df.to_csv(out, index=False)
    print_summary(df)
    print(f"Saved {out.relative_to(EVAL_DIR.parent)}")


if __name__ == "__main__":
    main()
