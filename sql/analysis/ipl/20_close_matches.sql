-- Q: How many close finishes (won by 5 runs or less, or by 1 wicket) were there each season?
-- Concepts: CTEs, date function EXTRACT, LEFT JOIN so seasons with zero still appear, scalar subquery
-- Result: season | matches | close_matches | close_pct | latest_close_finish
WITH seasons AS (
    SELECT EXTRACT(YEAR FROM match_date)::int AS season, COUNT(*) AS matches
    FROM ipl.matches
    GROUP BY 1
),
close_games AS (
    SELECT match_id, season, match_date
    FROM ipl.matches
    WHERE (result = 'runs' AND result_margin <= 5)
       OR (result = 'wickets' AND result_margin = 1)
)
SELECT s.season,
       s.matches,
       COUNT(c.match_id)                                    AS close_matches,
       ROUND(100.0 * COUNT(c.match_id) / s.matches, 1)      AS close_pct,
       MAX(c.match_date)                                    AS latest_close_finish
FROM seasons s
LEFT JOIN close_games c ON c.season = s.season
GROUP BY s.season, s.matches
ORDER BY s.season;
