-- Q: How did each team's win percentage change from one season to the next?
-- Concepts: UNION ALL to unpivot team1/team2, multiple CTEs, LAG() window function
-- Result: team | season | matches | win_pct | prev_win_pct | change_pct_points
WITH appearances AS (
    SELECT season, team1 AS team, winner FROM ipl.matches
    UNION ALL
    SELECT season, team2 AS team, winner FROM ipl.matches
),
season_stats AS (
    SELECT team, season,
           COUNT(*)                                                         AS matches,
           ROUND(100.0 * AVG(CASE WHEN winner = team THEN 1 ELSE 0 END), 1) AS win_pct
    FROM appearances
    GROUP BY team, season
)
SELECT team, season, matches, win_pct,
       LAG(win_pct) OVER (PARTITION BY team ORDER BY season)           AS prev_win_pct,
       win_pct - LAG(win_pct) OVER (PARTITION BY team ORDER BY season) AS change_pct_points
FROM season_stats
ORDER BY team, season;
