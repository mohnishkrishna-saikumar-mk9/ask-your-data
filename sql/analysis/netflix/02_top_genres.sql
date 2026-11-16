-- Q: Which genres have the most titles, split by movies and TV shows?
-- Concepts: bridge table JOIN, COUNT FILTER, ORDER BY + LIMIT
-- Result: genre | titles | movies | tv_shows  (top 15)
SELECT g.genre,
       COUNT(*)                                    AS titles,
       COUNT(*) FILTER (WHERE t.type = 'Movie')    AS movies,
       COUNT(*) FILTER (WHERE t.type = 'TV Show')  AS tv_shows
FROM netflix.title_genres g
JOIN netflix.titles t ON t.show_id = g.show_id
GROUP BY g.genre
ORDER BY titles DESC
LIMIT 15;
