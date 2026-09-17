CREATE OR REPLACE TABLE fact_expense_shares AS
WITH allocated_expenses AS (
    SELECT
        e.expense_id,
        e.trip_id,
        e.trip,
        e.reason,
        e.expense_date,
        e.expense_type,
        e.product,
        e.currency,
        e.exchange_rate,
        e.amount_original,
        e.amount_lps,
        e.amount_usd,
        e.lender_traveler_id,
        e.debtor_traveler_id AS traveler_id,
        FALSE AS is_shared_expense,
        1 AS participant_count
    FROM silver_expenses AS e
    WHERE NOT e.is_shared_expense

    UNION ALL

    SELECT
        e.expense_id,
        e.trip_id,
        e.trip,
        e.reason,
        e.expense_date,
        e.expense_type,
        e.product,
        e.currency,
        e.exchange_rate,
        e.amount_original,
        e.amount_lps,
        e.amount_usd,
        e.lender_traveler_id,
        tt.traveler_id,
        TRUE AS is_shared_expense,
        COUNT(*) OVER (PARTITION BY e.expense_id) AS participant_count
    FROM silver_expenses AS e
    INNER JOIN silver_trip_travelers AS tt
        ON e.trip_id = tt.trip_id
    WHERE e.is_shared_expense
)
SELECT
    expense_id || '_' || traveler_id AS expense_share_id,
    expense_id,
    trip_id,
    traveler_id,
    lender_traveler_id,
    trip,
    reason,
    expense_date,
    expense_type,
    product,
    currency,
    exchange_rate,
    amount_original AS expense_amount_original,
    amount_lps AS expense_amount_lps,
    amount_usd AS expense_amount_usd,
    is_shared_expense,
    participant_count,
    amount_original / participant_count AS share_original,
    amount_lps / participant_count AS share_lps,
    amount_usd / participant_count AS share_usd
FROM allocated_expenses
ORDER BY expense_id, traveler_id;
