-- Q: Who took the most wickets in each season (Purple Cap), keeping ties?
-- Concepts: multiple CTEs, DENSE_RANK() OVER (PARTITION BY), ties kept by dense rank
-- Result: season | bowler | wickets
WITH season_wkts AS (
    SELECT season, bowler, SUM(wickets) AS wickets
    FROM ipl.bowling_innings
    GROUP BY season, bowler
),
ranked AS (
    SELECT season, bowler, wickets,
           DENSE_RANK() OVER (PARTITION BY season ORDER BY wickets DESC) AS rnk
    FROM season_wkts
)
SELECT season, bowler, wickets
FROM ranked
WHERE rnk = 1
ORDER BY season, bowler;
