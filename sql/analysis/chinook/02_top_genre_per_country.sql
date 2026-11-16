-- Q: What is the best-selling genre (by units) in each country? Keep ties.
-- Concepts: 4-table JOIN, CTE, RANK() OVER (PARTITION BY country) keeps ties
-- Result: country | genre | units
WITH sales AS (
    SELECT i.billing_country AS country, g.name AS genre, SUM(il.quantity) AS units
    FROM chinook.invoice_line il
    JOIN chinook.invoice i ON i.invoice_id = il.invoice_id
    JOIN chinook.track t   ON t.track_id = il.track_id
    JOIN chinook.genre g   ON g.genre_id = t.genre_id
    GROUP BY i.billing_country, g.name
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY country ORDER BY units DESC) AS rnk
    FROM sales
)
SELECT country, genre, units
FROM ranked
WHERE rnk = 1
ORDER BY country, genre;
