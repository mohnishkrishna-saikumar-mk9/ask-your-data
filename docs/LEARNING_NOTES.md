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

---

## Phase 1 (continued) — the other 7 datasets

### What was built
Seven more loaders, one per dataset, all following the IPL pattern (pure cleaning functions →
one transactional load → report). After Phase 1 the database holds 8 schemas with 1 to 11 tables
each, every table and column commented. Details per dataset: `docs/DATA_SOURCES.md`.

### Key concepts
- **Bridge tables for many-to-many (Netflix).** One cell like `"India, United States"` breaks
  First Normal Form (one value per cell). Splitting it into `title_countries(show_id, country)`
  lets SQL answer "how many Indian titles?" with a simple join instead of string matching.
- **Profile before you trust (e-commerce).** The international sales file looked fine in the
  first rows, but half of it was the *same sales pasted again* one column to the right. Loading
  everything would have doubled revenue. I proved the duplication by matching rows between the
  two blocks (100% overlap) before dropping one — a decision backed by evidence, not a guess.
- **Tolerant parsing (startups).** Real dates looked like `12/05.2015`, `05/072018` and `01/07/015`.
  One regex `(\d{1,2})\D+(\d{1,2})\D*(\d{3,4})` plus a real date check parsed all 3,044 of them;
  anything still invalid (like 31 February) becomes NULL and is reported.
- **Outlier detection with domain knowledge (startups).** Rapido showed $3.9 billion — larger
  than Flipkart. The raw value was ₹390 crore entered as dollars. I set it to NULL instead of
  inventing an exchange rate: wrong data is worse than missing data, and the decision is logged.
- **Aggregating to the right grain (Olist).** Geolocation has 1M rows with many points per zip
  prefix. Joining it directly would multiply rows (fan-out). It is aggregated to one row per prefix
  first, so every join stays one-to-one.
- **Surrogate keys when the natural key isn't unique.** Olist's `review_id` repeats, and identical
  international sales lines are real repeat sales, so both tables get a generated `id` primary key.
- **Running a vendor SQL script safely (Chinook).** The script expects to own a whole database.
  The loader strips the database-level lines and runs the rest inside our schema. It drops the
  tables, not the schema, so the read-only user's default privileges survive.
- **A regex lesson.** `[^;]*` ("anything except `;`") also matches newlines. My first pattern ran
  from the words "Drop database" in a comment banner all the way to the next `;`, deleting the
  comment's closing `*/`. Fix: `[^;\n]*`. A regression test now covers it.
- **Fixtures with the hard cases.** Test fixtures are small samples of real rows that always
  include the tricky ones (typo dates, misplaced ratings, shifted rows, duplicate SKUs), so every
  cleaning rule is exercised in CI without the 300 MB of raw data.

### Interview questions
1. **How do you model a column that holds a comma-separated list?**
   Split it into a bridge table with one row per (entity, value) and a composite primary key. It
   follows First Normal Form, makes filtering and counting simple joins, and can be indexed.
2. **You find a value that looks wrong in the source data. What do you do?**
   Verify it against the raw file and an outside fact, then decide: fix it only if the correct
   value is certain, otherwise set it to NULL. Either way log the decision in the loader and the
   data documentation so the analysis stays reproducible and honest.
3. **What is a fan-out join and how did you avoid it?**
   Joining to a table with several rows per key multiplies the rows on the other side, so SUMs
   become too large. I aggregated geolocation to one row per zip prefix before it can be joined,
   and added primary keys so the database guarantees the grain.

---

## Phase 2 — SQL analysis (72 queries) and metric glossaries

### What was built
- 72 hand-written queries in `sql/analysis/<dataset>/`: IPL 20, e-commerce 10, placements 10,
  olist 8, startups 6, air quality 6, netflix 6, chinook 6. Each starts with a header
  (`-- Q:` question, `-- Concepts:` SQL used, `-- Result:` columns) that the Query Library page reads.
- `knowledge/<dataset>/glossary.yaml` for all 8 datasets: exact business definitions
  ("GMV = SUM(price)", "a real customer = customer_unique_id") that are added to the LLM prompt.
- Tests: every query has a header, runs on the fixture data, and never touches another dataset's
  schema; every dataset has a glossary.

### Key concepts (with the file that shows each one)
- **Window functions** compute over related rows without collapsing them:
  - `RANK` / `DENSE_RANK` / `ROW_NUMBER` — ties give 1,1,3 / 1,1,2 / 1,2,3 (`ipl/05`, `ipl/08`, `startups/06`).
  - `LAG` for change vs the previous period (`ipl/11`, `olist/01`, `startups/01`).
  - Running total: `SUM(x) OVER (ORDER BY t ROWS UNBOUNDED PRECEDING)` (`chinook/06`, `olist/05`).
  - Rolling average: `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` = 7-day window (`air_quality/06`).
  - Share inside a group: `SUM(SUM(x)) OVER (PARTITION BY g)` — a window over an aggregate (`ecommerce/03`).
- **Recursive CTE** for hierarchies: an anchor row (the top manager) plus a recursive part that joins
  employees to the rows found so far (`chinook/04`).
- **Anti-join** ("things with no match"): `LEFT JOIN ... WHERE right.id IS NULL` (`chinook/05`) or
  `NOT EXISTS`. **Semi-join** ("things with at least one match"): `EXISTS` (`netflix/04`).
- **Cohort analysis**: find each customer's first purchase month, then check whether they bought
  again within 3 / 6 months (`olist/08`).
- **Conditional aggregation**: `COUNT(*) FILTER (WHERE ...)` / `AVG(x) FILTER (...)` to pivot categories
  into columns in one pass (`netflix/01`, `air_quality/03`).
- **Choosing a fair period**: `olist/01` excludes 2016's handful of test orders, which produced a
  meaningless +1,000,000% "growth". Good analysis checks that the denominator is meaningful.

### Performance: aggregate before you join
Five e-commerce queries joined 129K order lines to orders and then used `COUNT(DISTINCT order_id)`.
Rewritten to sum the lines per order in a CTE first, then join one row per order and use `COUNT(*)`.
Each new version was checked to return *exactly* the same result as the old one (using the benchmark's
comparator) and ran 2–3.5× faster. `EXPLAIN ANALYZE` showed why: `COUNT(DISTINCT)` needs a big sort.

### Bugs found while writing these (good interview stories)
- `ORDER BY movies + tv_shows` fails: output aliases can be used alone in ORDER BY, but not inside
  an expression. Fix: repeat the expression (`netflix/06`).
- `GROUP BY 1` grouped `date_trunc(...)::date`, but the window's ORDER BY used `date_trunc(...)` without
  the cast — PostgreSQL treats them as different expressions. Fix: compute the month in a CTE (`chinook/06`).
- Reading the real results exposed a loader bug: the startups file stores characters as literal
  UTF-8 byte text (`Byju\xe2\x80\x99s`). The loader now *decodes* them (`’`, `é`, non-breaking space)
  instead of deleting them, so BYJU'S variants merge correctly.

### Interview questions
1. **RANK vs DENSE_RANK vs ROW_NUMBER?**
   For scores 90, 90, 80: RANK gives 1, 1, 3 (skips), DENSE_RANK 1, 1, 2 (no gaps), ROW_NUMBER
   1, 2, 3 (always unique, ties broken arbitrarily unless you add a tie-breaker). Use ROW_NUMBER for
   "exactly one per group", RANK/DENSE_RANK when ties should all be kept.
2. **How do you find customers who never ordered / tracks never sold?**
   An anti-join: `LEFT JOIN orders ... WHERE orders.id IS NULL`, or `WHERE NOT EXISTS (subquery)`.
   Avoid `NOT IN (subquery)` when the subquery can return NULL — then it returns no rows at all.
3. **A query is slow because of COUNT(DISTINCT) after a join. What do you do?**
   Aggregate the many-side to one row per key in a CTE first, then join and count rows. Prove the
   rewrite is equivalent by comparing results, and measure before/after with EXPLAIN ANALYZE.

---

## Phase 3 — Streamlit app and dashboards for 8 datasets

### What was built
- `app/Home.py`: page config + `st.navigation` over five pages in `app/app_pages/`.
- **Overview**: one card per dataset with its table and row counts, read from the PostgreSQL catalogue
  (`pg_class.reltuples`, refreshed by `ANALYZE` in the loaders) — no dataset-specific SQL.
- **Dashboard**: one generic renderer + `app/dashboards.py`, which describes each dataset's 4 KPI
  tiles, 4 charts and optional filter (a year/season slider or a month multiselect) as data.
- **Query library**: browse the 72 queries with their question, concepts, SQL, result and auto-chart.
- Caching: `st.cache_data(ttl=3600)` on every query, so a dashboard is instant after its first load.
- Tests: `tests/test_app.py` checks every dashboard definition and renders every page for every
  dataset with Streamlit's `AppTest` on the fixture data.

### Key concepts
- **Configuration over code (data-driven UI).** Instead of 8 `if dataset == ...` branches, each
  dashboard is a small data structure (dataclasses `Dashboard`, `Chart`, `Filter`). The page loops
  over it. Adding a dataset's dashboard is one entry; the renderer never changes. This is the same
  idea as the dataset-agnostic engine.
- **Filters done safely.** KPI queries receive filter values as **bound parameters** (`:lo`, `:hi`,
  `= ANY(:values)`), never string-formatted SQL. Chart data from library queries is filtered in pandas.
- **Caching keyed on inputs.** `st.cache_data` hashes the function arguments (SQL + parameters), so
  each filter combination is cached separately and expires after an hour.
- **Responsive layout.** `st.grid(4)` for KPI tiles and `st.grid(2, min_column_width=380)` for charts
  wrap to fewer columns on narrow screens.
- **Testing the UI.** `AppTest` runs a page script without a browser and exposes its elements
  (`at.metric`, `at.warning`, `at.exception`). The test also checks the tile labels match the
  requested dataset — otherwise a broken dataset picker could pass by showing the same dashboard 8 times.

### Bugs found while checking the running app
- **Legacy `pages/` folder:** after a cold start, opening a deep link like `/Dashboard` ran the page
  file directly (Streamlit's old auto-discovery), skipping `Home.py`: wrong layout and an extra "Home"
  menu item. Renaming the folder to `app_pages/` means only `st.navigation` decides the pages.
- **Stale imported module:** Streamlit reloads edited page scripts but not modules they import, so a
  new dataclass field caused `'Chart' object has no attribute 'label'` until the server restarted.
  Worth knowing when developing; not a production issue.

### Interview questions
1. **How did you avoid duplicating dashboard code for 8 datasets?**
   I separated *what* to show from *how* to show it: dashboard definitions are data in
   `dashboards.py`, and one renderer draws any definition. A test checks every definition is
   complete (4 KPIs, charts point to existing queries, filters are really used by the KPI SQL).
2. **What does `st.cache_data` cache, and when is it wrong to use it?**
   It stores the function's return value keyed by its arguments. It is right for read-only query
   results that may be an hour old. It is wrong for per-user secrets, data that must be live, or
   unhashable shared objects like database engines (use `st.cache_resource` for those).
3. **How do you test a Streamlit app?**
   Pure logic in normal unit tests; page behaviour with `streamlit.testing.v1.AppTest` (run the script,
   set session state or widget values, assert on the elements); and a manual check in a real browser
   for layout, which is how the `pages/` deep-link bug was found.

---

## Phase 4 — Text-to-SQL engine on all 8 datasets

### What was built
The engine modules were already dataset-agnostic (built earlier for 3 datasets). Phase 4 made them
work — and proved they work — on all 8:
- `knowledge/<dataset>/few_shots.yaml` for the 5 new datasets: 6 question → SQL pairs each, chosen to
  teach that schema's traps, plus 5 clickable example questions for the Ask page.
- Tests: every few-shot passes the guardrails and runs; an end-to-end test per dataset (fake LLM)
  checks prompt → guardrails → read-only run, and that the prompt contains *only* that dataset's tables.
- Guardrails now pretty-print the SQL they return (one clause per line) so the Ask page is readable.
- Loader fix found here: invisible zero-width spaces in Netflix titles (`\u200bSAINT SEIYA`) are removed
  for every dataset, so `WHERE title = '...'` can match.

### Key concepts
- **Prompt budget.** The prompt is schema + column comments + glossary + examples. Measured per dataset:
  700–1,900 tokens, even for 11 tables. Small enough that we send the whole schema; schema retrieval
  (picking only relevant tables) is only needed for much bigger databases (Phase 8).
- **Few-shot examples teach the traps, not the easy cases.** Olist examples always count people with
  `customer_unique_id`; Netflix examples join bridge tables instead of `LIKE '%India%'`; Chinook examples
  show the invoice_line → track → album → artist path and the employee self-join.
- **No leakage.** Few-shot questions must never appear in the benchmark, or few-shot accuracy would be
  inflated. A test enforces it once the benchmark exists.
- **Run exactly what you validated.** The guardrails parse the model's SQL into a tree, check the tree,
  and then run SQL *re-rendered from that tree* — not the model's original text. This avoids
  "parser differential" tricks where a validator and the database read the same text differently.
  Because the text changes (`x::int` → `CAST(x AS INT)`), I proved it never changes an answer: all 72
  analysis queries and 100 gold queries return identical results before and after the rewrite (now a test).
- **Testing the real client without paying for an API.** A 40-line fake OpenAI-compatible HTTP server
  (dev-only, not committed) let the Ask page run through the real `openai` SDK and HTTP path for all
  8 datasets. The provider registry made this a one-line config change (`OLLAMA_BASE_URL`).

### Interview questions
1. **How do you stop an LLM from running dangerous SQL?**
   Several layers: an AST check with sqlglot (one statement, SELECT only, no write nodes anywhere, only
   the chosen schema, no dangerous functions, LIMIT added); then a read-only database role, a READ ONLY
   transaction and a statement timeout. And I execute the SQL re-rendered from the validated tree.
2. **How would this scale to a database with 200 tables?**
   The whole schema would not fit or would confuse the model. Rank tables by how well their names,
   columns and comments match the question, send the top few plus their foreign-key neighbours, and keep
   the glossary and examples. That's schema retrieval (SPEC FR-25).
3. **How do you test an LLM feature without calling the LLM?**
   Make the model call a parameter (dependency injection). Unit tests pass a fake that returns scripted
   replies to cover success, self-correction, fallback and guardrail rejection. For an end-to-end UI
   check, point the real client at a local fake server that speaks the same API.

---

## Phase 5 — The benchmark (160 questions) and how to trust it

### What was built
- `eval/questions/<dataset>.jsonl`: 20 questions per dataset (6 easy, 9 medium, 5 hard), each with
  hand-written gold SQL. 60 kept from the first version, 100 new for the 5 new datasets.
- `eval/compare.py` (rewritten): execution accuracy with precision-aware numbers and tie-aware ordering.
- `eval/run_eval.py`: one model + prompt variant over all questions → a CSV per run, now including
  each dataset's number of tables.
- `eval/summarize.py`: combines the newest **complete** run per model × variant (partial smoke runs are
  skipped) into `summary.md`, including an "accuracy vs number of tables" table.
- `eval/sanity_check.py`: checks the benchmark itself (perfect model and negative control).
- Evaluation page: accuracy per model × prompt, a line chart of accuracy vs number of tables, and
  per-dataset and per-difficulty tables.

### Key concepts
- **Execution accuracy** compares *results*, not SQL text — there are many correct ways to write a query.
- **A benchmark can be unfair in both directions.** Too strict marks correct answers wrong; too lenient
  marks wrong answers right. Both were measured, not assumed:
  - *Perfect model*: answering every question with its own gold SQL through the whole pipeline must score
    100%. It found a gold query aliased `AS drop` — PostgreSQL accepts it but the guardrails' parser
    does not, so a model copying it would have been rejected.
  - *Negative control*: answering with a *different* question's gold SQL should score ~0%. It scored 0/160.
- **Precision-aware number matching.** "Round both to 2 decimals" marked `12.4637` wrong against a gold
  answer of `12.5` (gold rounded to 1 dp). Rounding the more precise value to the other's precision
  accepts harmless rounding differences while still rejecting real differences (12.4 vs 12.5) and keeping
  counts exact.
- **Ties.** Two kinds: (1) rows tied on the sort key inside an ordered answer — fixed in the comparator by
  checking only the order of the sort-key values; (2) a tie exactly at a `LIMIT` cut-off ("top 5" when
  #5 and #6 are equal) — two different answers are both right, so the *question* must change. An audit
  script found 4 such questions; they were changed to tie-free cut-offs.
- **No data leakage.** A test fails if any few-shot example also appears as a benchmark question.
- **Accuracy vs schema size** is the headline analysis: the 8 datasets go from 1 table to 11, so the
  results can show whether accuracy drops as schemas grow and how much the glossary/examples recover.

### Interview questions
1. **Why execution accuracy instead of exact SQL match?**
   `COUNT(*)` vs `COUNT(id)`, a JOIN vs a subquery, different aliases — all correct, all different text.
   Comparing results measures what the user cares about: the answer.
2. **How do you know your evaluation itself is correct?**
   A perfect model must score 100% (proves every question is answerable and the scorer isn't too strict),
   a negative control must score ~0% (proves it isn't too lenient), unit tests cover each comparison rule,
   and an audit checks questions for ties that would allow two valid answers.
3. **What is data leakage in an LLM benchmark, and how did you prevent it?**
   If a test question also appears in the prompt's examples, the model can copy the answer, inflating the
   score. The few-shot files and the benchmark are kept separate and a test enforces it.

---

## Phase 6 — Quality & CI

### What was built
- **CI reproduced locally before the first push.** A clean checkout of the latest commit, a brand-new
  virtual environment installed only from `requirements.txt`, an empty throwaway database and no `.env` —
  then exactly the CI steps (`ruff check .`, `python -m scripts.check_setup`, `pytest`). All green.
- **requirements.txt** now states the versions actually tested, with an upper limit for sqlglot.
- **Code audit** against the project's own rules: type hints and a docstring on every function, nothing
  over 50 lines. `answer_question` was split into its pipeline steps.
- **Benchmark runner made robust for free tiers:** saves after every question, resumes where it stopped,
  retries per-minute rate limits, and stops on a daily quota instead of recording errors as wrong answers.
- **Slow queries measured on a real install** and two more rewritten (same results, proven by the comparator).
- **Scope frozen** (recorded in SPEC 14): finish Phases 6 and 7; no UI rewrite; Phase 8 optional.

### Key concepts
- **Why reproduce CI locally?** The usual first-push failures are a dependency that exists on your laptop
  but not in `requirements.txt`, or a test that quietly needs a local file (`.env`, raw data). A clean
  checkout + fresh venv + empty database catches both. Remaining risk: GitHub runs Linux, this was Windows.
- **Version ranges.** A minimum version says "tested with at least this"; an upper bound protects code that
  depends on internals. The guardrails inspect sqlglot's syntax-tree classes, so a new major version must be
  re-tested before it can weaken a security check.
- **Measure before optimising, and verify after.** The window-function rewrite of the cohort query *looked*
  cleverer but was slower (1.6 s -> 2.0 s), so it was not used. Every kept rewrite was checked to return the
  identical result.
- **Don't change what you are measuring mid-experiment.** Materialising the IPL views would speed up queries but
  change the schema the LLM sees — so it waits until all benchmark runs are done.
- **Free-tier engineering.** Groq allows 200K tokens per model per day; one full run of a model uses more. The
  runner treats quota errors as "come back later", not as wrong answers, so the published accuracy is fair.
- **Is Streamlit the bottleneck?** Measured: a 4.2 s answer = 2.7 s LLM + 0.05 s database + fallback overhead.
  Rewriting the UI in another framework would not make answers faster.

### Interview questions
1. **How do you make sure CI will pass before you push?**
   Recreate CI's conditions: clean checkout, fresh environment from the requirements file only, an empty
   database, no local secrets, then run the same commands. It found nothing this time, which is the point —
   it proves the repo doesn't depend on my laptop.
2. **How did you handle API rate limits in a long benchmark?**
   Per-minute limits: wait and retry. Daily limits: stop that run, save progress, resume the next day in the
   same file. Errors are recorded separately from wrong answers so accuracy isn't distorted.
3. **Your app feels slow. How do you decide what to optimise?**
   Measure where the time goes first. Here the LLM call dominated; the database was 1% of the time. So the
   useful fixes are a faster model, streaming, or caching repeated questions — not rewriting the frontend.
