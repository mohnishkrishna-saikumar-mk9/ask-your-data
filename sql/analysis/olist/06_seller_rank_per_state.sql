-- Q: Who are the top 3 sellers by GMV in each of the 5 biggest seller states?
-- Concepts: multiple CTEs, RANK() OVER (PARTITION BY state), filtering on a window result
-- Result: state | seller_id | gmv | state_rank
WITH seller_gmv AS (
    SELECT s.state, s.seller_id, SUM(i.price) AS gmv
    FROM olist.order_items i
    JOIN olist.sellers s ON s.seller_id = i.seller_id
    GROUP BY s.state, s.seller_id
),
top_states AS (
    SELECT state FROM seller_gmv GROUP BY state ORDER BY SUM(gmv) DESC LIMIT 5
),
ranked AS (
    SELECT g.*, RANK() OVER (PARTITION BY g.state ORDER BY g.gmv DESC) AS state_rank
    FROM seller_gmv g
    JOIN top_states t ON t.state = g.state
)
SELECT state, seller_id, gmv, state_rank
FROM ranked
WHERE state_rank <= 3
ORDER BY state, state_rank;
