-- Q: For the top 5 cities by funding, which industry vertical raised the most in each?
-- Concepts: multiple CTEs, ROW_NUMBER() OVER (PARTITION BY city), share within group
-- Result: city | city_total_usd_mn | top_industry | industry_usd_mn | share_pct
WITH city_industry AS (
    SELECT city, COALESCE(industry_vertical, 'Unknown') AS industry, SUM(amount_usd) AS usd
    FROM startups.funding_rounds
    WHERE city IS NOT NULL AND amount_usd IS NOT NULL
    GROUP BY city, COALESCE(industry_vertical, 'Unknown')
),
ranked AS (
    SELECT city, industry, usd,
           SUM(usd) OVER (PARTITION BY city)                         AS city_total,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY usd DESC)   AS rn
    FROM city_industry
)
SELECT city,
       ROUND(city_total / 1e6, 1)               AS city_total_usd_mn,
       industry                                 AS top_industry,
       ROUND(usd / 1e6, 1)                      AS industry_usd_mn,
       ROUND(100.0 * usd / city_total, 1)       AS share_pct
FROM ranked
WHERE rn = 1
ORDER BY city_total DESC
LIMIT 5;
