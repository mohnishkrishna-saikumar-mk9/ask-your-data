-- Q: How many tracks have never been bought, per genre, and what share of the genre is that?
-- Concepts: anti-join with LEFT JOIN ... IS NULL, COUNT FILTER, ratio
-- Result: genre | tracks | never_sold | never_sold_pct
SELECT g.name                                                                  AS genre,
       COUNT(*)                                                                AS tracks,
       COUNT(*) FILTER (WHERE il.track_id IS NULL)                             AS never_sold,
       ROUND(100.0 * COUNT(*) FILTER (WHERE il.track_id IS NULL) / COUNT(*), 1) AS never_sold_pct
FROM chinook.track t
JOIN chinook.genre g ON g.genre_id = t.genre_id
LEFT JOIN (SELECT DISTINCT track_id FROM chinook.invoice_line) il ON il.track_id = t.track_id
GROUP BY g.name
ORDER BY never_sold DESC;
