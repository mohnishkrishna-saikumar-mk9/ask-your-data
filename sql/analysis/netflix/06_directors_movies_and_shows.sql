-- Q: Which directors have made both movies and TV shows on Netflix?
-- Concepts: GROUP BY with HAVING on two conditional counts (set logic without INTERSECT)
-- Result: director | movies | tv_shows
SELECT d.director,
       COUNT(*) FILTER (WHERE t.type = 'Movie')    AS movies,
       COUNT(*) FILTER (WHERE t.type = 'TV Show')  AS tv_shows
FROM netflix.title_directors d
JOIN netflix.titles t ON t.show_id = d.show_id
GROUP BY d.director
HAVING COUNT(*) FILTER (WHERE t.type = 'Movie') > 0
   AND COUNT(*) FILTER (WHERE t.type = 'TV Show') > 0
ORDER BY COUNT(*) DESC, d.director  -- output aliases cannot be used inside an ORDER BY expression
LIMIT 20;
