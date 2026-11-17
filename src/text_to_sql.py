"""Orchestrates one question end-to-end (SPEC 9.4):

cache lookup -> build prompt -> LLM -> extract SQL -> guardrails -> run
-> on DB error, ONE retry with the error appended -> cache store.
"""
import time
from dataclasses import dataclass, field

import pandas as pd

from src import cache
from src.charts import ChartSpec, pick_chart
from src.config import LLM_DEFAULT_MODEL, LLM_FALLBACK_MODEL, SQL_DIALECT
from src.db import run_query
from src.guardrails import GuardrailError, validate_sql
from src.llm.client import CompleteFn, Messages, complete
from src.llm.prompts import build_messages, build_retry_messages, extract_sql
from src.schema_context import get_schema_context


@dataclass
class Answer:
    """Everything the UI and the benchmark need to know about one answer."""

    question: str
    dataset: str
    model: str
    sql: str = ""
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    chart: ChartSpec = field(default_factory=lambda: ChartSpec("table"))
    llm_ms: float = 0.0
    db_ms: float = 0.0
    attempts: int = 0
    error: str | None = None
    error_kind: str | None = None  # 'guardrail' | 'db' | 'llm'
    cached: bool = False

    @property
    def ok(self) -> bool:
        """True when the question was answered without any error."""
        return self.error is None


def _ask_llm(messages: Messages, models: list[str], llm: CompleteFn,
             answer: Answer) -> str:
    """Try each model in order; the first one that responds wins (automatic fallback)."""
    last_error: Exception | None = None
    for model in models:
        try:
            text, ms = llm(messages, model)
            answer.llm_ms += ms
            answer.model = model
            return text
        except Exception as err:  # rate limit, network, bad key ... -> try the next model
            last_error = err
    raise RuntimeError(f"All models failed. Last error: {last_error}")


def _execute(sql: str, dataset: str, answer: Answer, dialect: str) -> pd.DataFrame:
    """Guardrails first, then the read-only database. Records DB time."""
    safe_sql = validate_sql(sql, dataset, dialect)
    answer.sql = safe_sql
    start = time.perf_counter()
    df = run_query(safe_sql, schema=dataset)
    answer.db_ms += (time.perf_counter() - start) * 1000
    return df


def _models_to_try(model: str, fallback: bool) -> list[str]:
    """The chosen model first, then the fallback model if there is a different one."""
    use_fallback = fallback and LLM_FALLBACK_MODEL and model != LLM_FALLBACK_MODEL
    return [model, LLM_FALLBACK_MODEL] if use_fallback else [model]


def _answer_from_cache(hit: dict, answer: Answer, dialect: str) -> bool:
    """Re-run a cached SQL answer. False if the entry no longer works (then answer fresh)."""
    answer.cached, answer.model = True, hit["model"]
    try:
        answer.df = _execute(hit["sql"], answer.dataset, answer, dialect)
        return True
    except Exception:  # stale cache entry
        answer.cached, answer.sql = False, ""
        return False


def _run_with_one_retry(sql: str, messages: Messages, answer: Answer, llm: CompleteFn,
                        dialect: str) -> None:
    """Run the SQL. On a database error, send the error back to the model once (FR-12).
    Unsafe SQL is never retried. Fills answer.df, or answer.error + error_kind."""
    for attempt in (1, 2):
        answer.attempts = attempt
        try:
            answer.df = _execute(sql, answer.dataset, answer, dialect)
            answer.error = answer.error_kind = None
            return
        except GuardrailError as err:
            answer.sql, answer.error, answer.error_kind = sql, str(err), "guardrail"
            return
        except Exception as err:
            answer.sql, answer.error, answer.error_kind = sql, str(err).splitlines()[0], "db"
            if attempt == 2:
                return
            try:
                retry = build_retry_messages(messages, sql, answer.error)
                sql = extract_sql(_ask_llm(retry, [answer.model], llm, answer))
            except Exception as llm_err:
                answer.error, answer.error_kind = str(llm_err), "llm"
                return


def answer_question(question: str, dataset: str, model: str | None = None,
                    variant: str = "full", llm: CompleteFn = complete,
                    use_cache: bool = True, fallback: bool = True,
                    dialect: str = SQL_DIALECT) -> Answer:
    """Answer a natural-language question about `dataset`. Never raises; errors go in Answer.

    Steps: cache -> prompt -> LLM (with fallback model) -> extract SQL -> guardrails ->
    read-only run (one self-correction on a DB error) -> auto-chart -> cache.
    """
    model = model or LLM_DEFAULT_MODEL
    answer = Answer(question=question, dataset=dataset, model=model)
    key = cache.cache_key(dataset, question, model, variant, dialect)

    hit = cache.get(key) if use_cache else None
    if hit and _answer_from_cache(hit, answer, dialect):
        answer.chart = pick_chart(answer.df)
        return answer

    try:
        messages = build_messages(question, dataset, get_schema_context(dataset), variant, dialect)
        sql = extract_sql(_ask_llm(messages, _models_to_try(model, fallback), llm, answer))
    except Exception as err:
        answer.error, answer.error_kind = str(err), "llm"
        return answer

    _run_with_one_retry(sql, messages, answer, llm, dialect)
    if answer.ok:
        answer.chart = pick_chart(answer.df)
        if use_cache:
            cache.put(key, {"sql": answer.sql, "model": answer.model})
    return answer
