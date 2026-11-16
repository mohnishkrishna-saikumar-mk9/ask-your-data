-- Q: Do late deliveries get worse review scores?
-- Concepts: CASE bucket, JOIN, AVG, COUNT FILTER, comparing two groups
-- Result: delivery | reviews | avg_score | one_star_pct
SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 'late' ELSE 'on time' END                                       AS delivery,
       COUNT(*)                                                                  AS reviews,
       ROUND(AVG(r.review_score), 2)                                             AS avg_score,
       ROUND(100.0 * COUNT(*) FILTER (WHERE r.review_score = 1) / COUNT(*), 1)   AS one_star_pct
FROM olist.reviews r
JOIN olist.orders o ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1
ORDER BY 1;
