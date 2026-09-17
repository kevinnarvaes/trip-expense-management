CREATE OR REPLACE TABLE dim_trips AS
SELECT
    trip_id,
    trip,
    destination,
    start_date,
    end_date
FROM silver_trips
ORDER BY trip_id;
