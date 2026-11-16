-- Q: Which 10 states bring the most revenue?
-- Concepts: aggregate-before-join CTE, JOIN, GROUP BY, share of total with a window SUM() OVER ()
-- Result: ship_state | revenue | orders | revenue_share_pct  (top 10)
WITH order_totals AS (
    SELECT order_id, SUM(amount) AS order_value
    FROM ecommerce.order_items
    GROUP BY order_id
)
SELECT o.ship_state,
       SUM(t.order_value)                                                AS revenue,
       COUNT(*)                                                          AS orders,
       ROUND(100.0 * SUM(t.order_value) / SUM(SUM(t.order_value)) OVER (), 2) AS revenue_share_pct
FROM ecommerce.orders o
JOIN order_totals t ON t.order_id = o.order_id
WHERE o.status NOT LIKE 'Cancelled%'
  AND o.ship_state IS NOT NULL
GROUP BY o.ship_state
ORDER BY revenue DESC
LIMIT 10;
