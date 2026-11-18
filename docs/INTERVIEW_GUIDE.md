# Interview guide — Ask Your Data

One page to explain the project simply. Deeper detail for each part: [LEARNING_NOTES.md](LEARNING_NOTES.md).

## The 30-second pitch

> "I built an app where you ask a question in plain English and get the answer from a SQL database.
> An LLM writes the SQL from the database's own column descriptions, a safety layer checks that the SQL
> is read-only before it runs, and the result is shown as a table and a chart. I tested it on 8 real
> datasets with a 160-question benchmark I wrote, and measured how accuracy changes with the size of the
> database and with what I put in the prompt."

## How it works — 5 steps

1. **Question** — the user picks a dataset and types a question.
2. **Prompt** — built from the database itself: table and column descriptions (`COMMENT ON`), plus a short
   glossary of business definitions and a few example question → SQL pairs.
3. **LLM** — writes one SQL query (any OpenAI-compatible provider; I used Groq and Gemini).
4. **Safety check** — the SQL is parsed into a syntax tree (sqlglot): it must be a single `SELECT`, only on
   the chosen dataset, with no write commands anywhere. It then runs read-only, with a 10 s timeout and a
   row limit. If the database returns an error, the error goes back to the model once to fix it.
5. **Answer** — a results table and an automatically chosen chart, plus the SQL so the user can check it.

## Numbers you can say

| | |
|---|---|
| Datasets | 8 real datasets, from 1 table to 11 tables (IPL 260K deliveries, Olist 99K orders, ...) |
| Hand-written SQL | 72 analysis queries: joins, CTEs, window functions, recursive CTE, cohorts |
| Benchmark | 160 questions with gold SQL, 20 per dataset, easy / medium / hard |
| Result so far | qwen3.8-27b, schema only: **78%** execution accuracy (125/160) |
| Tests | 860+ automated tests; the LLM is always mocked in tests |

## Key decisions — and why

- **One PostgreSQL schema per dataset** — the model only ever sees the schema it is asked about.
- **Column comments are the data dictionary** — improving a comment improves answers without code changes.
- **Safety in layers, not one check** — syntax-tree check, read-only transaction, read-only database user,
  timeout. If one layer has a bug, the others still protect the data.
- **Execution accuracy** — compare result rows, not SQL text: many different queries are correct.
- **OpenAI-compatible API** — switching provider is a config change (`provider:model` in `.env`).

## Three stories that show judgement

1. **Data cleaning found real problems in the source data.** Half of one sales file was the same sales
   pasted twice in shifted columns — loading it would have doubled revenue. One startup's ₹390 crore was
   recorded as US dollars (70x too big). I proved each issue before fixing it and logged every decision.
2. **Safety: run exactly what you checked.** The query that runs is re-built from the checked syntax tree,
   not the model's raw text, so the checker and the database can't read the text differently. I proved
   this never changes an answer on 172 queries.
3. **Making the benchmark fair.** A "perfect model" must score 100% and a deliberately wrong one ~0%. Real
   model answers then showed my scorer marked some correct answers wrong (order or extra columns the
   question never asked for) — I fixed the rules and re-scored. Provider errors (quota, network) are
   never counted as wrong answers.

## AI system design vocabulary — mapped to this project

Interviewers use these standard terms. Each one below is something this project actually does, so
you can answer with your own code as the example.

| Term | What it means | Where it is here |
|---|---|---|
| **Context engineering** | choosing what goes into the prompt | schema + `COMMENT ON` descriptions + glossary + examples, built from the database (`src/schema_context.py`, `src/llm/prompts.py`) |
| **Guardrails / output validation** | never trust model output; check it before acting | sqlglot syntax-tree check (`src/guardrails.py`); the SQL that runs is re-built from the checked tree |
| **Prompt injection defence** | a user or model tries to make the system do something unsafe | the checker refuses anything but one `SELECT`, whatever the prompt said; tested in `tests/test_guardrails.py` |
| **Defence in depth** | several independent safety layers | syntax check + read-only transaction + read-only DB user + timeout + row cap (`src/db.py`) |
| **Self-correction loop** | feed the error back so the model can fix it | one retry with the database error appended (`src/text_to_sql.py`) |
| **Fallback model** | if one model fails, try another | `LLM_FALLBACK_MODEL`; models are tried in order (`_models_to_try`) |
| **Timeouts** | never wait forever on a model or a query | LLM timeout `LLM_TIMEOUT_S`; database `statement_timeout` 10 s |
| **Retries with backoff** | wait longer after each failure | benchmark runner waits 30 → 60 → 120 s on rate limits and outages (`eval/run_eval.py`) |
| **Rate limits (TPM / per-day)** | providers cap tokens per minute and per day | daily-quota stop + resume next day; per-visitor question limit on the public demo (`DEMO_MAX_QUESTIONS`) |
| **Graceful degradation** | fail clearly instead of producing wrong results | a provider outage stops the benchmark with progress saved, instead of recording errors as wrong answers |
| **Caching** | don't pay twice for the same answer | exact-match cache of (dataset, question, model, prompt) → SQL, on disk (`src/cache.py`); rows are always re-queried, so data is fresh |
| **Model routing / AI gateway** | one interface in front of many providers | `provider:model_id` in `.env`; every provider speaks the OpenAI API (`src/llm/providers.py`); works through the OmniRoute gateway |
| **Evaluation pipeline** | measure quality with a fixed test set, not by feel | 160 questions, execution accuracy, perfect-model 100% and negative-control 0% checks (`eval/`) |
| **Prompt variants / ablation** | change one thing in the prompt and measure the effect | 3 prompt styles: schema only, + examples, + examples and glossary |

**What I would add at scale (say these as ideas, not as features):**
- **Observability**: log every question, the SQL, latency, tokens and errors, with a dashboard of failures.
- **Semantic cache**: reuse answers for questions that *mean* the same thing, not only identical text.
- **Schema retrieval** for very large databases: pick only the relevant tables before building the prompt
  (my largest database has 11 tables, which still fits in one prompt; real company databases can have hundreds).
- **LLM-as-a-judge** for questions where the exact result is not the only correct answer.

## Likely questions — short answers

- **How do you stop the LLM from deleting data?** Several layers: the syntax-tree check only allows one
  `SELECT`; the database transaction is read-only; the app's database user can only read; plus a timeout.
- **Why not just use LangChain?** The whole engine is six small files (~460 lines, the main flow ~140) that
  I can explain line by line; a framework would hide the parts I wanted to learn and test.
- **How do you know the answers are right?** The 160-question benchmark compares results with hand-written
  gold SQL, and the benchmark itself is checked (perfect model 100%, wrong model 0%).
- **What was hardest?** Messy real data, and making the evaluation fair — both needed checking assumptions
  against the real data instead of trusting the first result.
- **What would you improve?** Run the benchmark on more models (free API quotas limited me), and pick only
  the relevant tables for very large databases.

## 2-minute demo

1. Ask page → IPL → "Which team has won the most IPL titles?" → open *Generated SQL* → show the chart.
2. Open `tests/test_guardrails.py` → show attacks like `SELECT 1; DROP TABLE ...` and `pg_sleep(10)` that the
   safety layer refuses (the model itself usually won't write them, so the tests are the reliable demo).
3. Dashboard → switch dataset → move the season slider.
4. Evaluation page → accuracy by dataset and by number of tables.
