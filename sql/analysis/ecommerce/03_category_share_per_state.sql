-- Q: Within each of the top 5 states, what share of revenue does each category have?
-- Concepts: multiple CTEs, 3-table JOIN, window SUM() OVER (PARTITION BY state)
-- Result: ship_state | category | revenue | share_in_state_pct
WITH sales AS (
    SELECT o.ship_state, p.category, i.amount
    FROM ecommerce.orders o
    JOIN ecommerce.order_items i ON i.order_id = o.order_id
    JOIN ecommerce.products p ON p.sku = i.sku
    WHERE o.status NOT LIKE 'Cancelled%'
),
top_states AS (
    SELECT ship_state FROM sales
    WHERE ship_state IS NOT NULL
    GROUP BY ship_state ORDER BY SUM(amount) DESC NULLS LAST LIMIT 5
)
SELECT s.ship_state, s.category,
       SUM(s.amount) AS revenue,
       ROUND(100.0 * SUM(s.amount)
             / SUM(SUM(s.amount)) OVER (PARTITION BY s.ship_state), 1) AS share_in_state_pct
FROM sales s
JOIN top_states t ON t.ship_state = s.ship_state
GROUP BY s.ship_state, s.category
ORDER BY s.ship_state, revenue DESC NULLS LAST;
