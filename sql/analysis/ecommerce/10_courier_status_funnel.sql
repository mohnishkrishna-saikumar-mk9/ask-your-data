-- Q: What does the order funnel look like from placed to shipped to delivered / returned?
-- Concepts: CASE bucketing, COUNT DISTINCT, ordering by a CASE expression, share of total
-- Result: stage | orders | pct_of_all_orders
WITH staged AS (
    SELECT order_id,
           CASE
               WHEN status LIKE 'Cancelled%'                    THEN '4. Cancelled'
               WHEN status LIKE '%Returned%' OR status LIKE '%Rejected%' THEN '3. Returned / rejected'
               WHEN status LIKE '%Delivered%'                   THEN '2. Delivered'
               WHEN status LIKE 'Shipped%'                      THEN '1. Shipped'
               ELSE                                                  '5. Pending / other'
           END AS stage
    FROM ecommerce.orders
)
SELECT stage,
       COUNT(*)                                          AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_all_orders
FROM staged
GROUP BY stage
ORDER BY stage;
