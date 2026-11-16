-- Q: For each customer state, what are the average delivery days and the late-delivery percentage?
-- Concepts: timestamp arithmetic with EXTRACT(EPOCH ...), CASE, HAVING, ORDER BY
-- Result: state | delivered_orders | avg_delivery_days | late_pct
SELECT c.state,
       COUNT(*)                                                                  AS delivered_orders,
       ROUND(AVG(EXTRACT(EPOCH FROM o.order_delivered_customer_date
                                  - o.order_purchase_timestamp) / 86400)::numeric, 1) AS avg_delivery_days,
       ROUND(100.0 * AVG(CASE WHEN o.order_delivered_customer_date
                                   > o.order_estimated_delivery_date THEN 1 ELSE 0 END), 1) AS late_pct
FROM olist.orders o
JOIN olist.customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.state
HAVING COUNT(*) >= 100
ORDER BY avg_delivery_days DESC;
