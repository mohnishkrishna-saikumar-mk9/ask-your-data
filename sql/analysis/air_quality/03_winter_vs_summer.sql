-- Q: How much worse is air quality in winter (Nov-Feb) than in summer (Mar-Jun) for each city?
-- Concepts: EXTRACT(MONTH ...), CASE season buckets, conditional AVG with FILTER, ratio
-- Result: city | winter_avg_aqi | summer_avg_aqi | winter_to_summer_ratio
SELECT city,
       ROUND(AVG(aqi) FILTER (WHERE EXTRACT(MONTH FROM obs_date) IN (11, 12, 1, 2)), 0) AS winter_avg_aqi,
       ROUND(AVG(aqi) FILTER (WHERE EXTRACT(MONTH FROM obs_date) BETWEEN 3 AND 6), 0)   AS summer_avg_aqi,
       ROUND(AVG(aqi) FILTER (WHERE EXTRACT(MONTH FROM obs_date) IN (11, 12, 1, 2))
             / NULLIF(AVG(aqi) FILTER (WHERE EXTRACT(MONTH FROM obs_date) BETWEEN 3 AND 6), 0), 2)
                                                                                         AS winter_to_summer_ratio
FROM air_quality.city_daily
GROUP BY city
HAVING COUNT(aqi) >= 365
ORDER BY winter_to_summer_ratio DESC NULLS LAST;
