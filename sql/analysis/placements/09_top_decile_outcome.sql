-- Q: How do the top 10% of students (by MBA percentage) do compared with everyone else?
-- Concepts: CTE, NTILE(10) window function, CASE grouping, AVG
-- Result: group_name | students | placement_rate_pct | avg_salary
WITH ranked AS (
    SELECT *, NTILE(10) OVER (ORDER BY mba_percent DESC) AS decile
    FROM placements.students
)
SELECT CASE WHEN decile = 1 THEN 'Top 10%' ELSE 'Other 90%' END AS group_name,
       COUNT(*)                                                 AS students,
       ROUND(100.0 * AVG(is_placed::int), 1)                    AS placement_rate_pct,
       ROUND(AVG(salary), 0)                                    AS avg_salary
FROM ranked
GROUP BY 1
ORDER BY 1 DESC;
