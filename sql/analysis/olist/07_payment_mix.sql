-- Q: How do customers pay - share of payment value by type, and average instalments?
-- Concepts: GROUP BY, share of total with SUM() OVER (), AVG, FILTER out undefined values
-- Result: payment_type | payments | value | value_share_pct | avg_installments
SELECT payment_type,
       COUNT(*)                                                     AS payments,
       SUM(payment_value)                                           AS value,
       ROUND(100.0 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 1) AS value_share_pct,
       ROUND(AVG(payment_installments), 2)                          AS avg_installments
FROM olist.payments
WHERE payment_type <> 'not_defined'
GROUP BY payment_type
ORDER BY value DESC;
