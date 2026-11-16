-- Q: Which 10 startups raised the most disclosed funding in total?
-- Concepts: GROUP BY, SUM ignoring NULLs, COUNT, MIN/MAX dates, ORDER BY + LIMIT
-- Result: startup_name | rounds | total_usd_mn | first_round | last_round
SELECT startup_name,
       COUNT(*)                          AS rounds,
       ROUND(SUM(amount_usd) / 1e6, 1)   AS total_usd_mn,
       MIN(funding_date)                 AS first_round,
       MAX(funding_date)                 AS last_round
FROM startups.funding_rounds
GROUP BY startup_name
HAVING SUM(amount_usd) IS NOT NULL
ORDER BY total_usd_mn DESC
LIMIT 10;
