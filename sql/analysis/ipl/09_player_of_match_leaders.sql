-- Q: Which players have won the most Player of the Match awards?
-- Concepts: GROUP BY, COUNT, NULL filter, ORDER BY + LIMIT
-- Result: player | awards  (top 15)
SELECT player_of_match AS player,
       COUNT(*)        AS awards
FROM ipl.matches
WHERE player_of_match IS NOT NULL
GROUP BY player_of_match
ORDER BY awards DESC, player
LIMIT 15;
