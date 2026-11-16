"""Central settings, read from the .env file (or Streamlit secrets when deployed)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

# Admin URL: used by loaders (they create tables). The app prefers the read-only URL.
DATABASE_URL = os.getenv("DATABASE_URL", "")
READONLY_DATABASE_URL = os.getenv("READONLY_DATABASE_URL", "") or DATABASE_URL

# Registry of built-in data sources. Each lives in its own schema inside one database;
# the LLM only ever sees the selected schema. Ordered easy -> hard (1 table -> 11 tables).
# Adding a dataset = one loader + one sql/schema file + one knowledge/<name>/ folder + one entry here.
DATASETS = {
    "placements": "Campus placements - student scores, specialisation, placed/salary (1 table)",
    "netflix": "Netflix titles with directors, cast, countries and genres (5 tables)",
    "startups": "Indian startup funding rounds and their investors (2 tables)",
    "air_quality": "Daily air quality (AQI, PM2.5 ...) for Indian cities and stations (3 tables)",
    "ecommerce": "Indian Amazon seller sales - orders, products, states, amounts (5 tables)",
    "ipl": "IPL cricket - matches and ball-by-ball deliveries, 2008-2024 (2 tables + 2 views)",
    "olist": "Brazilian marketplace - orders, customers, items, payments, reviews (8 tables)",
    "chinook": "Chinook music store - artists, tracks, invoices, employees (11 tables)",
}

# SQL dialect of the built-in database (a sqlglot dialect name). The engine and guardrails take
# the dialect as a parameter so other databases can be plugged in later (SPEC Phase 8).
SQL_DIALECT = os.getenv("SQL_DIALECT", "postgres")

# Safety limits applied to every query the app runs
QUERY_TIMEOUT_MS = 10_000   # kill any query that runs longer than 10 s
MAX_ROWS = 1_000            # never send more than this many rows to the browser
WORK_MEM_MB = 32            # per-query sort/hash memory (avoids disk spills)

# LLM settings - models are "provider:model_id" strings, never hard-coded in logic.
LLM_DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "")
EVAL_MODELS = [m.strip() for m in os.getenv("EVAL_MODELS", "").split(",") if m.strip()]
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "30"))
