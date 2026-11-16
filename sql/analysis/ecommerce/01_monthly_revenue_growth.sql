-- Q: What is the monthly revenue and month-over-month growth?
-- Concepts: aggregate-before-join CTE, date_trunc, JOIN, LAG() window function, percentage change
-- Result: month | revenue | orders | prev_revenue | mom_growth_pct
-- Note: order lines are summed per order first, so orders can be counted with COUNT(*)
--       instead of a slower COUNT(DISTINCT) over the joined rows.
WITH order_totals AS (
    SELECT order_id, SUM(amount) AS order_value
    FROM ecommerce.order_items
    GROUP BY order_id
),
monthly AS (
    SELECT date_trunc('month', o.order_date)::date AS month,
           SUM(t.order_value)                      AS revenue,
           COUNT(*)                                AS orders
    FROM ecommerce.orders o
    JOIN order_totals t ON t.order_id = o.order_id
    WHERE o.status NOT LIKE 'Cancelled%'
    GROUP BY 1
)
SELECT month, revenue, orders,
       LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;
