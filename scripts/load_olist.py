"""Load the Olist Brazilian marketplace into the `olist` schema (8 tables).

Run from the project root:  python -m scripts.load_olist
Expects the 9 CSVs of Kaggle "Brazilian E-Commerce Public Dataset by Olist" in data/raw/olist/.
"""
from pathlib import Path

import pandas as pd

from scripts._loader_utils import RAW_DIR, load_tables, null_report, read_csv

# Two categories are missing from the official translation file.
EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_preparers",
}
ORDER_TIMESTAMPS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                    "order_delivered_customer_date", "order_estimated_delivery_date"]


def read(raw_dir: Path, name: str) -> pd.DataFrame:
    """Read olist_<name>_dataset.csv."""
    return read_csv(raw_dir / f"olist_{name}_dataset.csv")


def to_timestamps(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Convert text columns like '2017-10-02 10:56:33' to timestamps."""
    for col in cols:
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d %H:%M:%S")
    return df


def clean_customers(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop the 'customer_' prefix from column names."""
    return raw.rename(columns={"customer_zip_code_prefix": "zip_code_prefix",
                               "customer_city": "city", "customer_state": "state"})


def clean_sellers(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop the 'seller_' prefix from column names."""
    return raw.rename(columns={"seller_zip_code_prefix": "zip_code_prefix",
                               "seller_city": "city", "seller_state": "state"})


def clean_products(raw: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    """Fix the misspelt 'lenght' columns, drop the 'product_' prefix, add English category."""
    df = raw.rename(columns=lambda c: c.replace("lenght", "length").removeprefix("product_"))
    df = df.rename(columns={"id": "product_id", "category_name": "category"})
    english = dict(zip(translation["product_category_name"],
                       translation["product_category_name_english"], strict=True))
    df["category_english"] = df["category"].map(lambda c: english.get(c, EXTRA_TRANSLATIONS.get(c)))
    numeric = ["name_length", "description_length", "photos_qty", "weight_g", "length_cm",
               "height_cm", "width_cm"]
    df[numeric] = df[numeric].apply(pd.to_numeric).astype("Int64")
    return df[["product_id", "category", "category_english", *numeric]]


def build_zip_locations(geo: pd.DataFrame) -> pd.DataFrame:
    """1M geolocation rows -> one row per zip prefix (mean lat/lng, most common city/state)."""
    geo = geo.rename(columns=lambda c: c.removeprefix("geolocation_"))
    geo["lat"] = pd.to_numeric(geo["lat"])
    geo["lng"] = pd.to_numeric(geo["lng"])
    coords = geo.groupby("zip_code_prefix")[["lat", "lng"]].mean()
    place = (geo.groupby(["zip_code_prefix", "city", "state"]).size().rename("n").reset_index()
             .sort_values("n", ascending=False).drop_duplicates("zip_code_prefix")
             .set_index("zip_code_prefix")[["city", "state"]])
    return coords.join(place).reset_index()


def main(raw_dir: Path = RAW_DIR / "olist") -> None:
    """Read, clean and load the 9 Olist files into 8 tables."""
    print("Loading Olist ...")
    customers = clean_customers(read(raw_dir, "customers"))
    sellers = clean_sellers(read(raw_dir, "sellers"))
    products = clean_products(read(raw_dir, "products"),
                              read_csv(raw_dir / "product_category_name_translation.csv"))
    orders = to_timestamps(read(raw_dir, "orders"), ORDER_TIMESTAMPS)
    items = to_timestamps(read(raw_dir, "order_items"), ["shipping_limit_date"])
    payments = read(raw_dir, "order_payments")
    reviews = to_timestamps(read(raw_dir, "order_reviews"),
                            ["review_creation_date", "review_answer_timestamp"])
    raw_geo = read(raw_dir, "geolocation")
    zips = build_zip_locations(raw_geo)

    print(f"  zip_locations: aggregated {len(raw_geo):,} geolocation rows into "
          f"{len(zips):,} zip prefixes")
    missing = products.loc[products["category"].notna() & products["category_english"].isna(),
                           "category"].unique()
    print(f"    [category] untranslated categories: {list(missing)}")
    null_report(orders, "orders")
    load_tables("olist.sql", [
        ("olist.customers", customers), ("olist.sellers", sellers), ("olist.products", products),
        ("olist.orders", orders), ("olist.order_items", items), ("olist.payments", payments),
        ("olist.reviews", reviews), ("olist.zip_locations", zips),
    ])


if __name__ == "__main__":
    main()
