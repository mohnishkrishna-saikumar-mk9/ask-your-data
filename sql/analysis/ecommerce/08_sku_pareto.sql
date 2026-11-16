-- Q: Which SKUs drive revenue, and how quickly does the running share reach 80% (Pareto 80/20)?
-- Concepts: CTE, running SUM() OVER (ORDER BY ...), share of total, ROW_NUMBER
-- Result: rank | sku | category | revenue | running_share_pct  (top 10)
WITH sku_rev AS (
    SELECT i.sku, p.category, SUM(i.amount) AS revenue
    FROM ecommerce.order_items i
    JOIN ecommerce.orders o ON o.order_id = i.order_id
    JOIN ecommerce.products p ON p.sku = i.sku
    WHERE o.status NOT LIKE 'Cancelled%' AND i.amount IS NOT NULL
    GROUP BY i.sku, p.category
)
SELECT ROW_NUMBER() OVER (ORDER BY revenue DESC, sku)                        AS rank,
       sku, category, revenue,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC, sku
                                        ROWS UNBOUNDED PRECEDING)
             / SUM(revenue) OVER (), 2)                                       AS running_share_pct
FROM sku_rev
ORDER BY revenue DESC, sku
LIMIT 10;
