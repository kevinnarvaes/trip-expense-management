# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
# ---

# %% [markdown]
# ## Gold layer
#
# Build reporting-ready dimensions and facts from Silver CSVs. DuckDB reads
# the files locally and executes the checked-in SQL models.

# %%
from pathlib import Path

import duckdb


EXECUTION_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
PIPELINES_DIR = next(
    candidate
    for directory in (EXECUTION_DIR, *EXECUTION_DIR.parents)
    for candidate in (directory, directory / "data-pipelines")
    if (candidate / "database" / "silver").is_dir()
)
SILVER_DIR = PIPELINES_DIR / "database" / "silver"
GOLD_DIR = PIPELINES_DIR / "database" / "gold"
SQL_DIR = EXECUTION_DIR / "sql" / "gold"


# %%
def create_silver_views(connection: duckdb.DuckDBPyConnection) -> None:
    """Expose each Silver CSV to SQL through a stable view name."""
    table_names = ["trips", "travelers", "expenses", "payments", "trip_travelers"]
    for table_name in table_names:
        csv_path = (SILVER_DIR / f"{table_name}.csv").as_posix()
        connection.execute(
            f"CREATE OR REPLACE VIEW silver_{table_name} AS "
            f"SELECT * FROM read_csv_auto('{csv_path}')"
        )


def run_sql_model(connection: duckdb.DuckDBPyConnection, filename: str) -> None:
    """Execute one checked-in Gold SQL model."""
    sql_path = SQL_DIR / filename
    if not sql_path.exists():
        raise FileNotFoundError(f"Gold SQL model not found: {sql_path}")
    connection.execute(sql_path.read_text(encoding="utf-8"))


# %% [markdown]
# ## Create dimensions and facts from SQL models

# %%
connection = duckdb.connect()
create_silver_views(connection)

for model in [
    "dim_travelers.sql",
    "dim_trips.sql",
    "fact_expense_shares.sql",
    "fact_payments.sql",
    "fact_balances.sql",
]:
    run_sql_model(connection, model)


# %% [markdown]
# ## Validate and write Gold CSVs

# %%
total_net_balance_lps, balance_row_count = connection.execute(
    """
    SELECT
        SUM(net_balance_lps) AS total_net_balance_lps,
        COUNT(*) AS balance_row_count
    FROM fact_balances
    """
).fetchone()
max_share_difference_lps = connection.execute(
    """
    SELECT
        MAX(ABS(share_total_lps - expense_amount_lps))
    FROM (
        SELECT
            expense_id,
            SUM(share_lps) AS share_total_lps,
            MAX(expense_amount_lps) AS expense_amount_lps
        FROM fact_expense_shares
        GROUP BY expense_id
    )
    """
).fetchone()[0]

assert abs(total_net_balance_lps or 0) < 0.01, "Gold balances do not reconcile."
assert balance_row_count > 0, "Gold balance fact is empty."
assert abs(max_share_difference_lps or 0) < 0.01, "Expense shares do not reconcile."

GOLD_DIR.mkdir(parents=True, exist_ok=True)
for table_name in [
    "dim_travelers",
    "dim_trips",
    "fact_expense_shares",
    "fact_payments",
    "fact_balances",
]:
    output_path = (GOLD_DIR / f"{table_name}.csv").as_posix()
    connection.execute(f"COPY {table_name} TO '{output_path}' (HEADER, DELIMITER ',')")
    print(f"Wrote {output_path}")

connection.close()
print("Gold transformation completed successfully.")
