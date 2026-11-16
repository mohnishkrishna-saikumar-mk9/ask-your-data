-- Q: What is Delhi's 7-day rolling average PM2.5 during winter 2019-20?
-- Concepts: window frame ROWS BETWEEN 6 PRECEDING AND CURRENT ROW, date range filter
-- Result: obs_date | pm25 | rolling_7d_pm25
SELECT obs_date,
       pm25,
       ROUND(AVG(pm25) OVER (ORDER BY obs_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS rolling_7d_pm25
FROM air_quality.city_daily
WHERE city = 'Delhi'
  AND obs_date BETWEEN DATE '2019-11-01' AND DATE '2020-02-29'
ORDER BY obs_date;
