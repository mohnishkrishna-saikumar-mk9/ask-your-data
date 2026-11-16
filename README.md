# Ask Your Data - AI Text-to-SQL Analytics Assistant

Ask questions in plain English about **IPL cricket**, **Indian e-commerce sales** or **campus placements**,
and get back the SQL, a results table and a chart.

> Work in progress - built step by step. Sections marked TODO get filled in as each step is completed.

## Tech stack
Python · pandas · PostgreSQL · SQLAlchemy · Streamlit · Plotly · LLM (Groq / Gemini / OpenRouter) · sqlglot · pytest

## Project structure
```
ask-your-data/
├── src/            # config, database helpers (later: LLM + guardrails)
├── scripts/        # one-off scripts: setup check, data loaders
├── sql/            # schema files + hand-written analysis queries
├── data/raw/       # downloaded CSVs (not committed - see "Data")
├── app/            # Streamlit app (Step 3)
├── eval/           # 50-question accuracy benchmark (Step 5)
└── tests/          # pytest tests
```

## Setup (Windows)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then edit .env with your Postgres password
python -m scripts.check_setup
```

## Data
TODO (Step 2)

## Results
TODO - accuracy and latency per model (Step 5)
