-- Q: Does studying under a Central board vs Others (class 10 and 12) affect placement?
-- Concepts: GROUP BY two columns, AVG on boolean, HAVING to hide tiny groups
-- Result: ssc_board | hsc_board | students | placement_rate_pct
SELECT ssc_board, hsc_board,
       COUNT(*)                              AS students,
       ROUND(100.0 * AVG(is_placed::int), 1) AS placement_rate_pct
FROM placements.students
GROUP BY ssc_board, hsc_board
HAVING COUNT(*) >= 5
ORDER BY placement_rate_pct DESC;
