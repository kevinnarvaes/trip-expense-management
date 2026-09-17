CREATE OR REPLACE TABLE fact_balances AS
WITH participant_trips AS (
    SELECT
        trip_id,
        traveler_id
    FROM silver_trip_travelers
),
expense_amounts_paid AS (
    SELECT
        trip_id,
        lender_traveler_id AS traveler_id,
        SUM(amount_lps) AS paid_lps
    FROM silver_expenses
    GROUP BY
        trip_id,
        lender_traveler_id
),
expense_amounts_owed AS (
    SELECT
        trip_id,
        traveler_id,
        SUM(share_lps) AS owed_lps
    FROM fact_expense_shares
    GROUP BY
        trip_id,
        traveler_id
),
payments_sent AS (
    SELECT
        trip_id,
        debtor_traveler_id AS traveler_id,
        SUM(amount_lps) AS payment_sent_lps
    FROM fact_payments
    GROUP BY
        trip_id,
        debtor_traveler_id
),
payments_received AS (
    SELECT
        trip_id,
        lender_traveler_id AS traveler_id,
        SUM(amount_lps) AS payment_received_lps
    FROM fact_payments
    GROUP BY
        trip_id,
        lender_traveler_id
)
SELECT
    pt.trip_id || '_' || pt.traveler_id AS balance_id,
    pt.trip_id,
    pt.traveler_id,
    COALESCE(paid.paid_lps, 0) AS paid_lps,
    COALESCE(owed.owed_lps, 0) AS owed_lps,
    -- Position from expenses only, before any transfers are applied.
    COALESCE(paid.paid_lps, 0)
        - COALESCE(owed.owed_lps, 0) AS expense_balance_lps,
    COALESCE(sent.payment_sent_lps, 0) AS payment_sent_lps,
    COALESCE(received.payment_received_lps, 0) AS payment_received_lps,
    COALESCE(paid.paid_lps, 0)
        + COALESCE(sent.payment_sent_lps, 0)
        - COALESCE(owed.owed_lps, 0)
        - COALESCE(received.payment_received_lps, 0) AS net_balance_lps
FROM participant_trips AS pt
LEFT JOIN expense_amounts_paid AS paid
    ON pt.trip_id = paid.trip_id
    AND pt.traveler_id = paid.traveler_id
LEFT JOIN expense_amounts_owed AS owed
    ON pt.trip_id = owed.trip_id
    AND pt.traveler_id = owed.traveler_id
LEFT JOIN payments_sent AS sent
    ON pt.trip_id = sent.trip_id
    AND pt.traveler_id = sent.traveler_id
LEFT JOIN payments_received AS received
    ON pt.trip_id = received.trip_id
    AND pt.traveler_id = received.traveler_id
ORDER BY pt.trip_id, pt.traveler_id;
