"""Load the Amazon India sales report into the `ecommerce` schema.

Run from the project root:  python -m scripts.load_ecommerce
Expects data/raw/ecommerce/Amazon Sale Report.csv (Kaggle "E-Commerce Sales Dataset").
"""
import re
from pathlib import Path

import pandas as pd

from scripts._loader_utils import RAW_DIR, load_tables, null_report, read_csv, to_bool
from src.db import run_query

CSV_NAME = "Amazon Sale Report.csv"

# Known spelling variants / abbreviations, keyed by UPPER-CASE raw value.
STATE_FIXES = {
    "PONDICHERRY": "Puducherry",
    "RJ": "Rajasthan",
    "RAJSHTHAN": "Rajasthan",
    "RAJSTHAN": "Rajasthan",
    "NEW DELHI": "Delhi",
    "ORISSA": "Odisha",
    "PB": "Punjab",
    "PUNJAB/MOHALI/ZIRAKPUR": "Punjab",
    "AR": "Arunachal Pradesh",
    "NL": "Nagaland",
    "APO": None,  # army post office - not a state
}
CITY_FIXES = {"NEW DELHI": "Delhi", "BANGALORE": "Bengaluru", "GURGAON": "Gurugram"}

ORDER_COLS = ["order_id", "order_date", "status", "fulfilment", "sales_channel",
              "ship_service_level", "ship_city", "ship_state", "ship_postal_code",
              "is_b2b", "has_promotion"]
PRODUCT_COLS = ["sku", "style", "category", "size", "asin"]
ITEM_COLS = ["order_id", "sku", "qty", "amount", "currency", "courier_status", "amount_missing"]


def snake_case(name: str) -> str:
    """'Order ID' -> 'order_id', 'ship-service-level' -> 'ship_service_level'."""
    return re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_")


def clean_place(value: str | None, fixes: dict[str, str | None]) -> str | None:
    """Trim, Title Case, and map known variants."""
    if value is None:
        return None
    key = value.strip().upper()
    if key in fixes:
        return fixes[key]
    return value.strip().title()


def clean_sales(raw: pd.DataFrame) -> pd.DataFrame:
    """One cleaned row per raw line, with snake_case columns and proper types."""
    df = raw.rename(columns=snake_case)
    df = df.drop(columns=[c for c in df.columns if c.startswith("unnamed")], errors="ignore")
    df["order_date"] = pd.to_datetime(df["date"], format="%m-%d-%y").dt.date
    df["qty"] = pd.to_numeric(df["qty"]).fillna(0).astype(int)
    df["amount"] = pd.to_numeric(df["amount"])
    df["amount_missing"] = df["amount"].isna()
    df["is_b2b"] = to_bool(df["b2b"], {"True", "1", "Y"})
    df["has_promotion"] = df["promotion_ids"].notna()
    df["ship_postal_code"] = df["ship_postal_code"].map(
        lambda v: None if v is None else str(v).split(".")[0])
    before = df["ship_state"].dropna().str.strip().str.title()
    df["ship_state"] = df["ship_state"].map(lambda v: clean_place(v, STATE_FIXES))
    df["ship_city"] = df["ship_city"].map(lambda v: clean_place(v, CITY_FIXES))
    changed = (before != df["ship_state"].loc[before.index]).sum()
    print(f"    [state] mapped {changed} rows; {df['ship_state'].nunique()} distinct states")
    return df


def split_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Normalise the flat report into products, orders and order_items."""
    products = df[PRODUCT_COLS].drop_duplicates("sku")
    orders = df[ORDER_COLS].drop_duplicates("order_id")
    items = df[ITEM_COLS]
    return products, orders, items


def main(raw_dir: Path = RAW_DIR / "ecommerce") -> None:
    print("Loading e-commerce ...")
    df = clean_sales(read_csv(raw_dir / CSV_NAME))
    products, orders, items = split_tables(df)
    null_report(orders, "orders")
    null_report(items, "order_items")
    load_tables("ecommerce.sql", [("ecommerce.products", products),
                                  ("ecommerce.orders", orders),
                                  ("ecommerce.order_items", items)])
    months = run_query("SELECT date_trunc('month', order_date)::date AS m, COUNT(*) AS n "
                       "FROM ecommerce.orders GROUP BY 1 ORDER BY 1")
    print("  Orders per month:", dict(zip(months.m.astype(str), months.n, strict=True)))


if __name__ == "__main__":
    main()
