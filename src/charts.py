"""Pick a sensible chart for any result DataFrame (SPEC 9.5)."""
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

DATE_HINTS = ("date", "month", "season", "year", "week", "day")


@dataclass(frozen=True)
class ChartSpec:
    """What to draw: kind in {'kpi', 'line', 'bar', 'scatter', 'table'} plus column names."""

    kind: str
    x: str | None = None
    y: str | None = None


def _is_time_col(df: pd.DataFrame, col: str) -> bool:
    """Datetime dtype, or a name like 'month'/'season' (seasons are integer years)."""
    return pd.api.types.is_datetime64_any_dtype(df[col]) or any(
        h in col.lower() for h in DATE_HINTS)


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    """Columns that hold numbers (Decimal values from Postgres count too)."""
    cols = []
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if df[col].notna().any() and converted.notna().sum() == df[col].notna().sum() \
                and not pd.api.types.is_bool_dtype(df[col]):
            cols.append(col)
    return cols


def pick_chart(df: pd.DataFrame) -> ChartSpec:
    """Decide the chart type from the shape of the result."""
    if df.empty:
        return ChartSpec("table")
    numeric = _numeric_cols(df)
    time_cols = [c for c in df.columns if _is_time_col(df, c)]
    if len(df) == 1 and len(df.columns) == 1 and numeric:
        return ChartSpec("kpi", y=df.columns[0])
    if time_cols:
        values = [c for c in numeric if c not in time_cols]
        if values and len(df) > 1:
            return ChartSpec("line", x=time_cols[0], y=values[0])
    categorical = [c for c in df.columns if c not in numeric]
    if len(df.columns) == 2 and len(categorical) == 1 and len(numeric) == 1 and len(df) <= 25:
        return ChartSpec("bar", x=numeric[0], y=categorical[0])
    if len(df.columns) == 2 and len(numeric) == 2:
        return ChartSpec("scatter", x=df.columns[0], y=df.columns[1])
    return ChartSpec("table")


def make_figure(df: pd.DataFrame, spec: ChartSpec) -> Figure | None:
    """Build a Plotly figure for line / bar / scatter specs (None for kpi / table)."""
    if spec.kind == "line":
        data = df.assign(**{spec.y: pd.to_numeric(df[spec.y])}).sort_values(spec.x)
        return px.line(data, x=spec.x, y=spec.y, markers=True)
    if spec.kind == "bar":
        data = df.assign(**{spec.x: pd.to_numeric(df[spec.x])}).sort_values(spec.x)
        fig = px.bar(data, x=spec.x, y=spec.y, orientation="h")
        fig.update_layout(height=max(300, 28 * len(df)))
        return fig
    if spec.kind == "scatter":
        return px.scatter(df.apply(pd.to_numeric), x=spec.x, y=spec.y)
    return None
