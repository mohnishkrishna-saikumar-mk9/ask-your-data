-- Q: How does placement rate change across MBA score bands (50-55, 55-60, ...)?
-- Concepts: WIDTH_BUCKET to bin a number, CTE, string formatting of the band label
-- Result: band | students | placement_rate_pct
WITH banded AS (
    SELECT WIDTH_BUCKET(mba_percent, 50, 80, 6) AS bucket, is_placed
    FROM placements.students
)
SELECT (50 + (bucket - 1) * 5) || '-' || (55 + (bucket - 1) * 5) AS band,
       COUNT(*)                                                 AS students,
       ROUND(100.0 * AVG(is_placed::int), 1)                    AS placement_rate_pct
FROM banded
GROUP BY bucket
ORDER BY bucket;
