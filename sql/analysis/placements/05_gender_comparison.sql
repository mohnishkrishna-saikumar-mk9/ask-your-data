-- Q: How do placement rate and salary compare between male and female students?
-- Concepts: GROUP BY, AVG on boolean, median with PERCENTILE_CONT, FILTER
-- Result: gender | students | placement_rate_pct | avg_salary | median_salary
SELECT gender,
       COUNT(*)                                                                AS students,
       ROUND(100.0 * AVG(is_placed::int), 1)                                   AS placement_rate_pct,
       ROUND(AVG(salary), 0)                                                   AS avg_salary,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) FILTER (WHERE is_placed) AS median_salary
FROM placements.students
GROUP BY gender
ORDER BY gender;
