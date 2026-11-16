-- Q: What share of real customers (customer_unique_id) placed more than one order?
-- Concepts: the customer_id vs customer_unique_id trap, CTE, COUNT FILTER, ratio
-- Result: customers | repeat_customers | repeat_rate_pct
WITH orders_per_person AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders
    FROM olist.orders o
    JOIN olist.customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
)
SELECT COUNT(*)                                                   AS customers,
       COUNT(*) FILTER (WHERE orders > 1)                         AS repeat_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE orders > 1) / COUNT(*), 2) AS repeat_rate_pct
FROM orders_per_person;
