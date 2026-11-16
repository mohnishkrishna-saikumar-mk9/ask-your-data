-- Q: What share of runs came from boundaries (4s and 6s) each season - is T20 batting getting more aggressive?
-- Concepts: INNER JOIN, SUM with CASE, ratio, trend over time
-- Result: season | total_runs | boundary_runs | boundary_pct | sixes
SELECT m.season,
       SUM(d.total_runs)                                                    AS total_runs,
       SUM(CASE WHEN d.batter_runs IN (4, 6) THEN d.batter_runs ELSE 0 END) AS boundary_runs,
       ROUND(100.0 * SUM(CASE WHEN d.batter_runs IN (4, 6) THEN d.batter_runs ELSE 0 END)
             / NULLIF(SUM(d.total_runs), 0), 1)                             AS boundary_pct,
       COUNT(*) FILTER (WHERE d.batter_runs = 6)                            AS sixes
FROM ipl.deliveries d
JOIN ipl.matches m ON m.match_id = d.match_id
WHERE d.inning <= 2
GROUP BY m.season
ORDER BY m.season;
