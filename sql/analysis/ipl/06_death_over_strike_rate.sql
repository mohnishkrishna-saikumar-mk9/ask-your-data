-- Q: Which batters have the best strike rate in death overs (overs 16-20), min 200 balls?
-- Concepts: WHERE on derived phase column, COUNT FILTER, HAVING, computed metric, ORDER BY + LIMIT
-- Result: batter | runs | balls | strike_rate  (top 10)
SELECT batter,
       SUM(batter_runs)                                             AS runs,
       COUNT(*) FILTER (WHERE extras_type IS DISTINCT FROM 'wides') AS balls,
       ROUND(100.0 * SUM(batter_runs)
             / NULLIF(COUNT(*) FILTER (WHERE extras_type IS DISTINCT FROM 'wides'), 0), 2) AS strike_rate
FROM ipl.deliveries
WHERE phase = 'death'
  AND inning <= 2
GROUP BY batter
HAVING COUNT(*) FILTER (WHERE extras_type IS DISTINCT FROM 'wides') >= 200
ORDER BY strike_rate DESC
LIMIT 10;
