-- Q: How has the average movie length changed by release decade?
-- Concepts: integer arithmetic to bucket years into decades, AVG, MIN/MAX, HAVING
-- Result: decade | movies | avg_minutes | shortest | longest
SELECT (release_year / 10) * 10           AS decade,
       COUNT(*)                           AS movies,
       ROUND(AVG(duration_minutes), 1)    AS avg_minutes,
       MIN(duration_minutes)              AS shortest,
       MAX(duration_minutes)              AS longest
FROM netflix.titles
WHERE type = 'Movie' AND duration_minutes IS NOT NULL
GROUP BY 1
HAVING COUNT(*) >= 10
ORDER BY 1;
