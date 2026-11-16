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

st.set_page_config(page_title="Ask Your Data", page_icon=":material/query_stats:", layout="wide")

pages = [
    st.Page("pages/0_Overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("pages/1_Ask.py", title="Ask", icon=":material/chat:"),
    st.Page("pages/2_Dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page("pages/3_Query_Library.py", title="Query library", icon=":material/library_books:"),
    st.Page("pages/4_Evaluation.py", title="Evaluation", icon=":material/fact_check:"),
]
st.navigation(pages).run()
