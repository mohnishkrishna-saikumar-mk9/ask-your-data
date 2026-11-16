# Data sources

All raw files live in `data/raw/<dataset>/` (gitignored — download them yourself from the links
below). Row counts are what the loaders actually loaded on 2026-11-16.

> **Licences:** only Chinook's licence has been checked against the file it ships with. For each
> Kaggle dataset, open the link and copy the licence shown on the page into the table before
> publishing the README.

| Schema | Source | Licence | Raw rows | Loaded |
|---|---|---|---|---|
| `placements` | [Kaggle: Factors affecting campus placement](https://www.kaggle.com/datasets/benroshan/factors-affecting-campus-placement) | to verify | 215 | 215 students |
| `netflix` | [Kaggle: Netflix Movies and TV Shows](https://www.kaggle.com/datasets/shivamb/netflix-shows) | to verify | 8,807 | 8,807 titles + 4 bridge tables (6,977 directors, 64,124 cast, 10,012 countries, 19,323 genres) |
| `startups` | [Kaggle: Indian Startup Funding](https://www.kaggle.com/datasets/sudalairajkumar/indian-startup-funding) | to verify | 3,044 | 3,044 rounds, 5,742 round–investor rows |
| `air_quality` | [Kaggle: Air Quality Data in India](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) | to verify | 230 / 29,531 / 108,035 | stations / city_daily / station_daily (hourly files not loaded) |
| `ecommerce` | [Kaggle: E-Commerce Sales Data](https://www.kaggle.com/datasets/thedevastator/unlock-profits-with-e-commerce-sales-data) | to verify | 128,975 / 37,432 / 9,271 | 120,378 orders, 128,975 order lines, 7,195 products, 18,635 international sales, 9,170 inventory SKUs |
| `ipl` | [Kaggle: IPL Complete Dataset 2008–2024](https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020) | to verify | 1,095 / 260,920 | 1,095 matches, 260,920 deliveries |
| `olist` | [Kaggle: Brazilian E-Commerce by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) | to verify | 9 files | 99,441 orders, 112,650 items, 103,886 payments, 99,224 reviews, 32,951 products, 3,095 sellers, 19,015 zip prefixes (from 1,000,163 geolocation rows) |
| `chinook` | [GitHub: lerocha/chinook-database](https://github.com/lerocha/chinook-database) v1.4.5 | MIT (from `LICENSE.md`) | SQL script | 11 tables, 412 invoices, 3,503 tracks |

---

## Cleaning decisions (every one is printed in the loader's report)

### All datasets
- Files are read as text first; each column is converted on purpose (no pandas type guessing).
- Headers: UTF-8 BOM and surrounding spaces removed (`'﻿Sr No'`, `'Sales Channel '`).
- `''`, `NA`, `N/A`, `nan`, `None`, `null` → NULL. `Unnamed: N` index columns dropped.
- Each load runs in one transaction: drop tables → create → COPY → ANALYZE. A failure rolls back.

### placements
- Short codes renamed (`ssc_p` → `ssc_percent`, `etest_p` → `employability_test_percent` …).
- `workex` Yes/No and `status` Placed/Not Placed → booleans; salary NULL when not placed.

### netflix
- 3 rows had the duration (`74 min`) in `rating` and an empty `duration`: moved and rating set NULL.
- `duration` split into `duration_minutes` (movies) and `seasons` (TV shows).
- `director`, `cast`, `country`, `listed_in` split on commas into 4 bridge tables; items trimmed,
  blanks and repeats removed.
- Some descriptions contain `�` replacement characters from the source file; kept as published.

### startups
- Escape sequences are written **as literal text** in the file (`\\xc2\\xa0N/A`, `Seed\\nFunding`),
  not as real characters; removed with a regex in every text column.
- Dates parsed with a tolerant dd/mm/yyyy parser: `12/05.2015`, `13/04.2015`, `15/01.2015`,
  `22/01//2015`, `01/07/015` (→ 2015), `05/072018` (missing slash). All 3,044 dates parsed.
- Amounts use Indian digit grouping (`20,00,00,000` = 200,000,000); commas and a trailing `+`
  stripped; `N/A` / `undisclosed` / `unknown` → NULL (971 rounds).
- **Known source error:** round 61 (Rapido, Aug 2019, Series B) is `3,90,00,00,000` — ₹390 crore
  entered as USD, ~70× too large. Set to NULL rather than guessing an exchange rate.
- Investment types merged (e.g. `Seed Funding`, `Seed/ Angel Funding`, `Angel` → `Seed / Angel`;
  `PrivateEquity` → `Private Equity`; `Debt-Funding` → `Debt Funding`).
- Cities: first city kept (`Pune / US` → `Pune`); `Bangalore` → `Bengaluru`, `Gurgaon` → `Gurugram`,
  `New Delhi` → `Delhi`.
- Startup names merged for Ola, OYO, Paytm, Flipkart, Rapido.
- `Investors Name` split on commas into `round_investors`.

### air_quality
- Pollutant columns renamed (`PM2.5` → `pm25` …); missing readings stay NULL (averages ignore them).
- `city_hour.csv` (66 MB) and `station_hour.csv` (220 MB) are **not loaded**.
- Ahmedabad shows the highest average AQI (≈452) because of unusually high CO readings in the source.
  This is a known quirk of the dataset, kept as published.

### ecommerce
- Amazon report split into `products`, `orders`, `order_items`; states mapped from 69 spellings to 36
  (28 states + 8 union territories); `promotion-ids` → `has_promotion`.
- `International sale Report.csv` has three parts: block A (18,635 well-formed rows), block B (17,756
  rows — the **same sales pasted again one column to the right**; 100% of block A's rows in B's date
  range appear in B) and 1,041 stock-list rows. Only block A is loaded; loading B would roughly double
  international revenue.
- `Sale Report.csv` → `inventory`: 83 blank SKUs dropped, 18 duplicated SKU codes keep their first row,
  categories tidied (`AN : LEGGINGS` → `Leggings`).
- Ignored on purpose: `Cloud Warehouse Compersion Chart.csv`, `Expense IIGF.csv`, `May-2022.csv`,
  `P  L March 2021.csv` (messy layouts, low value).

### ipl
- Season from the match date (raw `2007/08` is ambiguous); renamed franchises merged (Deccan Chargers and
  Sunrisers Hyderabad kept separate); 58 venue spellings → 36 venues.
- Overs are 0-based → `phase` = powerplay (0–5), middle (6–14), death (15–19).
- Innings 3–6 are super overs and are excluded from the `batting_innings` / `bowling_innings` views.

### olist
- Misspelt `product_name_lenght` / `product_description_lenght` renamed to `…_length`.
- English category added from the translation file; 2 missing translations added by hand
  (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` → `portable_kitchen_and_food_preparers`).
- `review_id` is not unique in the source, so `reviews` uses a surrogate key.
- Geolocation (1,000,163 rows, many per prefix) aggregated to one row per zip prefix
  (mean lat/lng, most common city/state). Zip prefixes stay text to keep leading zeros.

### chinook
- The official script creates its own database. The loader strips exactly the three database-level
  lines (`DROP DATABASE`, `CREATE DATABASE`, psql's `\c`) and runs the rest with
  `search_path = chinook`. It drops the 11 tables (not the schema) so the read-only role's default
  privileges survive a reload. `COMMENT ON` for every table and column is added from
  `sql/schema/chinook.sql`.

---

## Sanity checks against known facts
- IPL: CSK and MI 5 titles each, KKR 3; V Kohli 8,004 runs; Purple Cap winners 2020–2024 match records.
- Startups: top funded = Flipkart, Paytm, Ola, OYO (after the Rapido fix).
- Olist: total GMV ≈ R$13.6M; top category health_beauty.
- Chinook: 412 invoices, total revenue $2,328.60.
- Air quality: Delhi yearly mean PM2.5 drops to 80 in 2020 (lockdown year).
