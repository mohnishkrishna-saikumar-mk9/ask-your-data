-- Q: How many movies and TV shows were added to Netflix each year?
-- Concepts: EXTRACT(YEAR ...), COUNT FILTER to pivot two categories into columns
-- Result: year_added | movies | tv_shows | total
SELECT EXTRACT(YEAR FROM date_added)::int                 AS year_added,
       COUNT(*) FILTER (WHERE type = 'Movie')             AS movies,
       COUNT(*) FILTER (WHERE type = 'TV Show')           AS tv_shows,
       COUNT(*)                                           AS total
FROM netflix.titles
WHERE date_added IS NOT NULL
GROUP BY 1
ORDER BY 1;
