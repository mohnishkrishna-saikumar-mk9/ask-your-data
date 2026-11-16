-- Q: What is the average order value (AOV) for each sales channel and fulfilment type?
-- Concepts: aggregate-before-join CTE, AOV = revenue / orders, GROUP BY two columns, NULLIF
-- Result: sales_channel | fulfilment | orders | revenue | aov
WITH order_totals AS (
    SELECT order_id, SUM(amount) AS order_value
    FROM ecommerce.order_items
    GROUP BY order_id
)
SELECT o.sales_channel, o.fulfilment,
       COUNT(*)                                            AS orders,
       SUM(t.order_value)                                  AS revenue,
       ROUND(SUM(t.order_value) / NULLIF(COUNT(*), 0), 2)  AS aov
FROM ecommerce.orders o
JOIN order_totals t ON t.order_id = o.order_id
WHERE o.status NOT LIKE 'Cancelled%'
GROUP BY o.sales_channel, o.fulfilment
ORDER BY revenue DESC NULLS LAST;
