-- Q: What share of real customers (customer_unique_id) placed more than one order?
-- Concepts: the customer_id vs customer_unique_id trap, CTE, COUNT FILTER, ratio
-- Result: customers | repeat_customers | repeat_rate_pct
-- Note: each order has exactly one customer_id row, so COUNT(*) per person counts orders
--       (no COUNT(DISTINCT) needed).
WITH orders_per_person AS (
    SELECT c.customer_unique_id, COUNT(*) AS orders
    FROM olist.orders o
    JOIN olist.customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
)
SELECT COUNT(*)                                                   AS customers,
       COUNT(*) FILTER (WHERE orders > 1)                         AS repeat_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE orders > 1) / COUNT(*), 2) AS repeat_rate_pct
FROM orders_per_person;
