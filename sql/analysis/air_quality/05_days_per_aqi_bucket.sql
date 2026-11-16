-- Q: For each city, how many days fell in each AQI category, ordered from Good to Severe?
-- Concepts: GROUP BY two columns, CASE to give categories a logical sort order, share within city
-- Result: city | aqi_bucket | days | pct_of_city_days
SELECT city, aqi_bucket,
       COUNT(*)                                                               AS days,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY city), 1)   AS pct_of_city_days
FROM air_quality.city_daily
WHERE aqi_bucket IS NOT NULL
GROUP BY city, aqi_bucket
ORDER BY city,
         CASE aqi_bucket WHEN 'Good' THEN 1 WHEN 'Satisfactory' THEN 2 WHEN 'Moderate' THEN 3
                         WHEN 'Poor' THEN 4 WHEN 'Very Poor' THEN 5 ELSE 6 END;
