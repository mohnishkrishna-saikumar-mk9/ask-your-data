-- Q: How did the mix of round types (Seed / Angel, Private Equity, Series A ...) change by year?
-- Concepts: CASE to group rare types into 'Other', GROUP BY two columns, share within year via window SUM
-- Result: year | round_type | rounds | share_of_year_pct
WITH typed AS (
    SELECT EXTRACT(YEAR FROM funding_date)::int AS year,
           CASE WHEN investment_type IN ('Seed / Angel', 'Private Equity') THEN investment_type
                WHEN investment_type ILIKE 'series%' OR investment_type ILIKE 'pre-series%' THEN 'Series rounds'
                ELSE 'Other' END                AS round_type
    FROM startups.funding_rounds
    WHERE funding_date IS NOT NULL
)
SELECT year, round_type,
       COUNT(*)                                                                 AS rounds,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY year), 1)      AS share_of_year_pct
FROM typed
GROUP BY year, round_type
ORDER BY year, rounds DESC;
