"""Overview page: what the project is, the 8 datasets, and how the engine works."""
import os

import streamlit as st

from app.ui import DATASET_LABELS, cached_query, db_ready
from src.config import DATASETS

st.title("Ask Your Data")
st.markdown(
    "Ask questions in plain English and get back the SQL, a table and a chart. An LLM writes "
    "the SQL from the database's own schema and data dictionary, guardrails check it, and a "
    "read-only PostgreSQL database answers. It is tested on **8 real datasets**, from a single "
    "table to an 11-table music store."
)
if os.getenv("GITHUB_URL"):
    st.link_button("Source code on GitHub", os.environ["GITHUB_URL"], icon=":material/code:")

# Table and row counts come from the catalogue (pg_class.reltuples is refreshed by ANALYZE in the
# loaders), so this page needs no dataset-specific SQL.
SIZE_SQL = """
SELECT n.nspname AS dataset, COUNT(*) AS tables, SUM(GREATEST(c.reltuples, 0))::bigint AS rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = ANY(:schemas)
GROUP BY n.nspname
"""

if db_ready():
    sizes = cached_query(SIZE_SQL, {"schemas": list(DATASETS)}).set_index("dataset")
    with st.grid(4, gap="medium"):
        for dataset, description in DATASETS.items():
            with st.container(border=True, height="stretch"):
                st.markdown(f"**{DATASET_LABELS.get(dataset, dataset)}**")
                st.caption(description)
                if dataset in sizes.index:
                    size = sizes.loc[dataset]
                    st.markdown(f"{int(size['tables'])} tables · ~{int(size['rows']):,} rows")
                else:
                    st.markdown(":orange[Not loaded yet]")

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
    "- **Dashboard** - KPIs and charts for each dataset, built from hand-written SQL\n"
    "- **Query library** - 72 commented queries (CTEs, window functions, recursive CTEs, cohorts)\n"
    "- **Evaluation** - accuracy of different LLMs and prompts on the benchmark"
)
