"""Run the whole comparison: every model in EVAL_MODELS x every prompt variant (FR-19).

    python -m eval.run_all                 # all models x all variants
    python -m eval.run_all --sleep 2       # pause between questions (free-tier rate limits)

Runs one after another, then rebuilds summary.md. A run that crashes is reported and the next
one still starts. Stop any time with Ctrl+C; finished runs are kept.
"""
import argparse
import time

from eval import summarize
from eval.run_eval import run
from src.config import EVAL_MODELS
from src.llm.prompts import VARIANTS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=VARIANTS)
    args = parser.parse_args()
    if not EVAL_MODELS:
        raise SystemExit("Set EVAL_MODELS in .env (comma-separated provider:model_id list).")

    plan = [(m, v) for m in EVAL_MODELS for v in args.variants]
    print(f"{len(plan)} runs: {len(EVAL_MODELS)} models x {len(args.variants)} prompt variants\n")
    for i, (model, variant) in enumerate(plan, 1):
        print(f"\n=== Run {i}/{len(plan)}: {model} | {variant} ===")
        start = time.perf_counter()
        try:
            run(model, variant, sleep=args.sleep)
        except Exception as err:  # keep going: one broken run must not lose the others
            print(f"Run failed: {err}")
        print(f"(run took {(time.perf_counter() - start) / 60:.1f} min)")

    print("\n=== Summary ===")
    summarize.main()


if __name__ == "__main__":
    main()
