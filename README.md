# trip-expense-management

An end-to-end data platform for managing shared trip expenses, demonstrating Python ETL, SQL transformations, PostgreSQL, Airflow orchestration, and Power BI analytics.

## Current pipeline

```text
Google Sheets export
        ↓
Bronze CSVs (raw source tables)
        ↓
Silver CSVs (cleaned relational tables)
        ↓
DuckDB + checked-in SQL models
        ↓
Gold CSVs (dimensions and reporting facts)
```

Run the Silver and Gold scripts in that order:

```powershell
python data-pipelines/transformations/transform_silver.py
python data-pipelines/transformations/transform_gold.py
```

To run every layer in sequence, use:

```powershell
python data-pipelines/transformations/run_pipeline.py
```

Gold SQL lives in `data-pipelines/transformations/sql/gold`. The resulting
tables are `dim_travelers`, `dim_trips`, `fact_payments`,
`fact_expense_shares`, and `fact_balances`.

## Power BI reports

Both PBIP reports use the `p_gold_folder` Power Query parameter for their CSV
source. It currently points to this repository's Gold output folder. After
moving or cloning the repository, update that one parameter to the local
`data-pipelines\database\gold` directory before refreshing the report.

See [Future Features](FUTURE_FEATURES.md) for the planned database, mock-data,
Google Sheets, and GitHub Pages enhancements.
An end-to-end data platform for managing shared trip expenses, demonstrating Python ETL, SQL transformations, PostgreSQL, Airflow orchestration, and Power BI analytics.
