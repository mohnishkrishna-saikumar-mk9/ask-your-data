"""Bridge Streamlit Cloud secrets into environment variables.

Locally, settings come from `.env`. On Streamlit Community Cloud they are typed into the app's
Secrets page and exposed as `st.secrets`. `src/` only reads environment variables (so the engine
does not depend on Streamlit), so this copies top-level secrets into `os.environ` - it must run
before anything from `src` is imported. Existing environment variables are never overwritten.
"""
import os

import streamlit as st


def secrets_to_env() -> int:
    """Copy top-level st.secrets values into os.environ; return how many were copied."""
    try:
        items = dict(st.secrets)
    except Exception:  # no secrets.toml (normal locally: .env is used instead)
        return 0
    copied = 0
    for key, value in items.items():
        if isinstance(value, str | int | float | bool) and key not in os.environ:
            os.environ[key] = str(value)
            copied += 1
    return copied
