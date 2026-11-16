-- Q: Which investors took part in the most funding rounds, and how many different startups did they back?
-- Concepts: bridge table JOIN, COUNT(DISTINCT), WHERE NOT LIKE to drop placeholder names
-- Result: investor_name | rounds | startups_backed  (top 15)
SELECT ri.investor_name,
       COUNT(DISTINCT ri.round_id)        AS rounds,
       COUNT(DISTINCT fr.startup_name)    AS startups_backed
FROM startups.round_investors ri
JOIN startups.funding_rounds fr ON fr.round_id = ri.round_id
WHERE ri.investor_name NOT ILIKE '%undisclosed%'
GROUP BY ri.investor_name
ORDER BY rounds DESC, startups_backed DESC
LIMIT 15;
