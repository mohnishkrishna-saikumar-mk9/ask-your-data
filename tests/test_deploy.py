"""Deployment helpers: Streamlit Cloud secrets bridge and the public-demo question limit."""
import os

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import secrets_env
from src.config import ROOT


class FakeStreamlit:
    def __init__(self, secrets: object) -> None:
        self.secrets = secrets


def test_secrets_are_copied_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AYD_TEST_SECRET", raising=False)
    monkeypatch.setenv("AYD_EXISTING", "from-env")
    fake = {"AYD_TEST_SECRET": "abc", "AYD_EXISTING": "from-secrets", "section": {"nested": "x"}}
    monkeypatch.setattr(secrets_env, "st", FakeStreamlit(fake))
    assert secrets_env.secrets_to_env() == 1
    assert os.environ["AYD_TEST_SECRET"] == "abc"
    assert os.environ["AYD_EXISTING"] == "from-env"  # never overwrite an existing variable
    monkeypatch.delenv("AYD_TEST_SECRET")


def test_no_secrets_file_is_fine(monkeypatch: pytest.MonkeyPatch) -> None:
    class Missing:
        def __iter__(self):  # dict(st.secrets) raises when there is no secrets.toml
            raise FileNotFoundError("no secrets.toml")

    monkeypatch.setattr(secrets_env, "st", FakeStreamlit(Missing()))
    assert secrets_env.secrets_to_env() == 0


@pytest.mark.db
def test_demo_question_limit(loaded_db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """With DEMO_MAX_QUESTIONS reached, the Ask page refuses before calling any model."""
    import src.config
    import src.text_to_sql

    calls: list[str] = []
    monkeypatch.setattr(src.config, "LLM_DEFAULT_MODEL", "ollama:test-model")  # no key needed
    monkeypatch.setattr(src.config, "LLM_FALLBACK_MODEL", "")
    monkeypatch.setattr(src.config, "EVAL_MODELS", [])
    monkeypatch.setattr(src.config, "DEMO_MAX_QUESTIONS", 2)
    monkeypatch.setattr(src.text_to_sql, "answer_question",
                        lambda *a, **k: calls.append("asked") or pd.DataFrame())

    at = AppTest.from_file(str(ROOT / "app" / "app_pages" / "1_Ask.py"), default_timeout=60)
    at.session_state["dataset"] = "placements"
    at.session_state["questions_asked"] = 2
    at.run()
    at.text_input(key="question").input("How many students are there?")
    at.button[-1].click().run()  # the form's Ask button
    assert [i.value for i in at.info if "limit" in str(i.value).lower()]
    assert calls == []
