-- Q: Is the employability test score correlated with salary or with MBA percentage, for placed students?
-- Concepts: statistical aggregate CORR(), REGR_SLOPE(), WHERE on boolean
-- Result: placed_students | corr_test_vs_salary | corr_mba_vs_salary | salary_per_test_point
SELECT COUNT(*)                                                  AS placed_students,
       ROUND(CORR(employability_test_percent, salary)::numeric, 3) AS corr_test_vs_salary,
       ROUND(CORR(mba_percent, salary)::numeric, 3)                AS corr_mba_vs_salary,
       ROUND(REGR_SLOPE(salary, employability_test_percent)::numeric, 0) AS salary_per_test_point
FROM placements.students
WHERE is_placed;
