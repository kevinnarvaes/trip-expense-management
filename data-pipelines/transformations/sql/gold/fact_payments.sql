CREATE OR REPLACE TABLE fact_payments AS
SELECT
    payment_id,
    trip_id,
    debtor_traveler_id,
    lender_traveler_id,
    trip,
    currency,
    exchange_rate,
    amount_original,
    amount_lps,
    amount_usd
FROM silver_payments
ORDER BY payment_id;
