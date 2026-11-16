-- Q: Which 10 states bring the most revenue?
-- Concepts: INNER JOIN, GROUP BY, SUM, share of total with a window SUM() OVER ()
-- Result: ship_state | revenue | orders | revenue_share_pct  (top 10)
SELECT o.ship_state,
       SUM(i.amount)                                           AS revenue,
       COUNT(DISTINCT o.order_id)                              AS orders,
       ROUND(100.0 * SUM(i.amount) / SUM(SUM(i.amount)) OVER (), 2) AS revenue_share_pct
FROM ecommerce.orders o
JOIN ecommerce.order_items i ON i.order_id = o.order_id
WHERE o.status NOT LIKE 'Cancelled%'
  AND o.ship_state IS NOT NULL
GROUP BY o.ship_state
ORDER BY revenue DESC
LIMIT 10;
