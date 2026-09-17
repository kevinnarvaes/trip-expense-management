# PROJECT_CONTEXT.md

## Project

**Trip Expense Management System**  
Repository: `data-pipeline`

A personal data-engineering and analytics project that may eventually grow into a small application.

The real-world problem is shared travel expenses: one traveler pays an expense upfront and other travelers owe their respective shares.

Current source: a Google Sheet containing:

- `Trips`
- `Travelers`
- `Expenses`

The project is being built incrementally.

## Goals

Demonstrate:

- Python
- ETL / ELT
- data cleaning and validation
- SQL
- relational modeling
- PostgreSQL
- medallion architecture
- Airflow
- Docker
- Power BI
- eventual VM/cloud deployment
- potentially an application layer

Do not implement future technologies prematurely.

## Personal vs Portfolio

The personal version uses real data and remains private.

The portfolio version uses synthetic/sanitized data and must never expose real financial or travel information.

Prefer one codebase with configurable inputs rather than two diverging codebases.

## Current Source Semantics

### Trips

Trip-level records.

### Travelers

People participating in trips.

`Todos` is a special source value in the expense workflow, not an actual traveler. It means all real travelers participate.

### Expenses

Individual expenses. Important concepts include:

- `Trip ID`
- `Debtor`
- `Lander`
- original amount
- LPS amount
- USD amount
- currency
- exchange rate, where present

Current interpretation:

- `Lander` = traveler who actually paid.
- `Debtor` = traveler responsible for the expense.
- `Debtor = Todos` = all real travelers share the expense.

If semantics are ambiguous, inspect the source and document the interpretation rather than silently inventing one.

## Medallion Architecture

### Bronze

Bronze represents data as received from the source.

```text
Google Sheets export
        ↓
extract_bronze.py
        ↓
storage/bronze/*.csv
```

Keep Bronze minimally transformed. Do not apply business rules here.

### Silver

Silver represents cleaned, standardized, validated, and derived data.

```text
storage/bronze/*.csv
        ↓
transform_silver.py
        ↓
storage/silver/*.csv
```

Examples:

- normalize identifiers and strings
- create technical expense IDs
- resolve `Todos`
- create expense shares
- calculate balances
- enforce referential integrity
- validate monetary reconciliation

### Gold

Not implemented yet.

Eventually it will contain reporting/analytics-ready datasets, likely using SQL and potentially a dimensional model.

Do not implement Gold until explicitly requested.

## Current Repository Direction

```text
data-pipeline/
├── README.md
├── PROJECT_CONTEXT.md
├── CODING_STYLE.md
├── requirements.txt
├── .gitignore
│
├── transformations/
│   ├── bronze/
│   │   └── extract_bronze.py
│   └── silver/
│       └── transform_silver.py
│
├── storage/
│   ├── bronze/
│   └── silver/
│
├── tests/
└── docs/
```

This is a direction, not an immutable contract.

The separation is intentional:

- `transformations/` = transformation code
- `storage/` = temporary/local storage simulation
- `tests/` = automated validation
- `docs/` = architecture/documentation

## Current Scripts

### `transformations/bronze/extract_bronze.py`

Responsibilities:

1. Read the current source workbook/export.
2. Extract Trips, Travelers, and Expenses.
3. Perform only minimal structural cleanup.
4. Write raw tables to Bronze CSV storage.

It must not calculate expense shares or balances.

### `transformations/silver/transform_silver.py`

Responsibilities:

1. Read Bronze CSVs.
2. Clean and standardize data.
3. Generate technical expense IDs.
4. Resolve `Todos`.
5. Create `expense_shares`.
6. Create `balances`.
7. Validate results.
8. Write Silver CSVs.

Keep transformation functions modular so they can later be called by Airflow.

## Expense Share Logic

For `Debtor = Todos`, split equally among all real travelers.

For a specific debtor, that traveler receives the full responsibility.

The derived `expense_shares` dataset contains one row per responsible traveler per expense.

## Balance Logic

```text
Net Balance = Amount Paid - Amount Owed
```

Positive means the traveler paid more than their share. Negative means they owe more than they paid.

At trip level:

```text
SUM(Net Balance) = 0
```

within an appropriate monetary tolerance.

## Monetary Handling

The source contains multiple monetary representations, including LPS and USD.

Do not discard original monetary fields without a reason.

Use explicit names such as:

- `amount_lps`
- `amount_usd`
- `share_lps`
- `share_usd`

Document currencies clearly.

The current Pandas implementation may use floats for convenience. Revisit exact decimal/numeric types when moving to production database storage.

## Validation Philosophy

Validation is part of the pipeline.

At minimum validate:

- required columns
- non-empty source tables
- unique identifiers
- valid trip references
- valid traveler references
- valid payers
- valid debtors
- expense-share reconciliation
- trip-level balance reconciliation

Fail loudly with useful errors. Never silently swallow important data errors.

## Future Architecture

### Current

```text
Google Sheets
      ↓
Python
      ↓
CSV Bronze
      ↓
Python
      ↓
CSV Silver
```

### SQL/database iteration

```text
Google Sheets
      ↓
Python
      ↓
Bronze
      ↓
PostgreSQL
      ↓
SQL transformations
      ↓
Gold
      ↓
Power BI
```

### Airflow iteration

```text
             Airflow
                │
       ┌────────┼────────┐
       ↓        ↓        ↓
   Extract   Silver    Gold
       │        │        │
       └────────┴────────┘
                ↓
             Power BI
```

Potential future local environment:

```text
Docker Compose
├── Airflow
├── PostgreSQL
└── supporting services
```

Potential future hosted environment:

```text
VM
├── Airflow
├── PostgreSQL
├── pipeline code
└── supporting services
```

Treat these as roadmap items, not current requirements.

## Portfolio Reproducibility

Eventually the public repository should allow someone to:

1. Clone the repo.
2. Install dependencies.
3. Use included synthetic/sample data.
4. Run Bronze extraction.
5. Run Silver transformations.
6. Inspect outputs.
7. Run SQL transformations.
8. Run tests.
9. Optionally run Airflow locally.
10. Understand how the local demonstration relates to the live/private deployment.

Never publish real personal expense data.

## Development Principles

1. Prefer simple solutions first.
2. Do not implement future architecture prematurely.
3. Separate responsibilities.
4. Make transformations deterministic where possible.
5. Avoid hidden global state.
6. Make configuration explicit.
7. Validate assumptions.
8. Prefer reusable functions over giant scripts.
9. Keep business logic readable.
10. Document non-obvious rules.
11. Preserve raw data before transforming it.
12. Avoid unnecessary duplication between Python and SQL.
13. Use SQL for relational/analytical transformations once the SQL layer exists.
14. Keep Airflow focused on orchestration.
15. Keep Power BI primarily focused on semantic modeling, measures, and visualization.

## Instructions for Codex

Before changing code:

1. Inspect the repository.
2. Read `PROJECT_CONTEXT.md`.
3. Read `CODING_STYLE.md`.
4. Inspect relevant existing files.
5. Understand existing conventions.

When changing code:

- preserve existing behavior unless explicitly changing it
- avoid unrelated refactoring
- explain meaningful architectural changes
- update documentation when architecture changes
- add/update tests for behavior changes
- run relevant tests
- report what changed and what was validated

Do not implement roadmap items merely because they appear here. The user's explicit current request takes precedence.

## Current Priority

1. Stable Bronze extraction
2. Stable Silver transformations
3. Automated tests
4. Portfolio-safe sample data
5. SQL / Gold layer
6. PostgreSQL
7. Local Airflow
8. Docker/local reproducibility
9. VM-hosted Airflow
10. Power BI integration and refresh strategy
11. Optional application layer

Build each stage only when the previous stage is sufficiently stable.
