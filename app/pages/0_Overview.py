"""Overview page: what the project is, the datasets, and how it works."""
import streamlit as st

from app.ui import DATASET_LABELS, cached_query, db_ready
from src.config import DATASETS

st.title("Ask Your Data")
st.markdown(
    "Ask questions in plain English about **IPL cricket**, **Indian e-commerce sales** or "
    "**campus placements**. An LLM writes the SQL, guardrails check it, and a read-only "
    "PostgreSQL database answers - with the SQL, a table and a chart."
)

COUNT_SQL = {
    "ipl": "SELECT (SELECT COUNT(*) FROM ipl.matches) AS a, (SELECT COUNT(*) FROM ipl.deliveries) AS b",
    "ecommerce": "SELECT (SELECT COUNT(*) FROM ecommerce.orders) AS a, "
                 "(SELECT COUNT(*) FROM ecommerce.order_items) AS b",
    "placements": "SELECT (SELECT COUNT(*) FROM placements.students) AS a, "
                  "(SELECT COUNT(*) FILTER (WHERE is_placed) FROM placements.students) AS b",
}
COUNT_LABELS = {"ipl": ("Matches", "Deliveries"), "ecommerce": ("Orders", "Order lines"),
                "placements": ("Students", "Placed")}

if db_ready():
    cols = st.columns(len(DATASETS))
    for col, (dataset, description) in zip(cols, DATASETS.items(), strict=True):
        with col, st.container(border=True, height="stretch"):
            st.subheader(DATASET_LABELS[dataset])
            st.caption(description)
            try:
                row = cached_query(COUNT_SQL[dataset]).iloc[0]
                a, b = COUNT_LABELS[dataset]
                st.metric(a, f"{int(row['a']):,}")
                st.metric(b, f"{int(row['b']):,}")
            except Exception:
                st.warning("Not loaded yet - run `python -m scripts.load_all`.")

st.subheader("How it works")
st.graphviz_chart("""
digraph {
  rankdir=LR; node [shape=box, style=rounded, fontname="sans-serif"];
  Q [label="Question"]; P [label="Prompt builder\\nschema + comments\\n+ glossary + examples"];
  L [label="LLM\\nGroq / Gemini /\\nOpenRouter / Ollama"]; X [label="Extract SQL"];
  G [label="Guardrails\\n(sqlglot AST)"]; D [label="PostgreSQL\\nread-only role"];
  R [label="Table + auto chart"];
  Q -> P -> L -> X -> G -> D -> R;
  G -> Q [label="rejected", style=dashed];
  D -> L [label="error: retry once", style=dashed];
}
""")

st.markdown(
    "- **Ask** - type a question and get SQL + results\n"
    "- **Dashboard** - KPIs and charts built from hand-written SQL\n"
    "- **Query library** - 40 commented queries (CTEs, window functions, percentiles)\n"
    "- **Evaluation** - accuracy of different LLMs and prompts on a 100-question benchmark"
)
