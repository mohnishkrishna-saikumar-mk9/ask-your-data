-- Q: Where does each batter rank by batting average, as a percentile (min 1000 runs)?
-- Concepts: CTE, HAVING, PERCENT_RANK() window function, NULLIF
-- Result: batter | runs | dismissals | average | percentile
WITH career AS (
    SELECT batter,
           SUM(runs)                               AS runs,
           SUM(CASE WHEN is_out THEN 1 ELSE 0 END) AS dismissals
    FROM ipl.batting_innings
    GROUP BY batter
    HAVING SUM(runs) >= 1000
)
SELECT batter, runs, dismissals,
       ROUND(runs::numeric / NULLIF(dismissals, 0), 2) AS average,
       ROUND((100 * PERCENT_RANK() OVER (
                ORDER BY runs::numeric / NULLIF(dismissals, 0) NULLS FIRST))::numeric, 1) AS percentile
FROM career
ORDER BY average DESC NULLS LAST;
