"""Prompt templates and the three benchmark variants (SPEC 9.1).

- zero_shot: schema only
- few_shot:  schema + examples
- full:      schema + examples + metric glossary + "prefer the views" hint
"""
import re

from src.config import SQL_DIALECT
from src.glossary import load_few_shots, render_glossary

VARIANTS = ("zero_shot", "few_shot", "full")

# Human-readable names for sqlglot dialects, used in the system prompt.
DIALECT_NAMES = {"postgres": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite",
                 "duckdb": "DuckDB", "tsql": "SQL Server"}

BASE_RULES = (
    "You are an expert {dialect} analyst. Write ONE read-only SELECT query that answers the "
    "question.\nRules: use only the tables below and always qualify them with the schema name; "
    "always add LIMIT 100 unless the question asks for a single value; "
    "return ONLY the SQL inside ```sql``` fences, with no explanation."
)
FULL_EXTRA_RULES = (
    "\nPrefer the provided VIEWs over raw tables when they contain what you need. "
    "Follow the METRIC DEFINITIONS exactly."
)


def build_messages(question: str, dataset: str, schema_text: str, variant: str = "full",
                   dialect: str = SQL_DIALECT) -> list[dict[str, str]]:
    """Return chat messages (system + user) for the chosen prompt variant and SQL dialect."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}")
    system = BASE_RULES.format(dialect=DIALECT_NAMES.get(dialect, dialect))
    system += FULL_EXTRA_RULES if variant == "full" else ""
    parts = [f"SCHEMA ({dataset}):\n{schema_text}"]
    if variant == "full":
        parts.append(f"METRIC DEFINITIONS:\n{render_glossary(dataset)}")
    if variant in ("few_shot", "full"):
        examples = "\n\n".join(f"Q: {ex['question']}\nSQL:\n```sql\n{ex['sql'].strip()}\n```"
                               for ex in load_few_shots(dataset))
        parts.append(f"EXAMPLES:\n{examples}")
    parts.append(f"QUESTION: {question}")
    return [{"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(parts)}]


def build_retry_messages(messages: list[dict[str, str]], bad_sql: str,
                         error: str) -> list[dict[str, str]]:
    """Self-correction (FR-12): show the model its SQL and the database error, ask for a fix."""
    return messages + [
        {"role": "assistant", "content": f"```sql\n{bad_sql}\n```"},
        {"role": "user", "content": f"That query failed with this error:\n{error}\n"
                                    "Fix it. Return ONLY the corrected SQL in ```sql``` fences."},
    ]


_FENCE = re.compile(r"```(?:\s*(?:sql|postgresql|postgres|pgsql))?\s*\n?(.*?)```",
                    re.IGNORECASE | re.DOTALL)
_THINK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_START = re.compile(r"\b(WITH|SELECT)\b", re.IGNORECASE)


def extract_sql(text: str) -> str:
    """Pull the SQL out of a messy LLM reply (FR-10).

    Order: strip <think> blocks -> last ```sql fenced block -> text from the first
    WITH/SELECT keyword. Trailing semicolons are removed.
    """
    text = _THINK.sub("", text or "").strip()
    blocks = [b.strip() for b in _FENCE.findall(text) if b.strip()]
    if blocks:
        sql = blocks[-1]
    else:
        match = _START.search(text)
        sql = text[match.start():] if match else text
    return sql.strip().rstrip(";").strip()
