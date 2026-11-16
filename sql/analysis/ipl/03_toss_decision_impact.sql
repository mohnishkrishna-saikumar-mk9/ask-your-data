-- Q: When a team wins the toss, how often does it win the match - by season and toss decision?
-- Concepts: CASE inside AVG, GROUP BY two columns, ROUND
-- Result: season | toss_decision | matches | toss_winner_win_pct
SELECT season,
       toss_decision,
       COUNT(*)                                                                AS matches,
       ROUND(100.0 * AVG(CASE WHEN winner = toss_winner THEN 1 ELSE 0 END), 1) AS toss_winner_win_pct
FROM ipl.matches
WHERE winner IS NOT NULL
GROUP BY season, toss_decision
ORDER BY season, toss_decision;
