-- Q: How does the undergraduate degree field affect placement rate?
-- Concepts: GROUP BY, AVG on boolean, COUNT FILTER
-- Result: degree_field | students | placed | placement_rate_pct
SELECT degree_field,
       COUNT(*)                              AS students,
       COUNT(*) FILTER (WHERE is_placed)     AS placed,
       ROUND(100.0 * AVG(is_placed::int), 1) AS placement_rate_pct
FROM placements.students
GROUP BY degree_field
ORDER BY placement_rate_pct DESC;
