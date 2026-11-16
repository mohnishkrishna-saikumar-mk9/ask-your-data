"""Combine all benchmark runs into summary.csv, summary_difficulty.csv and summary.md (FR-19).

    python -m eval.summarize

For each (model, variant) only the most recent full run is used.
"""
import pandas as pd

from eval.run_eval import RESULTS_DIR


def latest_runs() -> pd.DataFrame:
    """Rows from the newest CSV per (model, variant). File names start with a timestamp."""
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for path in sorted(RESULTS_DIR.glob("2*_*.csv")):
        df = pd.read_csv(path)
        if df.empty:
            continue
        frames[(df["model"].iloc[0], df["variant"].iloc[0])] = df  # later files overwrite
    return pd.concat(frames.values(), ignore_index=True) if frames else pd.DataFrame()


def aggregate(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Accuracy, valid-SQL rate and latency per model x variant x `by` (plus an 'all' row)."""
    def stats(g: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "n": len(g), "accuracy": g["correct"].mean(), "valid_sql": g["valid_sql"].mean(),
            "retries": int((g["attempts"] > 1).sum()),
            "p50_ms": g["latency_ms"].quantile(0.5), "p95_ms": g["latency_ms"].quantile(0.95),
        })

    per = df.groupby(["model", "variant", by]).apply(stats, include_groups=False).reset_index()
    overall = df.groupby(["model", "variant"]).apply(stats, include_groups=False).reset_index()
    overall[by] = "all"
    return pd.concat([per, overall], ignore_index=True)


def to_markdown(summary: pd.DataFrame) -> str:
    """Model x variant table with accuracy per dataset and p50 latency."""
    table = summary.pivot_table(index=["model", "variant"], columns="dataset",
                                values="accuracy").reset_index()
    p50 = summary[summary["dataset"] == "all"].set_index(["model", "variant"])["p50_ms"]
    cols = [c for c in ["ipl", "ecommerce", "placements", "all"] if c in table.columns]
    lines = ["| Model | Prompt | " + " | ".join(cols) + " | p50 latency |",
             "|---|---|" + "---|" * len(cols) + "---|"]
    for _, r in table.sort_values("all", ascending=False).iterrows():
        accs = " | ".join(f"{r[c]:.0%}" for c in cols)
        lines.append(f"| {r['model']} | {r['variant']} | {accs} | "
                     f"{p50[(r['model'], r['variant'])] / 1000:.2f} s |")
    return "\n".join(lines)


def main() -> None:
    df = latest_runs()
    if df.empty:
        print("No result CSVs found in eval/results. Run eval.run_eval first.")
        return
    summary = aggregate(df, "dataset")
    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)
    aggregate(df, "difficulty").to_csv(RESULTS_DIR / "summary_difficulty.csv", index=False)
    md = "# Benchmark results\n\nExecution accuracy on the 100-question set.\n\n" + to_markdown(summary)
    (RESULTS_DIR / "summary.md").write_text(md + "\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
