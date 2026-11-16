-- Q: What is the average first-innings score at each venue, by season?
-- Concepts: CTE, INNER JOIN, two-level aggregation (innings total, then average)
-- Result: venue | season | matches | avg_first_innings
WITH first_innings AS (
    SELECT m.venue, m.season, d.match_id, SUM(d.total_runs) AS total
    FROM ipl.deliveries d
    JOIN ipl.matches m ON m.match_id = d.match_id
    WHERE d.inning = 1
    GROUP BY m.venue, m.season, d.match_id
)
SELECT venue, season,
       COUNT(*)             AS matches,
       ROUND(AVG(total), 1) AS avg_first_innings
FROM first_innings
GROUP BY venue, season
ORDER BY venue, season;
