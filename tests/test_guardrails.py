"""Guardrail tests: safe SELECTs pass (with LIMIT added); everything else is rejected."""
import pytest

from src.guardrails import GuardrailError, validate_sql

SAFE = [
    "SELECT * FROM matches",
    "SELECT * FROM ipl.matches WHERE season = 2020",
    "WITH a AS (SELECT * FROM ipl.matches) SELECT * FROM a",
    "SELECT season, COUNT(*) FROM ipl.matches GROUP BY season ORDER BY season",
    "SELECT * FROM ipl.matches WHERE team1 LIKE 'Mum%'",
    "(SELECT 1 AS x) UNION ALL (SELECT 2)",
    "SELECT batter, RANK() OVER (ORDER BY runs DESC) FROM ipl.batting_innings",
    "SELECT 1 -- ; DROP TABLE ipl.matches",
]

UNSAFE = [
    ("SELECT 1; DROP TABLE ipl.matches", "exactly one"),
    ("DROP TABLE ipl.matches", "Only SELECT"),
    ("DELETE FROM ipl.matches", "Only SELECT"),
    ("UPDATE ipl.matches SET winner = 'x'", "Only SELECT"),
    ("INSERT INTO ipl.matches (match_id) VALUES (1)", "Only SELECT"),
    ("TRUNCATE ipl.matches", "Only SELECT"),
    ("CREATE TABLE ipl.x (a int)", "Only SELECT"),
    ("ALTER TABLE ipl.matches ADD COLUMN x int", "Only SELECT"),
    ("GRANT ALL ON ipl.matches TO public", None),
    ("COPY ipl.matches TO STDOUT", "Only SELECT"),
    ("SELECT * INTO ipl.copy_of_matches FROM ipl.matches", "INTO"),
    ("SELECT pg_sleep(10)", "pg_sleep"),
    ("SELECT pg_read_file('/etc/passwd')", "pg_read_file"),
    ("SELECT lo_import('/etc/passwd')", "lo_import"),
    ("SELECT set_config('search_path', 'public', false)", "set_config"),
    ("SELECT * FROM dblink('host=evil', 'select 1') AS t(a int)", None),
    ("SELECT * FROM ecommerce.orders", "outside"),
    ("SELECT * FROM pg_catalog.pg_user", "outside"),
    ("SELECT * FROM information_schema.tables", "outside"),
    ("SELECT * FROM pg_shadow", "System table"),
    ("WITH x AS (DELETE FROM ipl.matches RETURNING *) SELECT * FROM x", None),
    ("", "no SQL"),
    ("SELEC * FRM matches", None),
]


@pytest.mark.parametrize("sql", SAFE)
def test_safe_sql_passes_and_gets_limit(sql: str) -> None:
    out = validate_sql(sql, "ipl")
    assert "LIMIT" in out.upper()


@pytest.mark.parametrize(("sql", "reason"), UNSAFE)
def test_unsafe_sql_rejected(sql: str, reason: str | None) -> None:
    with pytest.raises(GuardrailError, match=reason):
        validate_sql(sql, "ipl")


def test_existing_limit_kept() -> None:
    assert validate_sql("SELECT * FROM ipl.matches LIMIT 5", "ipl").endswith("LIMIT 5")


def test_unknown_dataset_rejected() -> None:
    with pytest.raises(GuardrailError, match="Unknown dataset"):
        validate_sql("SELECT 1", "public")
