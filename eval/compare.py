"""Execution-accuracy comparison (SPEC 11).

Two results are "the same answer" when they contain the same rows:
- values are normalised (floats/decimals rounded to 2 dp, strings stripped, NULL-safe, dates as text)
- rows are compared as a multiset (order ignored) and column order is ignored
- if the gold SQL has a top-level ORDER BY, the row order must match too
- extra predicted columns are allowed if a subset of them matches the gold columns exactly
"""
import datetime as dt
import math
from collections import Counter
from decimal import Decimal

import pandas as pd
import sqlglot
from sqlglot import exp

Row = tuple


def normalise_value(v: object) -> object:
    """Make equal answers compare equal: 5 == 5.0 == Decimal('5.00'); ' x ' == 'x'."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int | float | Decimal):
        return round(float(v), 2) + 0.0  # + 0.0 turns -0.0 into 0.0
    if isinstance(v, dt.datetime | dt.date | pd.Timestamp):
        return v.isoformat()[:10] if isinstance(v, dt.date) and not isinstance(
            v, dt.datetime) else pd.Timestamp(v).isoformat()
    if hasattr(v, "item"):  # numpy scalar
        return normalise_value(v.item())
    return str(v).strip()


def _sort_key(v: object) -> tuple[int, str]:
    """Sort mixed types deterministically (None first)."""
    return (0, "") if v is None else (1, repr(v))


def normalise_rows(df: pd.DataFrame) -> list[Row]:
    """Each row becomes a column-order-independent tuple of normalised values."""
    rows = []
    for raw in df.itertuples(index=False, name=None):
        values = [normalise_value(v) for v in raw]
        rows.append(tuple(sorted(values, key=_sort_key)))
    return rows


def has_order_by(sql: str) -> bool:
    """True if the outermost query has an ORDER BY clause."""
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return False
    return isinstance(tree, exp.Query) and tree.args.get("order") is not None


def _same_rows(gold: pd.DataFrame, pred: pd.DataFrame, ordered: bool) -> bool:
    g, p = normalise_rows(gold), normalise_rows(pred)
    return g == p if ordered else Counter(g) == Counter(p)


def _project_matching_columns(gold: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame | None:
    """Pick, for each gold column, a predicted column holding the same values (as a multiset)."""
    chosen: list[str] = []
    for gcol in gold.columns:
        target = Counter(normalise_value(v) for v in gold[gcol])
        match = next((pcol for pcol in pred.columns if pcol not in chosen and
                      Counter(normalise_value(v) for v in pred[pcol]) == target), None)
        if match is None:
            return None
        chosen.append(match)
    return pred[chosen]


def results_match(gold: pd.DataFrame, pred: pd.DataFrame, ordered: bool = False) -> bool:
    """Execution accuracy for one question."""
    if len(gold) != len(pred) or pred.shape[1] < gold.shape[1]:
        return False
    if gold.shape[1] == pred.shape[1] and _same_rows(gold, pred, ordered):
        return True
    projected = _project_matching_columns(gold, pred)
    return projected is not None and _same_rows(gold, projected, ordered)
