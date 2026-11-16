"""Ask page: natural-language question -> SQL -> guarded execution -> table + chart."""
import streamlit as st

from app.ui import dataset_picker, db_ready, show_result
from src.config import EVAL_MODELS, LLM_DEFAULT_MODEL, LLM_FALLBACK_MODEL
from src.glossary import load_example_questions
from src.llm.providers import available_models
from src.text_to_sql import answer_question

st.title("Ask a question")

dataset = dataset_picker("ask_dataset")
candidates = list(dict.fromkeys(m for m in [LLM_DEFAULT_MODEL, LLM_FALLBACK_MODEL, *EVAL_MODELS] if m))
models = available_models(candidates)
if not models:
    st.warning("No LLM is configured. Add an API key and LLM_DEFAULT_MODEL to .env "
               "(see .env.example).", title="No model available")
    st.stop()
model = st.sidebar.selectbox("Model", models, key="ask_model")
st.sidebar.caption("If the chosen model fails, the fallback model answers automatically.")

if not db_ready():
    st.stop()

st.caption("Try an example:")
with st.container(horizontal=True):
    for i, example in enumerate(load_example_questions(dataset)):
        st.button(example, key=f"example_{dataset}_{i}",
                  on_click=st.session_state.update,
                  kwargs={"question": example, "_run_example": True})

with st.form("ask_form"):
    question = st.text_input("Your question", key="question",
                             placeholder="e.g. Top 5 batters by strike rate in death overs since 2020")
    submitted = st.form_submit_button("Ask", icon=":material/send:", type="primary")

if submitted or st.session_state.pop("_run_example", False):
    if not question.strip():
        st.warning("Type a question first.")
        st.stop()
    with st.spinner("Writing SQL and running it..."):
        answer = answer_question(question, dataset, model)

    stats = f"`{answer.model}` · LLM {answer.llm_ms:,.0f} ms · DB {answer.db_ms:,.0f} ms"
    stats += f" · {len(answer.df):,} rows" + (" · cached" if answer.cached else "")
    if answer.attempts > 1:
        stats += " · self-corrected after 1 error"
    st.caption(stats)

    if answer.sql:
        with st.expander("Generated SQL", expanded=not answer.ok):
            st.code(answer.sql, language="sql")

    if answer.error_kind == "guardrail":
        st.error(answer.error, title="Blocked by safety guardrails")
    elif answer.error_kind == "db":
        st.error(answer.error, title="The query failed even after one self-correction")
    elif answer.error_kind == "llm":
        st.error(answer.error, title="The language model could not be reached")
    elif answer.df.empty:
        st.info("The query ran but returned no rows.")
    else:
        show_result(answer.df)
