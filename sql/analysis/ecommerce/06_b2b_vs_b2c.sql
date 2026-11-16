-- Q: How do business (B2B) orders compare with consumer (B2C) orders?
-- Concepts: aggregate-before-join CTE, CASE label, multiple aggregates, AOV, weighted average
-- Result: segment | orders | revenue | aov | avg_qty_per_line
WITH order_totals AS (
    SELECT order_id, SUM(amount) AS order_value, SUM(qty) AS units, COUNT(*) AS lines
    FROM ecommerce.order_items
    GROUP BY order_id
)
SELECT CASE WHEN o.is_b2b THEN 'B2B' ELSE 'B2C' END              AS segment,
       COUNT(*)                                                  AS orders,
       SUM(t.order_value)                                        AS revenue,
       ROUND(SUM(t.order_value) / NULLIF(COUNT(*), 0), 2)        AS aov,
       ROUND(SUM(t.units)::numeric / SUM(t.lines), 2)            AS avg_qty_per_line
FROM ecommerce.orders o
JOIN order_totals t ON t.order_id = o.order_id
WHERE o.status NOT LIKE 'Cancelled%'
GROUP BY 1
ORDER BY segment;
