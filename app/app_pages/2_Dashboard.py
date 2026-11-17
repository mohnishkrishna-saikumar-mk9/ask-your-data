"""Dashboard page: 4 KPI tiles + 4 charts per dataset (FR-7).

Generic renderer - what each dataset shows is defined as data in app/dashboards.py.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboards import DASHBOARDS, Chart, Dashboard, Filter
from app.ui import cached_query, dataset_picker, db_ready, numeric_frame
from src.sql_library import get_query

st.title("Dashboard")
dataset = dataset_picker("dash_dataset")
if not db_ready():
    st.stop()
board: Dashboard | None = DASHBOARDS.get(dataset)
if board is None:
    st.info("No dashboard is defined for this dataset yet.", title="Not available")
    st.stop()


def filter_widget(flt: Filter) -> dict:
    """Draw the sidebar filter and return its values as SQL parameters."""
    options = cached_query(flt.options_sql)["v"].tolist()
    if flt.kind == "range":
        lo, hi = int(min(options)), int(max(options))
        if lo == hi:
            return {"lo": lo, "hi": hi}
        picked = st.sidebar.slider(flt.label, lo, hi, (lo, hi), key=f"flt_{dataset}")
        return {"lo": picked[0], "hi": picked[1]}
    picked = st.sidebar.multiselect(flt.label, options, default=options, key=f"flt_{dataset}")
    return {"values": picked or options}


def apply_filter(df: pd.DataFrame, flt: Filter | None, params: dict) -> pd.DataFrame:
    """Filter chart data in pandas when it contains the filter's column."""
    if flt is None or flt.column not in df.columns:
        return df
    col = df[flt.column]
    if flt.kind == "multi":
        return df[col.astype(str).isin(params["values"])]
    values = pd.to_datetime(col).dt.year if flt.as_year else pd.to_numeric(col)
    return df[values.between(params["lo"], params["hi"])]


def format_value(value: object) -> str:
    """1234 -> '1,234'; 12.345 -> '12.3'; NULL -> '-'."""
    if value is None or pd.isna(value):
        return "-"
    number = float(value)
    return f"{int(number):,}" if number.is_integer() else f"{number:,.1f}"


def chart_data(chart: Chart) -> pd.DataFrame:
    """Data for one chart: its library query or its own SQL, numbers as floats."""
    sql = chart.sql or get_query(dataset, chart.query).sql
    return numeric_frame(cached_query(sql, schema=dataset))


def draw_chart(chart: Chart, df: pd.DataFrame) -> None:
    """Plotly Express figure for one chart definition."""
    if df.empty:
        st.info("No data for this selection.")
        return
    if chart.kind == "barh":
        fig = px.bar(df.sort_values(chart.x), x=chart.x, y=chart.y, orientation="h")
    elif chart.kind == "bar":
        fig = px.bar(df, x=chart.x, y=chart.y, color=chart.color, barmode=chart.barmode,
                     text=chart.label)
        if chart.label:
            fig.update_traces(textposition="inside", textangle=-90, insidetextanchor="start")
    elif chart.kind == "line":
        fig = px.line(df, x=chart.x, y=chart.y, color=chart.color, markers=True)
    elif chart.kind == "pie":
        fig = px.pie(df, names=chart.x, values=chart.y, hole=0.4)
    else:
        fig = px.scatter(df, x=chart.x, y=chart.y, opacity=0.7)
    fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=340,
                      legend_title_text="", yaxis_title=None, xaxis_title=None)
    st.plotly_chart(fig, key=f"chart_{dataset}_{chart.title}")


try:
    params = filter_widget(board.filter) if board.filter else {}
    row = cached_query(board.kpi_sql, params or None).iloc[0]
    with st.grid(4, gap="medium"):
        for col, label in board.kpi_labels.items():
            st.metric(label, format_value(row[col]), border=True, height="stretch")
    for note in board.notes:
        st.caption(note)
    with st.grid(2, min_column_width=380, gap="medium"):
        for chart in board.charts:
            with st.container(border=True):
                st.markdown(f"**{chart.title}**")
                draw_chart(chart, apply_filter(chart_data(chart), board.filter, params))
except Exception as err:  # most likely: dataset not loaded yet
    st.warning(f"Could not build this dashboard: {str(err).splitlines()[0]}", title="Data missing")
    st.caption("Load the data with `python -m scripts.load_all`.")
