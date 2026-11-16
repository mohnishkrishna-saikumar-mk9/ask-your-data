# Learning Notes — Ask Your Data

Plain-English notes on what was built in each phase, the ideas behind it, and questions an
interviewer is likely to ask. Read these before an interview.

---

## Phase 0 — Setup

### What was built
- `requirements.txt` + `pyproject.toml`: one place for dependencies, lint rules (ruff) and test
  settings (pytest markers).
- `src/config.py`: every setting comes from `.env`. It holds the `DATASETS` registry (8 data
  sources, ordered from 1 table to 11 tables) and `SQL_DIALECT`.
- `src/db.py`: two engines — an **admin** engine for loaders (they create tables) and a
  **read-only** engine for the app. `run_query()` wraps every query in a READ ONLY transaction
  with a 10 s timeout and a 1,000-row cap.
- `sql/00_create_schemas.sql` + `scripts/check_setup.py`: create one PostgreSQL schema per
  dataset and verify all 8 exist.

### Key concepts
- **Schema per dataset.** A *schema* is a namespace inside one database (`ipl.matches`,
  `olist.orders`). The LLM is only shown one schema, and the guardrails reject any other, so a
  question about cricket can never read shop data.
- **Least privilege.** The app's database user can only `SELECT`. Writing is blocked by the
  database itself, not just by our Python code.
- **Defence in depth.** Several independent safety layers (guardrails, read-only role, read-only
  transaction, timeout, row cap). If one has a bug, the others still protect the data.
- **Dataset-agnostic, dialect-aware design.** Nothing in `src/` names a table or column. The SQL
  dialect (`postgres`, `mysql`, `sqlite`, `duckdb`) is a parameter passed into the guardrails and
  the prompt, so another database can be plugged in later without rewriting the engine.

### Interview questions
1. **Why not let the app connect as the admin user?**
   If anything goes wrong (a guardrail bug, a prompt-injection trick) an admin connection could
   delete data. A SELECT-only user means the worst case is a slow read, which the timeout stops.
2. **What is `statement_timeout` and why 10 seconds?**
   PostgreSQL cancels any statement that runs longer than this. An LLM can write a huge
   cross-join by mistake; the timeout keeps the app responsive and protects the shared database.
3. **How would you add a ninth dataset?**
   One loader script, one `sql/schema/<name>.sql`, one optional `knowledge/<name>/` folder and one
   entry in `DATASETS`. The engine needs no changes because it reads the schema at runtime.

---

## Phase 1 — Data loading (IPL, the reference loader)

### What was built
- `sql/schema/ipl.sql`: tables `matches` and `deliveries` with primary/foreign keys, indexes,
  two helper **views** (`batting_innings`, `bowling_innings`) and a `COMMENT ON` for every table
  and column.
- `scripts/_loader_utils.py`: shared helpers used by every loader — read CSV as text, clean
  headers (strip the BOM `﻿` and spaces), turn `""`/`NA`/`N/A`/`nan` into NULL, drop
  `Unnamed:` columns, bulk-load with `COPY`, print a load report.
- `scripts/load_ipl.py`: cleaning rules as small pure functions, then one transactional load.
- Result on the real data: 1,095 matches and 260,920 deliveries loaded, 0 dropped, 0 orphans,
  58 raw venue spellings merged into 36 venues.

### Key concepts
- **ETL** (Extract, Transform, Load). Extract = read the CSV. Transform = pure `clean_*`
  functions (DataFrame in, DataFrame out) that can be unit-tested without a database. Load = `COPY`.
- **Read as text first.** If pandas guesses types it can silently turn IDs into floats or dates
  into the wrong format. Reading everything as text and converting each column on purpose is safer.
- **Idempotent load.** The schema file starts with `DROP ... IF EXISTS`, and drop + create + copy
  all run in **one transaction**. Running the loader twice gives the same result, and a failure
  rolls back completely, so there are never half-loaded tables.
- **COPY vs INSERT.** `COPY` streams all rows in one command; for 260K rows that is seconds
  instead of minutes.
- **Data-quality decisions** (each one is logged):
  - season is taken from the match **date** (`2007/08` in the raw data is ambiguous);
  - renamed franchises are merged (Delhi Daredevils → Delhi Capitals), but Deccan Chargers and
    Sunrisers Hyderabad are kept separate because they are different franchises;
  - overs are 0-based, so `phase` = powerplay (0–5), middle (6–14), death (15–19);
  - innings 3–6 are super overs and are excluded from the batting/bowling views.
- **Views encode domain rules once.** "Balls faced excludes wides" and "run-outs are not the
  bowler's wicket" are easy to get wrong. Putting them in a view means analysts and the LLM
  both get them right automatically.
- **`COMMENT ON` is the data dictionary.** The LLM prompt is built from these comments, so a
  clearer comment directly improves answer accuracy without any code change.
- **Validation against known facts.** After loading, the results were checked against real IPL
  records: CSK and MI 5 titles each, KKR 3, V Kohli 8,004 runs, Purple Cap winners 2020–2024.

### Interview questions
1. **How did you make sure the cleaned data was correct?**
   Three layers: unit tests on each cleaning function using small, deliberately messy fixture
   CSVs; database checks (row counts, zero orphan foreign keys, every column has a comment); and
   comparing aggregate results with publicly known facts (titles, top run scorer).
2. **Why does `is_out` use `COALESCE(BOOL_OR(...), FALSE)`?**
   Comparing anything with NULL gives NULL, and `BOOL_OR` over only NULLs is NULL. A batter who
   was never dismissed would show NULL instead of FALSE. A test caught this; COALESCE fixes it.
3. **Why a view and not a precomputed table?**
   A view is always in sync with the base tables and costs nothing to maintain. If it became too
   slow I would switch to a materialized view refreshed by the loader — a trade of freshness for
   speed.
