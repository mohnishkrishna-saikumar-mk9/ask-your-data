-- Q: How do business (B2B) orders compare with consumer (B2C) orders?
-- Concepts: CASE label, JOIN, multiple aggregates, AOV, average quantity
-- Result: segment | orders | revenue | aov | avg_qty_per_line
SELECT CASE WHEN o.is_b2b THEN 'B2B' ELSE 'B2C' END                    AS segment,
       COUNT(DISTINCT o.order_id)                                       AS orders,
       SUM(i.amount)                                                    AS revenue,
       ROUND(SUM(i.amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2)  AS aov,
       ROUND(AVG(i.qty), 2)                                             AS avg_qty_per_line
FROM ecommerce.orders o
JOIN ecommerce.order_items i ON i.order_id = o.order_id
WHERE o.status NOT LIKE 'Cancelled%'
GROUP BY 1
ORDER BY segment;
