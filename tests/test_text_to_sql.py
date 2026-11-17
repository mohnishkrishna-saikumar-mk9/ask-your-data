"""Engine tests with a FAKE LLM (no real API calls ever)."""
from pathlib import Path

import pytest

from src import cache
from src.llm.providers import available_models, parse_model
from src.text_to_sql import answer_question


def fake_llm(*replies: str):
    """Return an llm function that plays back `replies` in order and records each call."""
    calls: list[list[dict]] = []

    def _llm(messages: list[dict], model: str) -> tuple[str, float]:
        calls.append(messages)
        reply = replies[len(calls) - 1]
        if reply == "RAISE":
            raise RuntimeError("rate limited")
        return reply, 5.0

    _llm.calls = calls  # type: ignore[attr-defined]
    return _llm


def test_parse_model() -> None:
    provider, model_id = parse_model("openrouter:qwen/qwen-2.5:free")
    assert provider.name == "openrouter" and model_id == "qwen/qwen-2.5:free"
    provider, model_id = parse_model("omniroute:auto/coding:fast")  # only the first ':' splits
    assert provider.name == "omniroute" and model_id == "auto/coding:fast"
    with pytest.raises(ValueError):
        parse_model("no-colon")
    with pytest.raises(ValueError):
        parse_model("madeup:x")


def test_available_models_filters_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert available_models(["groq:x", "ollama:llama3"]) == ["ollama:llama3"]


def test_cache_key_normalises() -> None:
    assert cache.cache_key("ipl", "Top  Batters") == cache.cache_key("ipl", "top batters")


def test_cache_roundtrip(tmp_path: Path) -> None:
    cache.put("k", {"sql": "SELECT 1"}, cache_dir=tmp_path)
    assert cache.get("k", cache_dir=tmp_path) == {"sql": "SELECT 1"}
    assert cache.get("missing", cache_dir=tmp_path) is None


@pytest.fixture
def temp_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the answer cache at a temp folder so tests never share state."""
    monkeypatch.setattr(cache.get, "__defaults__", (tmp_path,))
    monkeypatch.setattr(cache.put, "__defaults__", (tmp_path,))


@pytest.mark.db
def test_happy_path(loaded_db: None, temp_cache: None) -> None:
    llm = fake_llm("```sql\nSELECT COUNT(*) AS n FROM placements.students\n```")
    ans = answer_question("how many students?", "placements", "groq:m", llm=llm, fallback=False)
    assert ans.ok, ans.error
    assert ans.df["n"][0] == 30 and ans.chart.kind == "kpi" and ans.attempts == 1
    assert "LIMIT" in ans.sql


@pytest.mark.db
def test_self_correction_retry(loaded_db: None, temp_cache: None) -> None:
    llm = fake_llm("SELECT nope FROM placements.students",
                   "SELECT COUNT(*) AS n FROM placements.students")
    ans = answer_question("q", "placements", "groq:m", llm=llm, fallback=False)
    assert ans.ok and ans.attempts == 2
    assert "nope" in llm.calls[1][-1]["content"]  # the DB error was sent back to the model


@pytest.mark.db
def test_retry_only_once(loaded_db: None, temp_cache: None) -> None:
    llm = fake_llm("SELECT nope FROM placements.students", "SELECT nope2 FROM placements.students")
    ans = answer_question("q", "placements", "groq:m", llm=llm, fallback=False)
    assert not ans.ok and ans.error_kind == "db" and ans.attempts == 2 and len(llm.calls) == 2


@pytest.mark.db
def test_guardrail_rejection_not_executed(loaded_db: None, temp_cache: None) -> None:
    llm = fake_llm("DROP TABLE placements.students")
    ans = answer_question("q", "placements", "groq:m", llm=llm, fallback=False)
    assert ans.error_kind == "guardrail" and len(llm.calls) == 1


@pytest.mark.db
def test_fallback_model_used(loaded_db: None, temp_cache: None,
                             monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.text_to_sql.LLM_FALLBACK_MODEL", "gemini:backup")
    llm = fake_llm("RAISE", "SELECT 1 AS x")
    ans = answer_question("q", "placements", "groq:main", llm=llm)
    assert ans.ok and ans.model == "gemini:backup"


@pytest.mark.db
def test_second_ask_is_cached(loaded_db: None, temp_cache: None) -> None:
    llm = fake_llm("SELECT COUNT(*) AS n FROM placements.students")
    first = answer_question("cached q", "placements", "groq:m", llm=llm, fallback=False)
    second = answer_question("Cached  Q", "placements", "groq:m", llm=llm, fallback=False)
    assert first.ok and second.cached and len(llm.calls) == 1


@pytest.mark.db
def test_schema_context_has_comments(loaded_db: None) -> None:
    from src.schema_context import get_schema_context

    text = get_schema_context("ipl")
    assert "VIEW ipl.batting_innings" in text and "-- Batter on strike" in text
