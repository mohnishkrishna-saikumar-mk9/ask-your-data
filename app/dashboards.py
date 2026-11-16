"""Dashboard definitions: what each dataset's dashboard shows (FR-7).

The Dashboard page is one generic renderer; everything dataset-specific lives here as data.
Adding a dataset's dashboard = adding one entry to DASHBOARDS.

- kpis:   one single-row SQL query + {column: label} for 4 metric tiles. When the dashboard
          has a filter, the SQL receives its values as bound parameters (:lo/:hi or :values).
- charts: each chart reads either a library query (`query="05"` -> sql/analysis/<ds>/05_*.sql)
          or its own `sql`, and is drawn with Plotly Express.
- filter: optional. "range" = slider over integers (e.g. seasons, years);
          "multi" = multiselect of text values (e.g. months). Charts whose data contains
          `column` are filtered in pandas; KPI SQL is filtered in the database.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Filter:
    label: str
    kind: str                # "range" or "multi"
    options_sql: str         # returns one column of allowed values, sorted
    column: str              # column to filter in chart data
    as_year: bool = False    # chart column is a date; compare its year with the range


@dataclass(frozen=True)
class Chart:
    title: str
    kind: str                # "bar", "barh", "line", "pie", "scatter"
    x: str
    y: str | list[str]
    query: str | None = None  # number prefix of a library query
    sql: str | None = None
    color: str | None = None
    barmode: str = "relative"
    label: str | None = None  # column printed on each bar, e.g. the player's name


@dataclass(frozen=True)
class Dashboard:
    kpi_sql: str
    kpi_labels: dict[str, str]
    charts: list[Chart]
    filter: Filter | None = None
    notes: list[str] = field(default_factory=list)


YEARS = "SELECT DISTINCT EXTRACT(YEAR FROM {col})::int AS v FROM {table} WHERE {col} IS NOT NULL ORDER BY 1"

DASHBOARDS: dict[str, Dashboard] = {
    "placements": Dashboard(
        kpi_sql="""SELECT COUNT(*) AS students,
                          ROUND(100.0 * AVG(is_placed::int), 1) AS rate,
                          ROUND(AVG(salary), 0) AS avg_salary,
                          MAX(salary) AS max_salary
                   FROM placements.students""",
        kpi_labels={"students": "Students", "rate": "Placement rate %",
                    "avg_salary": "Avg salary (INR)", "max_salary": "Highest salary (INR)"},
        charts=[
            Chart("Placement rate by specialisation (%)", "bar", "mba_specialisation",
                  "placement_rate_pct", query="01"),
            Chart("Placement rate by MBA score band (%)", "bar", "band", "placement_rate_pct",
                  query="06"),
            Chart("Work experience and placement rate (%)", "bar", "work_experience",
                  "placement_rate_pct", query="03"),
            Chart("Employability test score vs salary (placed students)", "scatter", "test", "salary",
                  sql="SELECT employability_test_percent AS test, salary "
                      "FROM placements.students WHERE is_placed"),
        ],
    ),
    "netflix": Dashboard(
        filter=Filter("Year added", "range",
                      YEARS.format(col="date_added", table="netflix.titles"), "year_added"),
        kpi_sql="""SELECT COUNT(*) AS titles,
                          COUNT(*) FILTER (WHERE type = 'Movie') AS movies,
                          COUNT(*) FILTER (WHERE type = 'TV Show') AS shows,
                          ROUND(AVG(duration_minutes), 0) AS avg_minutes
                   FROM netflix.titles
                   WHERE EXTRACT(YEAR FROM date_added) BETWEEN :lo AND :hi""",
        kpi_labels={"titles": "Titles added", "movies": "Movies", "shows": "TV shows",
                    "avg_minutes": "Avg movie length (min)"},
        charts=[
            Chart("Titles added per year", "bar", "year_added", ["movies", "tv_shows"], query="01"),
            Chart("Top genres", "barh", "titles", "genre", query="02"),
            Chart("Top producing countries", "barh", "titles", "country", query="03"),
            Chart("Average movie length by release decade (min)", "line", "decade", "avg_minutes",
                  query="05"),
        ],
    ),
    "startups": Dashboard(
        filter=Filter("Funding year", "range",
                      YEARS.format(col="funding_date", table="startups.funding_rounds"), "year"),
        kpi_sql="""SELECT COUNT(*) AS rounds,
                          ROUND(SUM(amount_usd) / 1e9, 2) AS total_bn,
                          ROUND(100.0 * COUNT(amount_usd) / COUNT(*), 1) AS disclosed_pct,
                          (SELECT COUNT(DISTINCT ri.investor_name)
                             FROM startups.round_investors ri
                             JOIN startups.funding_rounds r2 ON r2.round_id = ri.round_id
                            WHERE EXTRACT(YEAR FROM r2.funding_date) BETWEEN :lo AND :hi) AS investors
                   FROM startups.funding_rounds
                   WHERE EXTRACT(YEAR FROM funding_date) BETWEEN :lo AND :hi""",
        kpi_labels={"rounds": "Funding rounds", "total_bn": "Disclosed funding ($ bn)",
                    "disclosed_pct": "Rounds with amount %", "investors": "Investors"},
        charts=[
            Chart("Disclosed funding per year ($ mn)", "bar", "year", "total_usd_mn", query="01"),
            Chart("Round types by year", "bar", "year", "rounds", color="round_type", query="05"),
            Chart("Most funded startups ($ mn)", "barh", "total_usd_mn", "startup_name", query="02"),
            Chart("Most active investors (rounds)", "barh", "rounds", "investor_name", query="03"),
        ],
        notes=["Round 61 (Rapido, 2019) is excluded from totals: the source entered rupees as dollars."],
    ),
    "air_quality": Dashboard(
        filter=Filter("Year", "range",
                      YEARS.format(col="obs_date", table="air_quality.city_daily"), "month",
                      as_year=True),
        kpi_sql="""SELECT COUNT(DISTINCT city) AS cities,
                          COUNT(aqi) AS readings,
                          ROUND(AVG(aqi), 0) AS avg_aqi,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE aqi > 200) / NULLIF(COUNT(aqi), 0), 1)
                              AS poor_pct
                   FROM air_quality.city_daily
                   WHERE EXTRACT(YEAR FROM obs_date) BETWEEN :lo AND :hi""",
        kpi_labels={"cities": "Cities", "readings": "City-days with AQI", "avg_aqi": "Average AQI",
                    "poor_pct": "Days Poor or worse %"},
        charts=[
            Chart("Monthly average AQI - 4 metros", "line", "month", "avg_aqi", color="city",
                  query="02"),
            Chart("Most polluted cities (average AQI, whole period)", "barh", "avg_aqi", "city",
                  query="01"),
            Chart("PM2.5 change: 2020 lockdown vs same dates 2019 (%)", "barh", "change_pct", "city",
                  query="04"),
            Chart("Winter vs summer average AQI", "bar", "city",
                  ["winter_avg_aqi", "summer_avg_aqi"], query="03", barmode="group"),
        ],
        notes=["Ahmedabad's very high AQI comes from unusually high CO readings in the source data."],
    ),
    "ecommerce": Dashboard(
        filter=Filter("Months", "multi",
                      "SELECT DISTINCT date_trunc('month', order_date)::date::text AS v "
                      "FROM ecommerce.orders ORDER BY 1", "month"),
        kpi_sql="""WITH o AS (
                       SELECT o.order_id, o.status, SUM(i.amount) AS value
                       FROM ecommerce.orders o JOIN ecommerce.order_items i USING (order_id)
                       WHERE date_trunc('month', o.order_date)::date::text = ANY(:values)
                       GROUP BY o.order_id, o.status)
                   SELECT SUM(value) FILTER (WHERE status NOT LIKE 'Cancelled%') AS revenue,
                          COUNT(*) AS orders,
                          ROUND(SUM(value) FILTER (WHERE status NOT LIKE 'Cancelled%')
                                / NULLIF(COUNT(*) FILTER (WHERE status NOT LIKE 'Cancelled%'), 0), 2)
                              AS aov,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE status LIKE 'Cancelled%')
                                / NULLIF(COUNT(*), 0), 1) AS cancel_pct
                   FROM o""",
        kpi_labels={"revenue": "Revenue (INR)", "orders": "Orders", "aov": "Avg order value",
                    "cancel_pct": "Cancellation %"},
        charts=[
            Chart("Monthly revenue (INR)", "bar", "month", "revenue", query="01"),
            Chart("Top 10 states by revenue", "barh", "revenue", "ship_state", query="02"),
            Chart("Cancellation rate by category (%)", "barh", "cancellation_rate_pct", "category",
                  query="05"),
            Chart("Order status funnel", "pie", "stage", "orders", query="10"),
        ],
    ),
    "ipl": Dashboard(
        filter=Filter("Seasons", "range", "SELECT DISTINCT season AS v FROM ipl.matches ORDER BY 1",
                      "season"),
        kpi_sql="""WITH m AS (SELECT * FROM ipl.matches WHERE season BETWEEN :lo AND :hi)
                   SELECT (SELECT COUNT(*) FROM m) AS matches,
                          (SELECT SUM(total_runs) FROM ipl.deliveries d JOIN m USING (match_id)) AS runs,
                          (SELECT COUNT(*) FROM ipl.deliveries d JOIN m USING (match_id)
                           WHERE d.batter_runs = 6) AS sixes,
                          (SELECT ROUND(AVG(target_runs - 1), 1) FROM m) AS avg_first_innings""",
        kpi_labels={"matches": "Matches", "runs": "Runs", "sixes": "Sixes",
                    "avg_first_innings": "Avg 1st-innings score"},
        charts=[
            Chart("Share of runs from boundaries (%)", "line", "season", "boundary_pct", query="15"),
            Chart("Top run scorer each season", "bar", "season", "runs", query="05", label="batter"),
            Chart("IPL titles by team", "barh", "titles", "team", query="01"),
            Chart("Win % for the toss winner, by decision", "line", "season", "toss_winner_win_pct",
                  color="toss_decision", query="03"),
        ],
    ),
    "olist": Dashboard(
        kpi_sql="""SELECT (SELECT COUNT(*) FROM olist.orders) AS orders,
                          (SELECT ROUND(SUM(price) / 1e6, 2) FROM olist.order_items) AS gmv_mn,
                          (SELECT ROUND(AVG(review_score), 2) FROM olist.reviews) AS avg_review,
                          (SELECT ROUND(100.0 * AVG((order_delivered_customer_date
                                                     > order_estimated_delivery_date)::int), 1)
                             FROM olist.orders
                            WHERE order_status = 'delivered'
                              AND order_delivered_customer_date IS NOT NULL) AS late_pct""",
        kpi_labels={"orders": "Orders", "gmv_mn": "GMV (R$ mn)", "avg_review": "Avg review score",
                    "late_pct": "Late deliveries %"},
        charts=[
            Chart("Monthly GMV (R$)", "line", "month", "gmv", query="01"),
            Chart("Top categories by GMV (R$)", "barh", "gmv", "category", query="05"),
            Chart("Average delivery days by customer state", "barh", "avg_delivery_days", "state",
                  query="03"),
            Chart("Payment mix by value", "pie", "payment_type", "value", query="07"),
        ],
    ),
    "chinook": Dashboard(
        filter=Filter("Invoice year", "range",
                      YEARS.format(col="invoice_date", table="chinook.invoice"), "month",
                      as_year=True),
        kpi_sql="""SELECT COUNT(DISTINCT customer_id) AS customers,
                          COUNT(*) AS invoices,
                          SUM(total) AS revenue,
                          ROUND(AVG(total), 2) AS avg_invoice
                   FROM chinook.invoice
                   WHERE EXTRACT(YEAR FROM invoice_date) BETWEEN :lo AND :hi""",
        kpi_labels={"customers": "Customers", "invoices": "Invoices", "revenue": "Revenue ($)",
                    "avg_invoice": "Avg invoice ($)"},
        charts=[
            Chart("Running revenue ($)", "line", "month", "running_revenue", query="06"),
            Chart("Revenue by country ($)", "barh", "revenue", "country", query="01"),
            Chart("Revenue by genre ($)", "barh", "revenue", "genre",
                  sql="SELECT g.name AS genre, SUM(il.unit_price * il.quantity) AS revenue "
                      "FROM chinook.invoice_line il "
                      "JOIN chinook.track t ON t.track_id = il.track_id "
                      "JOIN chinook.genre g ON g.genre_id = t.genre_id "
                      "GROUP BY g.name ORDER BY revenue DESC LIMIT 12"),
            Chart("Tracks never sold, by genre", "barh", "never_sold", "genre", query="05"),
        ],
    ),
}
