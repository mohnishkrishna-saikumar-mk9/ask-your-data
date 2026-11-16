-- Q: How much revenue does each billing country bring, with customers and average invoice value?
-- Concepts: JOIN, SUM, COUNT(DISTINCT), AVG, share of total with a window SUM
-- Result: country | customers | invoices | revenue | avg_invoice | revenue_share_pct
SELECT i.billing_country                                          AS country,
       COUNT(DISTINCT i.customer_id)                              AS customers,
       COUNT(*)                                                   AS invoices,
       SUM(i.total)                                               AS revenue,
       ROUND(AVG(i.total), 2)                                     AS avg_invoice,
       ROUND(100.0 * SUM(i.total) / SUM(SUM(i.total)) OVER (), 1) AS revenue_share_pct
FROM chinook.invoice i
GROUP BY i.billing_country
ORDER BY revenue DESC;
