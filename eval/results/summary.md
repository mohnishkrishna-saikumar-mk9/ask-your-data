# Benchmark results

Execution accuracy on the 160-question benchmark (8 datasets).

| Model | Prompt | placements | netflix | startups | air_quality | ecommerce | ipl | olist | chinook | all | p50 latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| groq:qwen/qwen3.8-27b | full | 95% | 90% | 60% | 90% | 90% | 80% | 100% | 80% | 86% | 12.07 s |
| groq:qwen/qwen3.8-27b | few_shot | 95% | 80% | 60% | 90% | 85% | 75% | 100% | 80% | 83% | 9.94 s |
| groq:qwen/qwen3.8-27b | zero_shot | 75% | 80% | 85% | 90% | 75% | 65% | 85% | 70% | 78% | 4.92 s |

## Accuracy vs number of tables

| Tables | Dataset | groq:qwen/qwen3.8-27b · few_shot | groq:qwen/qwen3.8-27b · full | groq:qwen/qwen3.8-27b · zero_shot |
|---|---|---|---|---|
| 1 | placements | 95% | 95% | 75% |
| 2 | ipl | 75% | 80% | 65% |
| 2 | startups | 60% | 60% | 85% |
| 3 | air_quality | 90% | 90% | 90% |
| 5 | ecommerce | 85% | 90% | 75% |
| 5 | netflix | 80% | 90% | 80% |
| 8 | olist | 100% | 100% | 85% |
| 11 | chinook | 80% | 80% | 70% |
