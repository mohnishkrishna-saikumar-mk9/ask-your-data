-- Q: Who was the top run scorer (Orange Cap) in each season?
-- Concepts: multiple CTEs, RANK() OVER (PARTITION BY ... ORDER BY ...), filter on rank
-- Result: season | batter | runs
WITH season_runs AS (
    SELECT season, batter, SUM(runs) AS runs
    FROM ipl.batting_innings
    GROUP BY season, batter
),
ranked AS (
    SELECT season, batter, runs,
           RANK() OVER (PARTITION BY season ORDER BY runs DESC) AS rnk
    FROM season_runs
)
SELECT season, batter, runs
FROM ranked
WHERE rnk = 1
ORDER BY season;
