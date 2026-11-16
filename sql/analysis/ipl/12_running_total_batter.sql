-- Q: How did V Kohli's career runs build up season by season (running total)?
-- Concepts: CTE, window SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING) = running total
-- Result: season | season_runs | career_runs
WITH by_season AS (
    SELECT season, SUM(runs) AS season_runs
    FROM ipl.batting_innings
    WHERE batter = 'V Kohli'
    GROUP BY season
)
SELECT season,
       season_runs,
       SUM(season_runs) OVER (ORDER BY season ROWS UNBOUNDED PRECEDING) AS career_runs
FROM by_season
ORDER BY season;
