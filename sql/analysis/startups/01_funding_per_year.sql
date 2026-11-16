-- Q: How much disclosed funding was raised each year, and how did it change from the previous year?
-- Concepts: EXTRACT(YEAR ...), CTE, COUNT FILTER, LAG() for year-over-year change
-- Result: year | rounds | disclosed_rounds | total_usd_mn | yoy_change_pct
WITH yearly AS (
    SELECT EXTRACT(YEAR FROM funding_date)::int              AS year,
           COUNT(*)                                          AS rounds,
           COUNT(*) FILTER (WHERE amount_usd IS NOT NULL)    AS disclosed_rounds,
           ROUND(SUM(amount_usd) / 1e6, 1)                   AS total_usd_mn
    FROM startups.funding_rounds
    WHERE funding_date IS NOT NULL
    GROUP BY 1
)
SELECT year, rounds, disclosed_rounds, total_usd_mn,
       ROUND(100.0 * (total_usd_mn - LAG(total_usd_mn) OVER (ORDER BY year))
             / NULLIF(LAG(total_usd_mn) OVER (ORDER BY year), 0), 1) AS yoy_change_pct
FROM yearly
ORDER BY year;
