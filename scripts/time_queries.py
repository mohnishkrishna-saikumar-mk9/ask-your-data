"""Time every analysis query (NFR-2 target: < 500 ms each).

Run from the project root:  python -m scripts.time_queries
"""
import time

from src.config import DATASETS
from src.db import run_query
from src.sql_library import list_queries

TARGET_MS = 500


def main() -> None:
    """Time every analysis query and report the ones over the target."""
    slow = 0
    for dataset in DATASETS:
        for q in list_queries(dataset):
            run_query(q.sql, schema=dataset)  # warm-up (caches)
            start = time.perf_counter()
            df = run_query(q.sql, schema=dataset)
            ms = (time.perf_counter() - start) * 1000
            flag = "SLOW" if ms > TARGET_MS else "ok"
            slow += ms > TARGET_MS
            print(f"{flag:4} {ms:7.1f} ms  {len(df):5} rows  {dataset}/{q.path.name}")
    print(f"\n{slow} queries slower than {TARGET_MS} ms")


if __name__ == "__main__":
    main()
