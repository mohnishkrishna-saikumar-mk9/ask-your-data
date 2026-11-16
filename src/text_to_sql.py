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


def answer_question(question: str, dataset: str, model: str | None = None,
                    variant: str = "full", llm: CompleteFn = complete,
                    use_cache: bool = True, fallback: bool = True,
                    dialect: str = SQL_DIALECT) -> Answer:
    """Answer a natural-language question about `dataset`. Never raises; errors go in Answer."""
    model = model or LLM_DEFAULT_MODEL
    models = [model] + ([LLM_FALLBACK_MODEL] if fallback and LLM_FALLBACK_MODEL
                        and model != LLM_FALLBACK_MODEL else [])
    answer = Answer(question=question, dataset=dataset, model=model)
    key = cache.cache_key(dataset, question, model, variant, dialect)

    hit = cache.get(key) if use_cache else None
    if hit:
        answer.cached, answer.model = True, hit["model"]
        try:
            answer.df = _execute(hit["sql"], dataset, answer, dialect)
            answer.chart = pick_chart(answer.df)
            return answer
        except Exception:  # stale cache entry -> answer fresh
            answer.cached, answer.sql = False, ""

    try:
        messages = build_messages(question, dataset, get_schema_context(dataset), variant, dialect)
        sql = extract_sql(_ask_llm(messages, models, llm, answer))
    except Exception as err:
        answer.error, answer.error_kind = str(err), "llm"
        return answer

    for attempt in (1, 2):
        answer.attempts = attempt
        try:
            answer.df = _execute(sql, dataset, answer, dialect)
            answer.error = answer.error_kind = None
            break
        except GuardrailError as err:
            answer.sql = sql
            answer.error, answer.error_kind = str(err), "guardrail"
            return answer  # unsafe SQL is never retried
        except Exception as err:
            answer.sql = sql
            answer.error, answer.error_kind = str(err).splitlines()[0], "db"
            if attempt == 2:
                return answer
            retry = build_retry_messages(messages, sql, answer.error)
            try:
                sql = extract_sql(_ask_llm(retry, [answer.model], llm, answer))
            except Exception as llm_err:
                answer.error, answer.error_kind = str(llm_err), "llm"
                return answer

    answer.chart = pick_chart(answer.df)
    if use_cache:
        cache.put(key, {"sql": answer.sql, "model": answer.model})
    return answer
