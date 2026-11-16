-- Q: What is the average order value (AOV) for each sales channel and fulfilment type?
-- Concepts: JOIN, AOV = revenue / distinct orders, GROUP BY two columns
-- Result: sales_channel | fulfilment | orders | revenue | aov
SELECT o.sales_channel, o.fulfilment,
       COUNT(DISTINCT o.order_id)                                   AS orders,
       SUM(i.amount)                                                AS revenue,
       ROUND(SUM(i.amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS aov
FROM ecommerce.orders o
JOIN ecommerce.order_items i ON i.order_id = o.order_id
WHERE o.status NOT LIKE 'Cancelled%'
GROUP BY o.sales_channel, o.fulfilment
ORDER BY revenue DESC NULLS LAST;
