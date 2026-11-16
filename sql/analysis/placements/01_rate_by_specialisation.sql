-- Q: What is the placement rate and average salary for each MBA specialisation?
-- Concepts: GROUP BY, AVG of a boolean cast to int, AVG ignoring NULL salaries
-- Result: mba_specialisation | students | placement_rate_pct | avg_salary
SELECT mba_specialisation,
       COUNT(*)                                AS students,
       ROUND(100.0 * AVG(is_placed::int), 1)   AS placement_rate_pct,
       ROUND(AVG(salary), 0)                   AS avg_salary
FROM placements.students
GROUP BY mba_specialisation
ORDER BY placement_rate_pct DESC;
