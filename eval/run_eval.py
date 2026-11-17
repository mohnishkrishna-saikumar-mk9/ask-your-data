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
from functools import lru_cache
from pathlib import Path

import pandas as pd

from eval.compare import has_order_by, order_columns, results_match
from src.config import DATASETS
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


@lru_cache(maxsize=1)
def table_counts() -> dict[str, int]:
    """Number of base tables per dataset schema (for 'accuracy vs number of tables')."""
    df = run_query("SELECT table_schema, COUNT(*) AS n FROM information_schema.tables "
                   "WHERE table_type = 'BASE TABLE' AND table_schema = ANY(:s) GROUP BY 1",
                   {"s": list(DATASETS)})
    return dict(zip(df["table_schema"], df["n"].astype(int), strict=True))


def answer_is_correct(q: dict, gold: pd.DataFrame, pred: pd.DataFrame) -> bool:
    """Score one answer with the question's own rules (see eval/questions/*.jsonl):
    `ordered` - must the row order match? (default: only if the gold SQL has ORDER BY);
    `key_columns` - which gold columns must be present (default: all)."""
    ordered = q.get("ordered", has_order_by(q["gold_sql"]))
    sort_keys = order_columns(q["gold_sql"], gold) if ordered else None
    return results_match(gold, pred, ordered=ordered, sort_keys=sort_keys,
                         key_columns=q.get("key_columns"))


def evaluate_one(q: dict, model: str, variant: str, llm: CompleteFn = complete) -> dict:
    """Ask the model one question and score it against the gold SQL."""
    gold = run_query(q["gold_sql"], schema=q["dataset"])
    ans = answer_question(q["question"], q["dataset"], model, variant, llm=llm,
                          use_cache=False, fallback=False)
    correct = ans.ok and answer_is_correct(q, gold, ans.df)
    return {
        "id": q["id"], "dataset": q["dataset"], "n_tables": table_counts().get(q["dataset"]),
        "difficulty": q["difficulty"],
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
          f"retries used: {int((df['attempts'] > 1).sum())}  "
          f"LLM/provider errors: {int(df['llm_error'].sum())}")
    print(f"Latency p50 {df['latency_ms'].quantile(0.5):,.0f} ms, "
          f"p95 {df['latency_ms'].quantile(0.95):,.0f} ms")
    for col in ("dataset", "difficulty"):
        print(df.groupby(col)["correct"].agg(["mean", "count"])
              .rename(columns={"mean": "accuracy"}).round(3).to_string(), "\n")


RATE_LIMIT_WAITS = (30, 60, 120)  # seconds to wait before retrying a rate-limited question


def is_rate_limited(row: dict) -> bool:
    """The provider refused for quota reasons - not the model's mistake, so retry it."""
    text = row["error"].lower()
    return row["llm_error"] and any(s in text for s in ("429", "rate limit", "rate_limit", "too many"))


class DailyQuotaExhausted(RuntimeError):
    """The provider's per-day limit is used up; waiting minutes will not help."""


def is_daily_quota(row: dict) -> bool:
    text = row["error"].lower()
    return row["llm_error"] and any(s in text for s in ("per day", "tpd", "rpd", "daily"))


def evaluate_with_retry(q: dict, model: str, variant: str) -> dict:
    """evaluate_one, waiting and retrying when the provider rate-limits us per minute.
    A daily limit raises DailyQuotaExhausted instead, so the caller can stop this run."""
    row = evaluate_one(q, model, variant)
    for wait in RATE_LIMIT_WAITS:
        if is_daily_quota(row):
            raise DailyQuotaExhausted(row["error"][:200])
        if not is_rate_limited(row):
            break
        print(f"      rate limited - waiting {wait}s and retrying {q['id']}")
        time.sleep(wait)
        row = evaluate_one(q, model, variant)
    if is_daily_quota(row):
        raise DailyQuotaExhausted(row["error"][:200])
    return row


def run_file(model: str, variant: str) -> Path | None:
    """The newest saved CSV for this model + variant, if any."""
    safe_model = re.sub(r"[^A-Za-z0-9.-]+", "-", model)
    files = sorted(RESULTS_DIR.glob(f"2*_{safe_model}_{variant}.csv"))
    return files[-1] if files else None


def load_progress(path: Path | None) -> list[dict]:
    """Rows already answered in a saved run, minus rate-limited ones (those are redone)."""
    if path is None or not path.exists():
        return []
    df = pd.read_csv(path, dtype={"error": str}, keep_default_na=False)  # empty error = ""
    return [r for r in df.to_dict("records") if not is_rate_limited(r)]


def run(model: str, variant: str, dataset: str | None = None, limit: int | None = None,
        sleep: float = 0.0, resume: bool = False) -> Path:
    """Evaluate one model + prompt variant. The CSV is saved after every question.

    resume=True continues the newest saved run for this model + variant in the same file:
    answered questions are kept, rate-limited ones are asked again. A daily-quota error stops
    the run (raising DailyQuotaExhausted); run it again later with resume to finish it.
    """
    questions = load_questions(dataset)[:limit]
    RESULTS_DIR.mkdir(exist_ok=True)
    previous = run_file(model, variant) if resume else None
    if previous:
        out = previous
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"{stamp}_{re.sub(r'[^A-Za-z0-9.-]+', '-', model)}_{variant}.csv"
    rows = load_progress(previous)
    done = {r["id"] for r in rows}
    todo = [q for q in questions if q["id"] not in done]
    if previous:
        print(f"Resuming {out.name}: {len(done)} answered, {len(todo)} to go")
    for q in todo:
        row = evaluate_with_retry(q, model, variant)
        rows.append(row)
        pd.DataFrame(rows).to_csv(out, index=False)
        mark = "OK " if row["correct"] else ("ERR" if row["llm_error"] else "BAD")
        print(f"[{len(rows):3}/{len(questions)}] {mark} {q['id']} {row['latency_ms']:6} ms  "
              f"{row['error'][:60]}")
        time.sleep(sleep)
    if rows:
        print_summary(pd.DataFrame(rows))
    print(f"Saved {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True, help="provider:model_id")
    parser.add_argument("--prompt", default="full", choices=VARIANTS)
    parser.add_argument("--dataset", choices=list(DATASETS))
    parser.add_argument("--limit", type=int, help="only the first N questions (smoke test)")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="seconds to wait between questions (free-tier rate limits)")
    parser.add_argument("--resume", action="store_true",
                        help="continue the newest saved run for this model + prompt")
    args = parser.parse_args()
    try:
        run(args.model, args.prompt, args.dataset, args.limit, args.sleep, args.resume)
    except DailyQuotaExhausted as err:
        raise SystemExit(f"Stopped: daily quota used up ({err}). Rerun later with --resume.") from err


if __name__ == "__main__":
    main()
