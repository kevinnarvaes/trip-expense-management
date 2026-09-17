CREATE OR REPLACE TABLE dim_travelers AS
SELECT
    traveler_id,
    traveler
FROM silver_travelers
ORDER BY traveler_id;
