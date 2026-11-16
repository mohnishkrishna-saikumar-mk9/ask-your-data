-- Q: Do orders with a promotion have a higher or lower average order value?
-- Concepts: CTE computing per-order totals, then AVG over orders, GROUP BY boolean
-- Result: has_promotion | orders | aov | median_order_value
WITH order_totals AS (
    SELECT o.order_id, o.has_promotion, SUM(i.amount) AS order_value
    FROM ecommerce.orders o
    JOIN ecommerce.order_items i ON i.order_id = o.order_id
    WHERE o.status NOT LIKE 'Cancelled%'
    GROUP BY o.order_id, o.has_promotion
)
SELECT has_promotion,
       COUNT(*)                                                     AS orders,
       ROUND(AVG(order_value), 2)                                   AS aov,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_value)     AS median_order_value
FROM order_totals
GROUP BY has_promotion
ORDER BY has_promotion;
