-- Q: What does the salary distribution look like for placed students (min, quartiles, max)?
-- Concepts: ordered-set aggregates PERCENTILE_CONT ... WITHIN GROUP, WHERE on boolean
-- Result: placed_students | min_salary | p25 | median | p75 | p90 | max_salary
SELECT COUNT(*)                                                 AS placed_students,
       MIN(salary)                                              AS min_salary,
       PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary)     AS p25,
       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY salary)     AS median,
       PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary)     AS p75,
       PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY salary)     AS p90,
       MAX(salary)                                              AS max_salary
FROM placements.students
WHERE is_placed;
