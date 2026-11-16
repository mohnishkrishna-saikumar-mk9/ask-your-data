# CLAUDE.md — Ask Your Data

AI Text-to-SQL analytics assistant (IPL, Indian e-commerce, campus placements) built with Python,
PostgreSQL, Streamlit and LLMs. It is a **portfolio project for a B.Tech student** targeting Software,
AI and AI Data Analytics roles.

**The full specification and roadmap is in `SPEC.md`. Read it before starting any work.**

## How to work
1. Follow the phases in `SPEC.md` Section 14 **in order**. Don't start a new phase until the current one's tests pass.
2. At the start of a session, say which phase and item you're on. At the end, tick the boxes you finished in `SPEC.md`.
3. Before writing a loader, **profile the real CSV first** (headers, dtypes, nulls, 5 sample rows). If it differs from SPEC Section 7, update the spec and tell the user.
4. After each phase:
   - run `ruff check .` and `pytest`
   - add a section to `docs/LEARNING_NOTES.md` explaining, in simple English, what was built, the key concepts (e.g. window functions, guardrails, execution accuracy) and 3 likely interview questions with answers
   - suggest a git commit message (conventional style: `feat:`, `fix:`, `docs:`, `test:`)
5. Keep commits small and frequent. The commit history is part of the portfolio.

## Environment
- OS: **Windows**. Give PowerShell commands. Project root: `D:\Self project\ask-your-data`
- Virtual env: `.venv\Scripts\activate`
- Run modules from the root with `python -m ...` (e.g. `python -m scripts.load_ipl`)
- Streamlit: `streamlit run app/Home.py`
- Settings come from `.env` (copy `.env.example`). Never print or commit secrets.

## Rules
- **Never commit:** `.env`, `data/raw/*`, `.pkl`, `__pycache__`, `.db`, videos, `.docx`/`.pptx`. Keep the repo small.
- **Every LLM-generated SQL goes through `src/guardrails.py`** and then `src/db.run_query` (read-only, timeout, row cap). No exceptions.
- **No hard-coded model names in logic.** Models come from `.env` as `provider:model_id`.
- All DB access uses SQLAlchemy `text()` with bound parameters. No string-formatting of user input into SQL (except via the guardrail-validated LLM SQL path).
- Every SQL file in `sql/analysis` has the header comment format from SPEC Section 8.
- Every table and column gets a `COMMENT ON`. The LLM depends on these.
- Code style: type hints, short docstrings, small functions, `ruff` clean. Prefer clear over clever. The owner must be able to explain every line in an interview.
- Tests must not call real LLM APIs. Mock the client.
- Don't add heavy dependencies (LangChain, vector DBs, Docker) without asking. They're not needed here.
- Don't inflate the README with claims that aren't backed by code or measured results.

## Existing files (Phase 0)
- `src/config.py`: DATABASE_URL, DATASETS dict (8 sources), SQL_DIALECT, QUERY_TIMEOUT_MS, MAX_ROWS
- `src/db.py`: `get_engine()`, `run_query(sql, params, schema)` (read-only transaction + timeout + row cap)
- `scripts/check_setup.py`: connection test, creates and verifies all 8 dataset schemas
- `sql/00_create_schemas.sql`
