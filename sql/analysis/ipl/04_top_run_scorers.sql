-- Q: Who are the top 10 run scorers of all time, and what is their strike rate?
-- Concepts: view, SUM, computed metric (strike rate), NULLIF to avoid divide-by-zero, LIMIT
-- Result: batter | runs | balls_faced | strike_rate  (top 10)
SELECT batter,
       SUM(runs)                                                 AS runs,
       SUM(balls_faced)                                          AS balls_faced,
       ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate
FROM ipl.batting_innings
GROUP BY batter
ORDER BY runs DESC
LIMIT 10;
