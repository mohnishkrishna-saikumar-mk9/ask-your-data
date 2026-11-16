-- Q: What does the management chain look like - each employee, their manager and their level below the top?
-- Concepts: WITH RECURSIVE (anchor + recursive member), self-join on reports_to, path building
-- Result: level | employee | title | manager | chain
WITH RECURSIVE org AS (
    SELECT employee_id, first_name || ' ' || last_name AS employee, title,
           NULL::text AS manager, 0 AS level,
           (first_name || ' ' || last_name)::text AS chain
    FROM chinook.employee
    WHERE reports_to IS NULL
    UNION ALL
    SELECT e.employee_id, e.first_name || ' ' || e.last_name, e.title,
           o.employee, o.level + 1,
           o.chain || ' > ' || e.first_name || ' ' || e.last_name
    FROM chinook.employee e
    JOIN org o ON e.reports_to = o.employee_id
)
SELECT level, employee, title, manager, chain
FROM org
ORDER BY chain;
