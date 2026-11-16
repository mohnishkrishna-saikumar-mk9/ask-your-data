"""Shared helpers for the Streamlit pages: cached queries, dataset picker, result display."""
import pandas as pd
import streamlit as st

from src.charts import make_figure, pick_chart
from src.config import DATASETS
from src.db import run_query

DATASET_LABELS = {"ipl": "IPL cricket", "ecommerce": "E-commerce (Amazon India)",
                  "placements": "Campus placements"}


@st.cache_data(ttl=3600, show_spinner=False)
def cached_query(sql: str, params: dict | None = None, schema: str | None = None) -> pd.DataFrame:
    """Run a read-only query once per hour per (sql, params, schema) - dashboards stay fast."""
    return run_query(sql, params=params, schema=schema)


def dataset_picker(key: str, sidebar: bool = True) -> str:
    """Dataset selector that remembers the choice across pages."""
    target = st.sidebar if sidebar else st
    return target.selectbox("Dataset", list(DATASETS), key=key,
                            format_func=lambda d: DATASET_LABELS.get(d, d),
                            index=list(DATASETS).index(st.session_state.get("dataset", "ipl")),
                            on_change=lambda: st.session_state.update(dataset=st.session_state[key]))


def show_result(df: pd.DataFrame, title: str | None = None) -> None:
    """Auto-chart (KPI / line / bar / scatter) followed by the data table."""
    spec = pick_chart(df)
    if spec.kind == "kpi":
        value = df.iloc[0, 0]
        st.metric(spec.y or "value", f"{value:,}" if isinstance(value, int | float) else str(value))
        return
    fig = make_figure(df, spec)
    if fig is not None:
        if title:
            fig.update_layout(title=title)
        fig.update_layout(margin={"l": 10, "r": 10, "t": 40 if title else 10, "b": 10})
        st.plotly_chart(fig)
    st.dataframe(df, hide_index=True)


def db_ready() -> bool:
    """Show a friendly message instead of a stack trace when the DB is not set up."""
    try:
        cached_query("SELECT 1 AS ok")
        return True
    except Exception as err:
        st.error(f"Could not connect to the database: {str(err).splitlines()[0]}",
                 title="Database not available")
        st.caption("Set DATABASE_URL in .env (or Streamlit secrets) and run the loaders.")
        return False
