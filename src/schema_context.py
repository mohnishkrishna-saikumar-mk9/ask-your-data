"""Builds the SCHEMA section of the prompt from information_schema + COMMENT ON (FR-9)."""
from functools import lru_cache

import pandas as pd

from src.db import run_query

COLUMNS_SQL = """
SELECT c.table_name,
       t.table_type,
       c.column_name,
       c.data_type,
       obj_description(format('%I.%I', c.table_schema, c.table_name)::regclass) AS table_comment,
       col_description(format('%I.%I', c.table_schema, c.table_name)::regclass,
                       c.ordinal_position) AS column_comment
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = :schema
ORDER BY t.table_type, c.table_name, c.ordinal_position
"""


def format_schema(schema: str, columns: pd.DataFrame) -> str:
    """Turn column metadata rows into compact text, one block per table/view."""
    blocks = []
    for table, cols in columns.groupby("table_name", sort=False):
        kind = "VIEW" if cols["table_type"].iloc[0] == "VIEW" else "TABLE"
        header = f"{kind} {schema}.{table}"
        if cols["table_comment"].iloc[0]:
            header += f"  -- {cols['table_comment'].iloc[0]}"
        lines = [header]
        for _, c in cols.iterrows():
            comment = f"  -- {c['column_comment']}" if c["column_comment"] else ""
            lines.append(f"    {c['column_name']} {c['data_type'].upper()}{comment}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


@lru_cache(maxsize=8)
def get_schema_context(schema: str) -> str:
    """Schema text for a dataset, cached because it only changes when data is reloaded."""
    return format_schema(schema, run_query(COLUMNS_SQL, {"schema": schema}))
