-- Q: Which product categories drive GMV, and what is their running share of the total (Pareto)?
-- Concepts: CTE, 3-table JOIN, COALESCE, running SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING)
-- Result: category | gmv | share_pct | running_share_pct  (top 15)
WITH cat AS (
    SELECT COALESCE(p.category_english, 'unknown') AS category, SUM(i.price) AS gmv
    FROM olist.order_items i
    JOIN olist.products p ON p.product_id = i.product_id
    GROUP BY 1
)
SELECT category, gmv,
       ROUND(100.0 * gmv / SUM(gmv) OVER (), 2)                                   AS share_pct,
       ROUND(100.0 * SUM(gmv) OVER (ORDER BY gmv DESC ROWS UNBOUNDED PRECEDING)
             / SUM(gmv) OVER (), 2)                                               AS running_share_pct
FROM cat
ORDER BY gmv DESC
LIMIT 15;
