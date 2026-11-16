-- Q: What was the single largest disclosed round in each year?
-- Concepts: CTE, ROW_NUMBER() OVER (PARTITION BY year ORDER BY amount DESC), keep rn = 1
-- Result: year | startup_name | investment_type | amount_usd_mn | funding_date
WITH ranked AS (
    SELECT EXTRACT(YEAR FROM funding_date)::int AS year, startup_name, investment_type,
           amount_usd, funding_date,
           ROW_NUMBER() OVER (PARTITION BY EXTRACT(YEAR FROM funding_date)
                              ORDER BY amount_usd DESC) AS rn
    FROM startups.funding_rounds
    WHERE amount_usd IS NOT NULL AND funding_date IS NOT NULL
)
SELECT year, startup_name, investment_type,
       ROUND(amount_usd / 1e6, 1) AS amount_usd_mn, funding_date
FROM ranked
WHERE rn = 1
ORDER BY year;
