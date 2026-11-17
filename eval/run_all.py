"""Run the whole comparison: every model in EVAL_MODELS x every prompt variant (FR-19).

    python -m eval.run_all                       # all models x all variants, resuming
    python -m eval.run_all --models omniroute:gemini/gemini-flash-lite-latest
    python -m eval.run_all --sleep 2             # pause between questions

Always resumes: finished runs are skipped, unfinished ones continue in the same file. When a
provider's daily quota is used up, that run stops and the next model starts - so running this
once a day finishes everything on free tiers. Rebuilds summary.md at the end.
"""
import argparse
import time

from eval import summarize
from eval.run_eval import DailyQuotaExhausted, load_progress, load_questions, run, run_file
from src.config import EVAL_MODELS
from src.llm.prompts import VARIANTS


def is_complete(model: str, variant: str, total: int) -> bool:
    """True if the saved run for this model + variant has every question answered."""
    return len(load_progress(run_file(model, variant))) >= total


def main() -> None:
    """Run every model x prompt variant (resuming), then rebuild the summary."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--models", nargs="+", default=EVAL_MODELS)
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=VARIANTS)
    args = parser.parse_args()
    if not args.models:
        raise SystemExit("Set EVAL_MODELS in .env (comma-separated provider:model_id list).")

    total = len(load_questions())
    plan = [(m, v) for m in args.models for v in args.variants]
    waiting: list[str] = []
    for i, (model, variant) in enumerate(plan, 1):
        print(f"\n=== Run {i}/{len(plan)}: {model} | {variant} ===")
        if is_complete(model, variant, total):
            print("already complete - skipped")
            continue
        start = time.perf_counter()
        try:
            run(model, variant, sleep=args.sleep, resume=True)
        except DailyQuotaExhausted as err:
            print(f"Daily quota used up - progress saved, resume tomorrow. ({err})")
            waiting.append(f"{model} | {variant}")
        except Exception as err:  # keep going: one broken run must not lose the others
            print(f"Run failed: {err}")
            waiting.append(f"{model} | {variant}")
        print(f"(run took {(time.perf_counter() - start) / 60:.1f} min)")

    print("\n=== Summary ===")
    summarize.main()
    if waiting:
        print("\nNot finished yet (run `python -m eval.run_all` again later):")
        print("\n".join(f"  - {w}" for w in waiting))


if __name__ == "__main__":
    main()
