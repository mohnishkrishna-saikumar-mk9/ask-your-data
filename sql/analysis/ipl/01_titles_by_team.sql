-- Q: How many IPL titles has each team won (winner of the Final each season)?
-- Concepts: WHERE filter, GROUP BY, COUNT, STRING_AGG with ORDER BY
-- Result: team | titles | seasons_won
SELECT winner                                         AS team,
       COUNT(*)                                       AS titles,
       STRING_AGG(season::text, ', ' ORDER BY season) AS seasons_won
FROM ipl.matches
WHERE match_type = 'Final'
  AND winner IS NOT NULL
GROUP BY winner
ORDER BY titles DESC, team;
