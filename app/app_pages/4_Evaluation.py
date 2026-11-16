"""Evaluation page: latest benchmark results (accuracy and latency per model x prompt)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import DATASETS, ROOT

RESULTS = ROOT / "eval" / "results"

st.title("Evaluation")
st.markdown(
    f"Each model answers a benchmark of **20 questions per dataset across {len(DATASETS)} "
    "datasets** (1 to 11 tables), each with hand-written gold SQL. An answer counts as correct "
    "when its result rows match the gold result (**execution accuracy**), not when the SQL text "
    "matches. Numbers are compared at the precision the gold answer uses, and rows that tie on "
    "the sort order may appear in any order."
)

summary_csv = RESULTS / "summary.csv"
if not summary_csv.exists():
    st.info("No benchmark has been run yet. Run "
            "`python -m eval.run_eval --model <provider:model> --prompt full` "
            "and then `python -m eval.summarize`.", title="No results yet")
    st.stop()

summary = pd.read_csv(summary_csv)
overall = summary[summary["dataset"] == "all"].copy()
overall["run"] = overall["model"] + " · " + overall["variant"]

best = overall.sort_values("accuracy", ascending=False).iloc[0]
with st.grid(4, gap="medium"):
    st.metric("Best accuracy", f"{best['accuracy']:.0%}", border=True, height="stretch")
    st.metric("Best run", best["run"], border=True, height="stretch")
    st.metric("Median latency (best run)", f"{best['p50_ms'] / 1000:.2f} s", border=True,
              height="stretch")
    st.metric("Runs compared", len(overall), border=True, height="stretch")

fig = px.bar(overall.sort_values("accuracy"), x="accuracy", y="model", color="variant",
             barmode="group", orientation="h", range_x=[0, 1],
             labels={"accuracy": "Execution accuracy", "model": "", "variant": "Prompt"})
fig.update_layout(title="Accuracy by model and prompt variant", xaxis_tickformat=".0%",
                  margin={"l": 10, "r": 10, "t": 40, "b": 10})
st.plotly_chart(fig)

per_dataset = summary[summary["dataset"] != "all"].copy()
if "n_tables" in per_dataset.columns:
    per_dataset["run"] = per_dataset["model"] + " · " + per_dataset["variant"]
    trend = px.line(per_dataset.sort_values("n_tables"), x="n_tables", y="accuracy", color="run",
                    markers=True, hover_name="dataset", range_y=[0, 1.05],
                    labels={"n_tables": "Tables in the dataset", "accuracy": "Execution accuracy",
                            "run": "Model · prompt"})
    trend.update_layout(title="Does accuracy drop as schemas get bigger?", yaxis_tickformat=".0%",
                        margin={"l": 10, "r": 10, "t": 40, "b": 10})
    st.plotly_chart(trend)

st.subheader("By dataset")
pivot = summary.pivot_table(index=["model", "variant"], columns="dataset", values="accuracy")
pivot = pivot[[c for c in [*DATASETS, "all"] if c in pivot.columns]]
st.dataframe(pivot.style.format("{:.0%}"))

if (RESULTS / "summary_difficulty.csv").exists():
    diff = pd.read_csv(RESULTS / "summary_difficulty.csv")
    st.subheader("By difficulty")
    table = diff.pivot_table(index=["model", "variant"], columns="difficulty", values="accuracy")
    st.dataframe(table[[c for c in ["easy", "medium", "hard", "all"] if c in table.columns]]
                 .style.format("{:.0%}"))

summary_md = RESULTS / "summary.md"
if summary_md.exists():
    with st.expander("Raw summary.md"):
        st.markdown(summary_md.read_text(encoding="utf-8"))
