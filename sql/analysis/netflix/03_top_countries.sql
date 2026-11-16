-- Q: Which countries produce the most Netflix titles, and what share are movies?
-- Concepts: bridge table JOIN, ratio with COUNT FILTER, ORDER BY + LIMIT
-- Result: country | titles | movie_pct  (top 10)
SELECT c.country,
       COUNT(*)                                                                  AS titles,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.type = 'Movie') / COUNT(*), 1)     AS movie_pct
FROM netflix.title_countries c
JOIN netflix.titles t ON t.show_id = c.show_id
GROUP BY c.country
ORDER BY titles DESC
LIMIT 10;
