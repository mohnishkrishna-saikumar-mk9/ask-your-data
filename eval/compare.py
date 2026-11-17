"""Execution-accuracy comparison (SPEC 11).

Two results are "the same answer" when they hold the same rows:
- values are normalised: strings stripped, dates as ISO text, NULL-safe, numbers as Decimal;
- numbers are compared **precision-aware**: the more precise value is rounded to the other's
  number of decimals (gold 12.5 vs predicted 12.4637 -> equal; 12.5 vs 12.4 -> not equal;
  whole numbers such as counts must match exactly);
- column order and column names are ignored (columns are matched by their values);
- extra predicted columns are allowed if a subset of them matches the gold columns;
- rows are compared as a multiset (order ignored), unless the gold SQL has a top-level
  ORDER BY - then the row order must match too.
"""
import datetime as dt
import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pandas as pd
import sqlglot
from sqlglot import exp

MAX_DECIMALS = 6  # floats like 12.041643518518 are compared at most to 6 decimals


def normalise_value(v: object) -> object:
    """Make equal answers comparable: numbers -> Decimal, dates -> 'YYYY-MM-DD', strings stripped."""
    if v is None or v is pd.NaT or (isinstance(v, float) and math.isnan(v)):
        return None
    if hasattr(v, "item") and not isinstance(v, str | bytes):  # numpy scalar
        v = v.item()
    if isinstance(v, bool):
        return v
    if isinstance(v, int | float | Decimal):
        return _to_decimal(v)
    if isinstance(v, dt.datetime | pd.Timestamp):
        ts = pd.Timestamp(v)
        return ts.date().isoformat() if ts == ts.normalize() else ts.isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v).strip()


def _to_decimal(x: int | float | Decimal) -> Decimal:
    """Exact Decimal for ints/Decimals; floats are rounded to MAX_DECIMALS to drop binary noise."""
    try:
        d = Decimal(x) if not isinstance(x, float) else Decimal(repr(x))
    except InvalidOperation:
        return Decimal(0)
    if _decimals(d) > MAX_DECIMALS:
        d = d.quantize(Decimal(1).scaleb(-MAX_DECIMALS), rounding=ROUND_HALF_UP)
    return d.normalize() if d != 0 else Decimal(0)


def _decimals(d: Decimal) -> int:
    """Number of digits after the decimal point (12.50 -> 1 after normalising, 300 -> 0)."""
    exponent = d.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def values_equal(a: object, b: object) -> bool:
    """Equality with precision-aware numbers (see module docstring)."""
    if isinstance(a, Decimal) and isinstance(b, Decimal):
        places = Decimal(1).scaleb(-min(_decimals(a), _decimals(b)))
        return a.quantize(places, ROUND_HALF_UP) == b.quantize(places, ROUND_HALF_UP)
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def _sort_key(v: object) -> tuple:
    """Order values of mixed types deterministically: NULL < bool < number < text."""
    if v is None:
        return (0, 0)
    if isinstance(v, bool):
        return (1, int(v))
    if isinstance(v, Decimal):
        return (2, v)
    return (3, str(v))


def _column(df: pd.DataFrame, i: int) -> list:
    return [normalise_value(v) for v in df.iloc[:, i]]


def _same_values(a: list, b: list) -> bool:
    """Two columns hold the same multiset of values (precision-aware)."""
    return len(a) == len(b) and all(
        values_equal(x, y) for x, y in zip(sorted(a, key=_sort_key), sorted(b, key=_sort_key), strict=True))


def align_columns(gold: pd.DataFrame, pred: pd.DataFrame) -> list[int] | None:
    """For each gold column, the index of a predicted column with the same values (or None)."""
    pred_cols = [_column(pred, j) for j in range(pred.shape[1])]
    used: list[int] = []
    for i in range(gold.shape[1]):
        gold_col = _column(gold, i)
        match = next((j for j, col in enumerate(pred_cols)
                      if j not in used and _same_values(gold_col, col)), None)
        if match is None:
            return None
        used.append(match)
    return used


def _rows(df: pd.DataFrame, columns: list[int]) -> list[tuple]:
    return [tuple(normalise_value(row[j]) for j in columns) for row in df.itertuples(index=False)]


def _rows_equal(a: tuple, b: tuple) -> bool:
    return all(values_equal(x, y) for x, y in zip(a, b, strict=True))


def _same_multiset(gold_rows: list[tuple], pred_rows: list[tuple]) -> bool:
    """Rows match in any order. Fast path: sort both; fallback: greedy matching."""
    key = lambda r: tuple(_sort_key(v) for v in r)  # noqa: E731
    if all(_rows_equal(a, b) for a, b in zip(sorted(gold_rows, key=key), sorted(pred_rows, key=key),
                                             strict=True)):
        return True
    remaining = list(pred_rows)
    for row in gold_rows:
        hit = next((k for k, cand in enumerate(remaining) if _rows_equal(row, cand)), None)
        if hit is None:
            return False
        remaining.pop(hit)
    return True


def _outer_order(sql: str) -> exp.Order | None:
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return None
    return tree.args.get("order") if isinstance(tree, exp.Query) else None


def has_order_by(sql: str) -> bool:
    """True if the outermost query has an ORDER BY clause."""
    return _outer_order(sql) is not None


def order_columns(sql: str, result: pd.DataFrame) -> list[int] | None:
    """Positions of the output columns the outer ORDER BY sorts on (ORDER BY name / alias / 1).

    None when any sort key is not an output column - then the full row order is compared.
    """
    order = _outer_order(sql)
    if order is None:
        return None
    names = list(result.columns)
    positions = []
    for key in order.expressions:
        node = key.this
        if isinstance(node, exp.Literal) and node.is_int and 1 <= int(node.this) <= len(names):
            positions.append(int(node.this) - 1)
        elif isinstance(node, exp.Column) and node.name in names:
            positions.append(names.index(node.name))
        else:
            return None
    return positions


def results_match(gold: pd.DataFrame, pred: pd.DataFrame, ordered: bool = False,
                  sort_keys: list[int] | None = None,
                  key_columns: list[str] | None = None) -> bool:
    """Execution accuracy for one question.

    ordered=True requires the same row order. If `sort_keys` (gold column positions from the gold
    ORDER BY) are given, only the order of those values must match, so rows that tie on the
    sort key may appear in any order - both orders are correct answers.
    key_columns: the gold columns a correct answer must contain (e.g. just the city for "Which
    city ...?"); other gold columns such as supporting counts become optional.
    """
    if key_columns:
        gold = gold[key_columns]
    if len(gold) != len(pred) or pred.shape[1] < gold.shape[1]:
        return False
    columns = align_columns(gold, pred)
    if columns is None:
        return False
    gold_rows = _rows(gold, list(range(gold.shape[1])))
    pred_rows = _rows(pred, columns)
    if not _same_multiset(gold_rows, pred_rows):
        return False
    if not ordered:
        return True
    keys = sort_keys if sort_keys is not None else list(range(gold.shape[1]))
    return all(_rows_equal(tuple(g[k] for k in keys), tuple(p[k] for k in keys))
               for g, p in zip(gold_rows, pred_rows, strict=True))
