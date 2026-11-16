-- Q: At each venue, how often does the team batting first win vs the chasing team (min 10 matches)?
-- Concepts: COUNT FILTER, HAVING, computed percentage
-- Result: venue | matches | bat_first_win_pct | chase_win_pct
SELECT venue,
       COUNT(*)                                                                AS matches,
       ROUND(100.0 * COUNT(*) FILTER (WHERE result = 'runs') / COUNT(*), 1)    AS bat_first_win_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE result = 'wickets') / COUNT(*), 1) AS chase_win_pct
FROM ipl.matches
WHERE result IN ('runs', 'wickets')
GROUP BY venue
HAVING COUNT(*) >= 10
ORDER BY matches DESC;
