-- Q: For each sales support rep, who is their highest-spending customer?
-- Concepts: JOIN customer -> employee (support_rep_id), CTE, ROW_NUMBER() per rep, string concatenation
-- Result: sales_rep | customer | country | total_spent
WITH spend AS (
    SELECT e.first_name || ' ' || e.last_name  AS sales_rep,
           c.first_name || ' ' || c.last_name  AS customer,
           c.country,
           SUM(i.total)                        AS total_spent
    FROM chinook.customer c
    JOIN chinook.employee e ON e.employee_id = c.support_rep_id
    JOIN chinook.invoice i  ON i.customer_id = c.customer_id
    GROUP BY e.employee_id, e.first_name, e.last_name, c.customer_id, c.first_name, c.last_name, c.country
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY sales_rep ORDER BY total_spent DESC, customer) AS rn
    FROM spend
)
SELECT sales_rep, customer, country, total_spent
FROM ranked
WHERE rn = 1
ORDER BY total_spent DESC;
