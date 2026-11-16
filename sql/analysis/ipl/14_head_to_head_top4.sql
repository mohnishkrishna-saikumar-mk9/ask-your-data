-- Q: What is the head-to-head record between the 4 teams with the most wins?
-- Concepts: multiple CTEs, UNION ALL, INNER JOIN to a top-N list (acts as a filter), CASE
-- Result: team | opponent | matches | wins
WITH top4 AS (
    SELECT winner AS team, COUNT(*) AS wins
    FROM ipl.matches
    WHERE winner IS NOT NULL
    GROUP BY winner
    ORDER BY wins DESC
    LIMIT 4
),
pairs AS (
    SELECT team1 AS team, team2 AS opponent, winner FROM ipl.matches
    UNION ALL
    SELECT team2, team1, winner FROM ipl.matches
)
SELECT p.team, p.opponent,
       COUNT(*)                                           AS matches,
       SUM(CASE WHEN p.winner = p.team THEN 1 ELSE 0 END) AS wins
FROM pairs p
JOIN top4 a ON a.team = p.team
JOIN top4 b ON b.team = p.opponent
GROUP BY p.team, p.opponent
ORDER BY p.team, p.opponent;
