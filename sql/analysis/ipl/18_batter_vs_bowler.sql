-- Q: Which bowler has dismissed the same batter most often?
-- Concepts: COUNT FILTER with NOT IN, GROUP BY two columns, ORDER BY + LIMIT
-- Result: bowler | batter | dismissals | balls  (top 15)
SELECT bowler, batter,
       COUNT(*) FILTER (WHERE is_wicket AND player_dismissed = batter
                          AND dismissal_kind NOT IN ('run out', 'retired hurt',
                                                     'retired out', 'obstructing the field')) AS dismissals,
       COUNT(*) AS balls
FROM ipl.deliveries
WHERE inning <= 2
GROUP BY bowler, batter
ORDER BY dismissals DESC, balls
LIMIT 15;
