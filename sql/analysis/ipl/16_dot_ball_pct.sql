-- Q: Which bowlers bowl the highest percentage of dot balls (min 1000 legal balls)?
-- Concepts: CTE, COUNT FILTER, HAVING, percentage
-- Result: bowler | legal_balls | dot_balls | dot_ball_pct  (top 10)
WITH legal AS (
    SELECT bowler, total_runs
    FROM ipl.deliveries
    WHERE (extras_type IS NULL OR extras_type NOT IN ('wides', 'noballs'))
      AND inning <= 2
)
SELECT bowler,
       COUNT(*)                                                            AS legal_balls,
       COUNT(*) FILTER (WHERE total_runs = 0)                              AS dot_balls,
       ROUND(100.0 * COUNT(*) FILTER (WHERE total_runs = 0) / COUNT(*), 1) AS dot_ball_pct
FROM legal
GROUP BY bowler
HAVING COUNT(*) >= 1000
ORDER BY dot_ball_pct DESC
LIMIT 10;
