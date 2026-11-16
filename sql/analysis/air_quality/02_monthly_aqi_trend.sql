-- Q: How did the monthly average AQI change over time in Delhi, Mumbai, Bengaluru and Chennai?
-- Concepts: date_trunc('month'), WHERE IN list, GROUP BY two columns (long format for a line chart)
-- Result: month | city | avg_aqi
SELECT date_trunc('month', obs_date)::date AS month,
       city,
       ROUND(AVG(aqi), 0)                  AS avg_aqi
FROM air_quality.city_daily
WHERE city IN ('Delhi', 'Mumbai', 'Bengaluru', 'Chennai')
  AND aqi IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;
