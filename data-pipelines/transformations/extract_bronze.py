# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: base
#     language: python
#     name: python3
# ---

# %% [markdown]
#
# ## 1. Setup
#
# Extract the source tables from the current Google Sheets export and persist
# them as raw CSV files.
#
# This script represents the **Bronze layer** of the medallion architecture.
#
# Current source:
#
#     Google Sheets -> Excel export -> Bronze CSV
#
# Later, the Excel input can be replaced by the Google Sheets API without
# changing the downstream Silver transformation script.

# %% [markdown]
# ### 1.1 Paramaters

# %%
from pathlib import Path

import pandas as pd


# Pipeline paths
EXECUTION_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)
PIPELINES_DIR = next(
    candidate
    for directory in (EXECUTION_DIR, *EXECUTION_DIR.parents)
    for candidate in (directory, directory / "data-pipelines")
    if (candidate / "landing").is_dir()
)
INPUT_FILE = PIPELINES_DIR / "landing" / "expenses-tracker-potencial.xlsx"
BRONZE_DIR = PIPELINES_DIR / "database" / "bronze"

SOURCE_SHEETS = ["Trips", "Travelers", "Expenses", "Payments"]
print(INPUT_FILE)
print(BRONZE_DIR)


# %% [markdown]
# ### 1.2 Source configuration
#
# The workbook currently contains a title row before the actual table header,
# so the second row (`header=1`) is used when reading each sheet.
#
# The Bronze layer should preserve the source data as closely as possible.
# Business transformations belong in the Silver layer.

# %%
def read_source_table(
    input_file: Path,
    sheet_name: str,
) -> pd.DataFrame:
    """Read one source table from the exported workbook."""
    if not input_file.exists():
        raise FileNotFoundError(f"Source file not found: {input_file}")

    return pd.read_excel(
        input_file,
        sheet_name=sheet_name,
        header=1,
    )


# %% [markdown]
# ## 2. Data Sources
#
# The source system currently consists of four Google Sheets tables:
#
# - `Trips`
# - `Travelers`
# - `Expenses`
# - `Payments`
#
# No derived tables are created here.

# %% [markdown]
# ### 2.1 Source Definition

# %%
source_tables = {}

for sheet_name in SOURCE_SHEETS:
    source_tables[sheet_name] = read_source_table(
        INPUT_FILE,
        sheet_name,
    )

    print(
        f"{sheet_name}: "
        f"{source_tables[sheet_name].shape[0]} rows x "
        f"{source_tables[sheet_name].shape[1]} columns"
    )

# %% [markdown]
# ### 2.2 Source inspection
#
# Inspect the raw tables before writing them.
#
# This is useful during development because the Bronze layer is our record of
# what arrived from the source system.

# %%
for sheet_name, df in source_tables.items():
    print(f"\n--- {sheet_name} ---")
    print("Columns:", list(df.columns))
    display(df.head())


# %% [markdown]
# ## 3. Transformations
#
# There are intentionally **no business transformations** in the Bronze
# extraction.
#
# We only remove completely empty rows/columns that can be introduced by the
# spreadsheet export. The actual business logic is handled by the Silver
# transformation script.

# %%
def remove_empty_structure(df: pd.DataFrame) -> pd.DataFrame:
    """Remove completely empty rows and columns from the export."""
    return df.dropna(axis=0, how="all").dropna(axis=1, how="all").copy()


bronze_tables = {
    name: remove_empty_structure(df)
    for name, df in source_tables.items()
}

# %% [markdown]
# ## 4. Validations
#
# Bronze validation is intentionally lightweight.
#
# We validate that all expected source tables exist and contain data, but we
# do not enforce business rules here. Bronze should reflect the source, even
# when the source contains data that later needs to be rejected or corrected.

# %%
assert set(bronze_tables) == set(SOURCE_SHEETS)

for sheet_name, df in bronze_tables.items():
    assert not df.empty, f"{sheet_name} is empty."

print("Bronze source validation passed.")


# %% [markdown]
# ## 5. Data Writing
#
# Write one CSV per source table.
#
# Output:
#
#     bronze/
#     ├── trips.csv
#     ├── travelers.csv
#     ├── expenses.csv
#     └── payments.csv

# %%
def write_bronze_tables(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Persist source tables as Bronze CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in tables.items():
        output_file = output_dir / f"{name.lower()}.csv"
        df.to_csv(output_file, index=False)
        print(f"Wrote {output_file}")


write_bronze_tables(bronze_tables, BRONZE_DIR)

print("\nBronze extraction completed successfully.")
