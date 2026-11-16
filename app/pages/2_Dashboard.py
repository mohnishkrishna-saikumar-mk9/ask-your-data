"""Dashboard page: 4 KPI tiles + 4 charts per dataset, built from hand-written SQL."""
import pandas as pd
import plotly.express as px
import streamlit as st

from app.ui import cached_query, dataset_picker, db_ready
from src.sql_library import get_query

st.title("Dashboard")
dataset = dataset_picker("dash_dataset")
if not db_ready():
    st.stop()


def kpi_row(sql: str, labels: dict[str, str], params: dict | None = None) -> None:
    """Render one row of metric tiles from a single-row query."""
    row = cached_query(sql, params).iloc[0]
    with st.container(horizontal=True):
        for col, label in labels.items():
            value = row[col]
            if pd.isna(value):
                text = "-"
            elif float(value).is_integer():  # pandas upcasts mixed rows to float
                text = f"{int(value):,}"
            else:
                text = f"{float(value):,.1f}"
            st.metric(label, text, border=True)


def analysis(prefix: str) -> pd.DataFrame:
    """Result of a library query, e.g. analysis('05') for the current dataset."""
    df = cached_query(get_query(dataset, prefix).sql)
    for col in df.columns:  # Postgres NUMERIC arrives as Decimal objects; Plotly wants floats
        converted = pd.to_numeric(df[col], errors="coerce")
        if df[col].dtype == object and converted.notna().sum() == df[col].notna().sum():
            df[col] = converted
    return df


def chart(fig, title: str) -> None:
    fig.update_layout(title=title, margin={"l": 10, "r": 10, "t": 40, "b": 10}, height=360)
    st.plotly_chart(fig)


try:
    if dataset == "ipl":
        seasons = cached_query("SELECT DISTINCT season FROM ipl.matches ORDER BY 1")["season"]
        lo, hi = int(seasons.min()), int(seasons.max())
        picked = st.sidebar.slider("Seasons", lo, hi, (lo, hi)) if lo < hi else (lo, hi)
        kpi_row("""WITH m AS (SELECT * FROM ipl.matches WHERE season BETWEEN :lo AND :hi)
                   SELECT (SELECT COUNT(*) FROM m) AS matches,
                          (SELECT SUM(total_runs) FROM ipl.deliveries d JOIN m USING (match_id)) AS runs,
                          (SELECT COUNT(*) FROM ipl.deliveries d JOIN m USING (match_id)
                           WHERE d.batter_runs = 6) AS sixes,
                          (SELECT ROUND(AVG(target_runs - 1), 1)::float FROM m) AS avg_first_innings""",
                {"matches": "Matches", "runs": "Runs", "sixes": "Sixes",
                 "avg_first_innings": "Avg 1st-innings score"},
                {"lo": picked[0], "hi": picked[1]})
        left, right = st.columns(2)
        with left:
            df = analysis("15").query("@picked[0] <= season <= @picked[1]")
            chart(px.line(df, x="season", y="boundary_pct", markers=True),
                  "Share of runs from boundaries (%)")
            titles = analysis("01")
            chart(px.bar(titles, x="titles", y="team", orientation="h"), "IPL titles by team")
        with right:
            df = analysis("05").query("@picked[0] <= season <= @picked[1]")
            chart(px.bar(df, x="season", y="runs", hover_name="batter", text="batter"),
                  "Top run scorer each season")
            df = analysis("03").query("@picked[0] <= season <= @picked[1]")
            chart(px.line(df, x="season", y="toss_winner_win_pct", color="toss_decision",
                          markers=True), "Win % for the toss winner, by decision")

    elif dataset == "ecommerce":
        months = cached_query("SELECT DISTINCT date_trunc('month', order_date)::date AS m "
                              "FROM ecommerce.orders ORDER BY 1")["m"].astype(str).tolist()
        picked = st.sidebar.multiselect("Months", months, default=months)
        kpi_row("""SELECT SUM(i.amount) FILTER (WHERE o.status NOT LIKE 'Cancelled%')::float AS revenue,
                           COUNT(DISTINCT o.order_id) AS orders,
                           ROUND(SUM(i.amount) FILTER (WHERE o.status NOT LIKE 'Cancelled%')
                                 / NULLIF(COUNT(DISTINCT o.order_id) FILTER
                                          (WHERE o.status NOT LIKE 'Cancelled%'), 0), 2)::float AS aov,
                           ROUND(100.0 * COUNT(DISTINCT o.order_id) FILTER (WHERE o.status LIKE 'Cancelled%')
                                 / NULLIF(COUNT(DISTINCT o.order_id), 0), 1)::float AS cancel_pct
                    FROM ecommerce.orders o JOIN ecommerce.order_items i USING (order_id)
                    WHERE date_trunc('month', o.order_date)::date::text = ANY(:months)""",
                {"revenue": "Revenue (INR)", "orders": "Orders", "aov": "Avg order value",
                 "cancel_pct": "Cancellation %"},
                {"months": picked})
        left, right = st.columns(2)
        with left:
            df = analysis("01")
            df = df[df["month"].astype(str).isin(picked)]
            chart(px.bar(df, x="month", y="revenue"), "Monthly revenue")
            chart(px.bar(analysis("02"), x="revenue", y="ship_state", orientation="h"),
                  "Top 10 states by revenue")
        with right:
            chart(px.bar(analysis("05"), x="cancellation_rate_pct", y="category",
                         orientation="h"), "Cancellation rate by category (%)")
            chart(px.pie(analysis("10"), names="stage", values="orders", hole=0.4),
                  "Order status funnel")

    else:
        kpi_row("""SELECT COUNT(*) AS students,
                          ROUND(100.0 * AVG(is_placed::int), 1)::float AS rate,
                          ROUND(AVG(salary), 0)::float AS avg_salary,
                          MAX(salary)::float AS max_salary
                   FROM placements.students""",
                {"students": "Students", "rate": "Placement rate %",
                 "avg_salary": "Avg salary (INR)", "max_salary": "Highest salary (INR)"})
        left, right = st.columns(2)
        with left:
            chart(px.bar(analysis("01"), x="mba_specialisation", y="placement_rate_pct"),
                  "Placement rate by specialisation (%)")
            chart(px.bar(analysis("06"), x="band", y="placement_rate_pct"),
                  "Placement rate by MBA score band (%)")
        with right:
            chart(px.bar(analysis("03"), x="work_experience", y="placement_rate_pct"),
                  "Work experience and placement rate (%)")
            placed = cached_query("SELECT employability_test_percent::float AS test, "
                                  "salary::float AS salary FROM placements.students WHERE is_placed")
            chart(px.scatter(placed, x="test", y="salary", opacity=0.7),
                  "Employability test score vs salary")
except Exception as err:  # most likely: dataset not loaded yet
    st.warning(f"Could not build this dashboard: {str(err).splitlines()[0]}",
               title="Data missing")
    st.caption("Load the data with `python -m scripts.load_all`.")
