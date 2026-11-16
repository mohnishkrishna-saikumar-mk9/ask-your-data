-- Q: Which product categories have the highest order cancellation rate?
-- Concepts: CASE with LIKE, COUNT DISTINCT, conditional ratio, 3-table JOIN
-- Result: category | orders | cancelled_orders | cancellation_rate_pct
SELECT p.category,
       COUNT(DISTINCT o.order_id) AS orders,
       COUNT(DISTINCT CASE WHEN o.status LIKE 'Cancelled%' THEN o.order_id END) AS cancelled_orders,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN o.status LIKE 'Cancelled%' THEN o.order_id END)
             / COUNT(DISTINCT o.order_id), 1) AS cancellation_rate_pct
FROM ecommerce.orders o
JOIN ecommerce.order_items i ON i.order_id = o.order_id
JOIN ecommerce.products p ON p.sku = i.sku
GROUP BY p.category
ORDER BY cancellation_rate_pct DESC;
