-- Q: Which cities have the worst average AQI over the whole period (ignoring missing readings)?
-- Concepts: AVG ignores NULLs, COUNT(column) vs COUNT(*), HAVING for minimum coverage
-- Result: city | days_with_aqi | avg_aqi | avg_pm25  (top 10)
SELECT city,
       COUNT(aqi)              AS days_with_aqi,
       ROUND(AVG(aqi), 0)      AS avg_aqi,
       ROUND(AVG(pm25), 1)     AS avg_pm25
FROM air_quality.city_daily
GROUP BY city
HAVING COUNT(aqi) >= 365
ORDER BY avg_aqi DESC
LIMIT 10;
