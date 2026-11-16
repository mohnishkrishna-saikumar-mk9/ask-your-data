-- Q: Which path from class 12 stream to MBA specialisation leads to the best placement rate?
-- Concepts: GROUP BY two columns, HAVING, RANK() OVER for ordering paths
-- Result: hsc_stream | mba_specialisation | students | placement_rate_pct | path_rank
SELECT hsc_stream, mba_specialisation,
       COUNT(*)                                                          AS students,
       ROUND(100.0 * AVG(is_placed::int), 1)                             AS placement_rate_pct,
       RANK() OVER (ORDER BY AVG(is_placed::int) DESC)                   AS path_rank
FROM placements.students
GROUP BY hsc_stream, mba_specialisation
HAVING COUNT(*) >= 3
ORDER BY path_rank;
