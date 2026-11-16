-- Q: What is the monthly revenue and month-over-month growth?
-- Concepts: CTE, date_trunc, JOIN, LAG() window function, percentage change
-- Result: month | revenue | orders | prev_revenue | mom_growth_pct
WITH monthly AS (
    SELECT date_trunc('month', o.order_date)::date AS month,
           SUM(i.amount)                           AS revenue,
           COUNT(DISTINCT o.order_id)              AS orders
    FROM ecommerce.orders o
    JOIN ecommerce.order_items i ON i.order_id = o.order_id
    WHERE o.status NOT LIKE 'Cancelled%'
    GROUP BY 1
)
SELECT month, revenue, orders,
       LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;
