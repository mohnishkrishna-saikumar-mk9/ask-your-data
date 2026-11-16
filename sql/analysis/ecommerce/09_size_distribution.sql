-- Q: How are units sold distributed across sizes within each category?
-- Concepts: JOIN, GROUP BY two columns, window SUM() OVER (PARTITION BY category) for percentage
-- Result: category | size | units | pct_of_category
SELECT p.category, p.size,
       SUM(i.qty) AS units,
       ROUND(100.0 * SUM(i.qty) / NULLIF(SUM(SUM(i.qty)) OVER (PARTITION BY p.category), 0), 1)
                  AS pct_of_category
FROM ecommerce.order_items i
JOIN ecommerce.products p ON p.sku = i.sku
GROUP BY p.category, p.size
ORDER BY p.category, units DESC;
