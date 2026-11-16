"""Evaluation page: latest benchmark results (accuracy and latency per model x prompt)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import ROOT

RESULTS = ROOT / "eval" / "results"

st.title("Evaluation")
st.markdown(
    "Each model answers a **100-question benchmark** (50 IPL, 25 e-commerce, 25 placements) "
    "with gold SQL. A prediction counts as correct when its result rows match the gold "
    "result (**execution accuracy**), not when the SQL text matches."
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
with st.container(horizontal=True):
    st.metric("Best accuracy", f"{best['accuracy']:.0%}", border=True)
    st.metric("Best run", best["run"], border=True)
    st.metric("Median latency (best run)", f"{best['p50_ms'] / 1000:.2f} s", border=True)
    st.metric("Runs compared", len(overall), border=True)

fig = px.bar(overall.sort_values("accuracy"), x="accuracy", y="model", color="variant",
             barmode="group", orientation="h", range_x=[0, 1],
             labels={"accuracy": "Execution accuracy"})
fig.update_layout(title="Accuracy by model and prompt variant", xaxis_tickformat=".0%",
                  margin={"l": 10, "r": 10, "t": 40, "b": 10})
st.plotly_chart(fig)

st.subheader("By dataset")
pivot = summary.pivot_table(index=["model", "variant"], columns="dataset", values="accuracy")
st.dataframe(pivot.style.format("{:.0%}"))

if (RESULTS / "summary_difficulty.csv").exists():
    diff = pd.read_csv(RESULTS / "summary_difficulty.csv")
    st.subheader("By difficulty")
    st.dataframe(diff.pivot_table(index=["model", "variant"], columns="difficulty",
                                  values="accuracy").style.format("{:.0%}"))

summary_md = RESULTS / "summary.md"
if summary_md.exists():
    with st.expander("Raw summary.md"):
        st.markdown(summary_md.read_text(encoding="utf-8"))
