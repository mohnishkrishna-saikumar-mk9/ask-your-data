-- Q: Which product categories have the highest order cancellation rate?
-- Concepts: DISTINCT pairs in a CTE (de-duplicate once), JOIN, COUNT FILTER, conditional ratio
-- Result: category | orders | cancelled_orders | cancellation_rate_pct
-- Note: an order can contain several categories, so (order, category) pairs are de-duplicated
--       first; then plain COUNT(*) replaces three slower COUNT(DISTINCT ...) calls.
WITH order_categories AS (
    SELECT DISTINCT i.order_id, p.category
    FROM ecommerce.order_items i
    JOIN ecommerce.products p ON p.sku = i.sku
)
SELECT oc.category,
       COUNT(*)                                                    AS orders,
       COUNT(*) FILTER (WHERE o.status LIKE 'Cancelled%')          AS cancelled_orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE o.status LIKE 'Cancelled%') / COUNT(*), 1)
                                                                   AS cancellation_rate_pct
FROM order_categories oc
JOIN ecommerce.orders o ON o.order_id = oc.order_id
GROUP BY oc.category
ORDER BY cancellation_rate_pct DESC, orders DESC;
