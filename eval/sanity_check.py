"""Check the benchmark itself before trusting any model's score.

    python -m eval.sanity_check            # needs the real data loaded

1. Perfect model: answers every question with its own gold SQL through the full pipeline
   (prompt -> guardrails rewrite -> read-only run -> comparator). Must score 100%; anything less
   means a question cannot be answered correctly even in principle.
2. Negative control: answers each question with the gold SQL of a *different* question from the
   same dataset. Should score ~0%; a high score means the comparator is too lenient.

Run it after adding or editing questions. No LLM is called.
"""
from eval.run_eval import evaluate_one, load_questions


def _question_from(messages: list[dict]) -> str:
    return messages[-1]["content"].rsplit("QUESTION: ", 1)[1]


def run_check(answers: dict[str, str], label: str, questions: list[dict]) -> list[str]:
    """Score a fake model that returns `answers[question]`; return ids marked correct."""
    def fake(messages: list[dict], model: str) -> tuple[str, float]:
        return f"```sql\n{answers[_question_from(messages)]}\n```", 0.0

    rows = [evaluate_one(q, f"check:{label}", "full", llm=fake) for q in questions]
    return [r["id"] for r in rows if r["correct"]]


def main() -> None:
    questions = load_questions()
    perfect = {q["question"]: q["gold_sql"] for q in questions}
    wrong: dict[str, str] = {}
    for dataset in {q["dataset"] for q in questions}:
        same = [q for q in questions if q["dataset"] == dataset]
        for i, q in enumerate(same):
            wrong[q["question"]] = same[(i + 1) % len(same)]["gold_sql"]

    ok = run_check(perfect, "perfect", questions)
    missed = sorted({q["id"] for q in questions} - set(ok))
    print(f"Perfect model:    {len(ok)}/{len(questions)} correct  (expected all) {missed or ''}")
    accepted = run_check(wrong, "wrong", questions)
    print(f"Negative control: {len(accepted)}/{len(questions)} correct  (expected ~0) {accepted or ''}")
    if missed or len(accepted) > len(questions) * 0.02:
        raise SystemExit("Benchmark check FAILED - fix the questions or the comparator first.")
    print("Benchmark check passed.")


if __name__ == "__main__":
    main()
