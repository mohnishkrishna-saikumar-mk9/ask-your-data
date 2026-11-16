"""Query library: browse the 40 hand-written analysis queries with SQL, result and chart."""
import streamlit as st

from app.ui import cached_query, dataset_picker, db_ready, show_result
from src.sql_library import list_queries

st.title("Query library")
st.caption("Hand-written PostgreSQL showing joins, CTEs, window functions and statistics. "
           "Each file lives in `sql/analysis/`.")

dataset = dataset_picker("lib_dataset")
queries = list_queries(dataset)
concept_filter = st.sidebar.text_input("Filter by concept", placeholder="e.g. LAG, CTE, NTILE")
if concept_filter:
    queries = [q for q in queries if concept_filter.lower() in q.concepts.lower()]
if not queries:
    st.info("No queries match that concept.")
    st.stop()

choice = st.selectbox("Query", queries, format_func=lambda q: f"{q.title} - {q.question}",
                      key=f"lib_query_{dataset}")

with st.container(border=True):
    st.markdown(f"**Question:** {choice.question}")
    st.markdown(f"**SQL concepts:** {choice.concepts}")
    st.markdown(f"**Result shape:** `{choice.result_shape}`")

st.code(choice.sql, language="sql")

if db_ready():
    try:
        df = cached_query(choice.sql, schema=dataset)
        if df.empty:
            st.info("The query returned no rows (the loaded data may be a small sample).")
        else:
            show_result(df)
    except Exception as err:
        st.error(str(err).splitlines()[0], title="Query failed")
