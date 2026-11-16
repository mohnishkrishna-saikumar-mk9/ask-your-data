-- Q: What is the monthly revenue and the running total since the store opened?
-- Concepts: CTE, date_trunc, GROUP BY, running SUM() OVER (ORDER BY month ROWS UNBOUNDED PRECEDING)
-- Result: month | invoices | revenue | running_revenue
WITH monthly AS (
    SELECT date_trunc('month', invoice_date)::date AS month,
           COUNT(*)                                AS invoices,
           SUM(total)                              AS revenue
    FROM chinook.invoice
    GROUP BY 1
)
SELECT month, invoices, revenue,
       SUM(revenue) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) AS running_revenue
FROM monthly
ORDER BY month;
