-- Q: What are the highest team innings totals, and the lowest first-innings totals that were successfully defended?
-- Concepts: CTE, INNER JOIN deliveries to matches, UNION ALL of two ranked lists
-- Result: category | team | season | total | opponent
WITH innings_totals AS (
    SELECT d.match_id, d.inning, d.batting_team AS team, d.bowling_team AS opponent,
           m.season, m.winner, SUM(d.total_runs) AS total
    FROM ipl.deliveries d
    JOIN ipl.matches m ON m.match_id = d.match_id
    WHERE d.inning <= 2
    GROUP BY d.match_id, d.inning, d.batting_team, d.bowling_team, m.season, m.winner
)
(SELECT 'highest total' AS category, team, season, total, opponent
 FROM innings_totals ORDER BY total DESC LIMIT 5)
UNION ALL
(SELECT 'lowest defended' AS category, team, season, total, opponent
 FROM innings_totals
 WHERE inning = 1 AND winner = team
 ORDER BY total ASC LIMIT 5);
