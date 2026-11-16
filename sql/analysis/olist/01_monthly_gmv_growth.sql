-- Q: What is the monthly GMV (gross merchandise value) and its month-over-month growth?
-- Concepts: CTE, date_trunc, INNER JOIN, LAG() window function, percentage change, NULLIF
-- Result: month | orders | gmv | prev_gmv | mom_growth_pct
-- Note: limited to Jan 2017 - Aug 2018. Before that there are only a handful of test orders
--       (growth of +1,000,000% is meaningless) and Sep-Oct 2018 are incomplete months.
WITH monthly AS (
    SELECT date_trunc('month', o.order_purchase_timestamp)::date AS month,
           COUNT(DISTINCT o.order_id)                            AS orders,
           SUM(i.price)                                          AS gmv
    FROM olist.orders o
    JOIN olist.order_items i ON i.order_id = o.order_id
    WHERE o.order_purchase_timestamp >= TIMESTAMP '2017-01-01'
      AND o.order_purchase_timestamp <  TIMESTAMP '2018-09-01'
    GROUP BY 1
)
SELECT month, orders, gmv,
       LAG(gmv) OVER (ORDER BY month)                                     AS prev_gmv,
       ROUND(100.0 * (gmv - LAG(gmv) OVER (ORDER BY month))
             / NULLIF(LAG(gmv) OVER (ORDER BY month), 0), 1)             AS mom_growth_pct
FROM monthly
ORDER BY month;
