"""SQL guardrails: parse LLM SQL with sqlglot and reject anything unsafe (SPEC 9.3).

We inspect the parsed syntax tree (AST) instead of using regex, so tricks like comments,
odd casing or extra statements cannot hide a DROP TABLE.
"""
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from src.config import DATASETS, MAX_ROWS, SQL_DIALECT

# Node types that change data or the database itself.
FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create, exp.TruncateTable,
    exp.Grant, exp.Copy, exp.Merge, exp.Command, exp.Into, exp.Set, exp.Transaction,
    exp.Commit, exp.Rollback, exp.Use, exp.LoadData,
)
FORBIDDEN_FUNCTIONS = {"pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
                       "dblink", "dblink_exec", "set_config", "pg_terminate_backend",
                       "pg_cancel_backend", "pg_reload_conf", "current_setting", "query_to_xml",
                       "pg_stat_file", "copy"}
FORBIDDEN_PREFIXES = ("lo_", "pg_read", "pg_write", "dblink")


class GuardrailError(ValueError):
    """Raised when SQL is not safe to run. The message is shown to the user."""


def _parse_single(sql: str, dialect: str) -> exp.Expression:
    """Rule 1: must parse in the source's SQL dialect and contain exactly one statement."""
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except ParseError as err:
        raise GuardrailError(f"SQL could not be parsed: {str(err).splitlines()[0]}") from err
    if len(statements) != 1:
        raise GuardrailError(f"Expected exactly one SQL statement, got {len(statements)}.")
    return statements[0]


def _check_is_select(tree: exp.Expression) -> None:
    """Rules 2 + 3: top level is a SELECT (or UNION of SELECTs) and nothing writes anywhere."""
    if not isinstance(tree, exp.Query):
        raise GuardrailError(f"Only SELECT queries are allowed (got {tree.key.upper()}).")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise GuardrailError(f"Statement type {node.key.upper()} is not allowed.")


def _check_tables(tree: exp.Expression, schema: str) -> None:
    """Rule 4: every table must live in the selected dataset's schema."""
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        db = (table.db or "").lower()
        if not name:  # e.g. table functions like generate_series()
            continue
        if db and db != schema:
            raise GuardrailError(f"Table {db}.{name} is outside the '{schema}' dataset.")
        if not db and name in cte_names:
            continue
        if name.startswith("pg_") or db in ("pg_catalog", "information_schema"):
            raise GuardrailError(f"System table {name} is not allowed.")


def _check_functions(tree: exp.Expression) -> None:
    """Rule 5: block functions that can sleep, read files or reach other databases."""
    for func in tree.find_all(exp.Func):
        name = (func.name if isinstance(func, exp.Anonymous) else func.sql_name()).lower()
        if name in FORBIDDEN_FUNCTIONS or name.startswith(FORBIDDEN_PREFIXES):
            raise GuardrailError(f"Function {name}() is not allowed.")


def _ensure_limit(tree: exp.Expression) -> exp.Expression:
    """Rule 6: add LIMIT MAX_ROWS to the outer query if it has none."""
    if tree.args.get("limit") is None:
        tree = tree.limit(MAX_ROWS)
    return tree


def validate_sql(sql: str, schema: str, dialect: str = SQL_DIALECT) -> str:
    """Return a cleaned, safe SQL string for `schema` in `dialect`, or raise GuardrailError."""
    if schema not in DATASETS:
        raise GuardrailError(f"Unknown dataset '{schema}'.")
    if not sql or not sql.strip():
        raise GuardrailError("The model returned no SQL.")
    tree = _parse_single(sql, dialect)
    _check_is_select(tree)
    _check_tables(tree, schema)
    _check_functions(tree)
    # pretty=True: one clause per line, so the SQL shown to users is readable. Same tree, same meaning.
    return _ensure_limit(tree).sql(dialect=dialect, pretty=True)
