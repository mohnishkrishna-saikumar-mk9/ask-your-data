-- Q: Which batters have scored 400+ runs in the most seasons (consistency)?
-- Concepts: subquery in FROM, two-level aggregation, HAVING
-- Result: batter | seasons_400_plus | best_season_runs  (top 15)
SELECT batter,
       COUNT(*)  AS seasons_400_plus,
       MAX(runs) AS best_season_runs
FROM (
    SELECT season, batter, SUM(runs) AS runs
    FROM ipl.batting_innings
    GROUP BY season, batter
    HAVING SUM(runs) >= 400
) AS big_seasons
GROUP BY batter
ORDER BY seasons_400_plus DESC, best_season_runs DESC
LIMIT 15;
