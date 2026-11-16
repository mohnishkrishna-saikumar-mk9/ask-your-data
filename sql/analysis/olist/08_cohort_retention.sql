-- Q: Cohort retention: of the customers whose first purchase was in a given month, what % bought again within 3 and 6 months?
-- Concepts: multiple CTEs, MIN() for first purchase, date_trunc, interval arithmetic, EXISTS-style conditional COUNT
-- Result: cohort_month | customers | returned_3m_pct | returned_6m_pct
WITH purchases AS (
    SELECT c.customer_unique_id, o.order_purchase_timestamp AS ts
    FROM olist.orders o
    JOIN olist.customers c ON c.customer_id = o.customer_id
),
firsts AS (
    SELECT customer_unique_id, MIN(ts) AS first_ts
    FROM purchases
    GROUP BY customer_unique_id
),
returns AS (
    SELECT f.customer_unique_id,
           date_trunc('month', f.first_ts)::date                                    AS cohort_month,
           BOOL_OR(p.ts > f.first_ts AND p.ts <= f.first_ts + INTERVAL '3 months')  AS back_3m,
           BOOL_OR(p.ts > f.first_ts AND p.ts <= f.first_ts + INTERVAL '6 months')  AS back_6m
    FROM firsts f
    JOIN purchases p ON p.customer_unique_id = f.customer_unique_id
    GROUP BY f.customer_unique_id, f.first_ts
)
SELECT cohort_month,
       COUNT(*)                                                         AS customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE back_3m) / COUNT(*), 2)     AS returned_3m_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE back_6m) / COUNT(*), 2)     AS returned_6m_pct
FROM returns
WHERE cohort_month BETWEEN DATE '2017-01-01' AND DATE '2018-02-01'
GROUP BY cohort_month
ORDER BY cohort_month;
