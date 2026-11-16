-- Q: Which actors appear most often in Indian titles?
-- Concepts: semi-join with EXISTS (titles that have country 'India'), bridge tables, GROUP BY
-- Result: actor | titles  (top 10)
SELECT ca.actor,
       COUNT(*) AS titles
FROM netflix.title_cast ca
WHERE EXISTS (
    SELECT 1
    FROM netflix.title_countries co
    WHERE co.show_id = ca.show_id
      AND co.country = 'India'
)
GROUP BY ca.actor
ORDER BY titles DESC, ca.actor
LIMIT 10;
