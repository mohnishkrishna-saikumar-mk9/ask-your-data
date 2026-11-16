-- Q: How did PM2.5 during the 2020 lockdown (25 Mar - 31 May) compare with the same dates in 2019?
-- Concepts: multiple CTEs, date ranges, JOIN two periods on city, percentage change
-- Result: city | pm25_2019 | pm25_lockdown_2020 | change_pct
WITH y2019 AS (
    SELECT city, AVG(pm25) AS pm25
    FROM air_quality.city_daily
    WHERE obs_date BETWEEN DATE '2019-03-25' AND DATE '2019-05-31'
    GROUP BY city
),
y2020 AS (
    SELECT city, AVG(pm25) AS pm25
    FROM air_quality.city_daily
    WHERE obs_date BETWEEN DATE '2020-03-25' AND DATE '2020-05-31'
    GROUP BY city
)
SELECT a.city,
       ROUND(a.pm25, 1)                                    AS pm25_2019,
       ROUND(b.pm25, 1)                                    AS pm25_lockdown_2020,
       ROUND(100.0 * (b.pm25 - a.pm25) / a.pm25, 1)        AS change_pct
FROM y2019 a
JOIN y2020 b ON b.city = a.city
WHERE a.pm25 IS NOT NULL AND b.pm25 IS NOT NULL
ORDER BY change_pct;
