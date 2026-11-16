"""The SQL dialect is a parameter, not an assumption (SPEC 9 design rule)."""
from src.guardrails import validate_sql
from src.llm.prompts import build_messages


def one_line(sql: str) -> str:
    """Guardrails pretty-print SQL over several lines; compare ignoring layout."""
    return " ".join(sql.split())


def test_guardrails_parse_and_render_in_given_dialect() -> None:
    mysql = validate_sql("SELECT `name` FROM t", "placements", dialect="mysql")
    assert one_line(mysql) == "SELECT `name` FROM t LIMIT 1000"
    pg = validate_sql('SELECT "name" FROM t', "placements", dialect="postgres")
    assert one_line(pg) == 'SELECT "name" FROM t LIMIT 1000'


def test_output_is_pretty_printed() -> None:
    sql = validate_sql("SELECT a, b FROM t WHERE a > 1 AND b < 2", "placements")
    assert sql.splitlines()[0] == "SELECT" and "\nWHERE" in sql


def test_prompt_names_the_dialect() -> None:
    system = build_messages("q", "placements", "", "zero_shot", dialect="sqlite")[0]["content"]
    assert "expert SQLite analyst" in system
    default = build_messages("q", "placements", "", "zero_shot")[0]["content"]
    assert "expert PostgreSQL analyst" in default
