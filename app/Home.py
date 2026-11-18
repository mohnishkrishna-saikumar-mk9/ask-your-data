"""Streamlit entry point: sets up the page config and multipage navigation.

Run from the project root:  streamlit run app/Home.py
"""
import sys
from pathlib import Path

import streamlit as st

# `streamlit run app/Home.py` only puts app/ on the path; add the project root for `src`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# On Streamlit Cloud, settings live in st.secrets; copy them into the environment before any
# page imports `src` (which reads os.environ, exactly like .env locally).
from app.secrets_env import secrets_to_env  # noqa: E402

secrets_to_env()

st.set_page_config(page_title="Ask Your Data", page_icon=":material/query_stats:", layout="wide")

pages = [
    st.Page("app_pages/0_Overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("app_pages/1_Ask.py", title="Ask", icon=":material/chat:"),
    st.Page("app_pages/2_Dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page("app_pages/3_Query_Library.py", title="Query library", icon=":material/library_books:"),
    st.Page("app_pages/4_Evaluation.py", title="Evaluation", icon=":material/fact_check:"),
]
st.navigation(pages).run()
