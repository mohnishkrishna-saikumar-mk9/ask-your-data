-- Q: Which bowlers have the best economy rate in the powerplay (min 300 legal balls)?
-- Concepts: CTE, conditional aggregation with CASE, economy = runs / (balls / 6)
-- Result: bowler | legal_balls | runs_conceded | economy  (top 10)
WITH pp AS (
    SELECT bowler,
           COUNT(*) FILTER (WHERE extras_type IS NULL
                               OR extras_type NOT IN ('wides', 'noballs')) AS legal_balls,
           SUM(total_runs - CASE WHEN extras_type IN ('byes', 'legbyes')
                                 THEN extra_runs ELSE 0 END)               AS runs_conceded
    FROM ipl.deliveries
    WHERE phase = 'powerplay'
      AND inning <= 2
    GROUP BY bowler
)
SELECT bowler, legal_balls, runs_conceded,
       ROUND(runs_conceded / (legal_balls / 6.0), 2) AS economy
FROM pp
WHERE legal_balls >= 300
ORDER BY economy
LIMIT 10;
