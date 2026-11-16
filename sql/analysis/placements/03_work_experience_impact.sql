-- Q: Does work experience before the MBA improve placement rate and salary?
-- Concepts: CASE label, GROUP BY boolean, AVG with NULLs
-- Result: work_experience | students | placement_rate_pct | avg_salary
SELECT CASE WHEN has_work_experience THEN 'Yes' ELSE 'No' END AS work_experience,
       COUNT(*)                                               AS students,
       ROUND(100.0 * AVG(is_placed::int), 1)                  AS placement_rate_pct,
       ROUND(AVG(salary), 0)                                  AS avg_salary
FROM placements.students
GROUP BY 1
ORDER BY 1;
