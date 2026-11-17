"""Combine benchmark runs into summary.csv, summary_difficulty.csv and summary.md (FR-19).

    python -m eval.summarize

For each (model, variant) the most recent *complete* run is used (one row per benchmark
question). Partial runs - e.g. `--limit 10` smoke tests - are listed and skipped, so they can
never replace a full run in the published numbers.
"""
import pandas as pd

from eval.run_eval import RESULTS_DIR, load_questions
from src.config import DATASETS


def latest_runs(expected: int | None = None) -> pd.DataFrame:
    """Rows from the newest complete CSV per (model, variant). File names start with a timestamp."""
    expected = expected or len(load_questions())
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for path in sorted(RESULTS_DIR.glob("2*_*.csv")):
        df = pd.read_csv(path)
        if len(df) != expected:
            print(f"  skipped partial run {path.name} ({len(df)} of {expected} questions)")
            continue
        frames[(df["model"].iloc[0], df["variant"].iloc[0])] = df  # later files overwrite
    return pd.concat(frames.values(), ignore_index=True) if frames else pd.DataFrame()


def aggregate(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Accuracy, valid-SQL rate and latency per model x variant x `by` (plus an 'all' row)."""
    def stats(g: pd.DataFrame) -> pd.Series:
        """Metrics for one group of benchmark rows."""
        return pd.Series({
            "n": len(g), "accuracy": g["correct"].mean(), "valid_sql": g["valid_sql"].mean(),
            "retries": int((g["attempts"] > 1).sum()),
            "p50_ms": g["latency_ms"].quantile(0.5), "p95_ms": g["latency_ms"].quantile(0.95),
        })

    per = df.groupby(["model", "variant", by]).apply(stats, include_groups=False).reset_index()
    overall = df.groupby(["model", "variant"]).apply(stats, include_groups=False).reset_index()
    overall[by] = "all"
    out = pd.concat([per, overall], ignore_index=True)
    if by == "dataset" and "n_tables" in df.columns:
        tables = df.groupby("dataset")["n_tables"].first()
        out["n_tables"] = out["dataset"].map(tables)
    return out


def to_markdown(summary: pd.DataFrame) -> str:
    """Model x variant table: accuracy per dataset (ordered by number of tables) and p50 latency."""
    table = summary.pivot_table(index=["model", "variant"], columns="dataset",
                                values="accuracy").reset_index()
    p50 = summary[summary["dataset"] == "all"].set_index(["model", "variant"])["p50_ms"]
    cols = [c for c in [*DATASETS, "all"] if c in table.columns]
    lines = ["| Model | Prompt | " + " | ".join(cols) + " | p50 latency |",
             "|---|---|" + "---|" * len(cols) + "---|"]
    for _, r in table.sort_values("all", ascending=False).iterrows():
        accs = " | ".join(f"{r[c]:.0%}" for c in cols)
        lines.append(f"| {r['model']} | {r['variant']} | {accs} | "
                     f"{p50[(r['model'], r['variant'])] / 1000:.2f} s |")
    return "\n".join(lines)


def tables_markdown(summary: pd.DataFrame) -> str:
    """Accuracy by schema size: one row per dataset sorted by number of tables."""
    per = summary[summary["dataset"] != "all"].copy()
    if "n_tables" not in per.columns:
        return ""
    per["run"] = per["model"] + " · " + per["variant"]
    table = per.pivot_table(index=["n_tables", "dataset"], columns="run", values="accuracy")
    table = table.sort_index()
    runs = list(table.columns)
    lines = ["| Tables | Dataset | " + " | ".join(runs) + " |", "|---|---|" + "---|" * len(runs)]
    for (n_tables, dataset), row in table.iterrows():
        lines.append(f"| {int(n_tables)} | {dataset} | " + " | ".join(f"{v:.0%}" for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    """Write summary.csv, summary_difficulty.csv and summary.md from complete runs."""
    df = latest_runs()
    if df.empty:
        print("No complete result CSVs found in eval/results. Run eval.run_eval first.")
        return
    summary = aggregate(df, "dataset")
    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)
    aggregate(df, "difficulty").to_csv(RESULTS_DIR / "summary_difficulty.csv", index=False)
    n = df.groupby(["model", "variant"]).size().iloc[0]
    md = (f"# Benchmark results\n\nExecution accuracy on the {n}-question benchmark "
          f"({len(DATASETS)} datasets).\n\n" + to_markdown(summary)
          + "\n\n## Accuracy vs number of tables\n\n" + tables_markdown(summary))
    (RESULTS_DIR / "summary.md").write_text(md + "\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
