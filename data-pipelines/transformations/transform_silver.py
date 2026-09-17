# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
# ---

# %% [markdown]
# ## Silver layer
#
# Clean and standardize Bronze CSVs into relational source tables for the
# Gold SQL layer. This layer preserves expense-level transactions; allocation
# of `Todos` and all reporting calculations happen in Gold.

# %%
from pathlib import Path
import re

import pandas as pd


try:
    from IPython.display import display
except ImportError:
    def display(value: object) -> None:
        """Print notebook previews when IPython is unavailable."""
        print(value)


EXECUTION_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
PIPELINES_DIR = next(
    candidate
    for directory in (EXECUTION_DIR, *EXECUTION_DIR.parents)
    for candidate in (directory, directory / "data-pipelines")
    if (candidate / "landing").is_dir()
)
BRONZE_DIR = PIPELINES_DIR / "database" / "bronze"
SILVER_DIR = PIPELINES_DIR / "database" / "silver"


# %%
def to_snake_case(column_name: object) -> str:
    """Convert a source column header to a lowercase snake_case name."""
    name = str(column_name).strip()
    name = name.replace("?", "_flag").replace("%", "_percent")
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    return re.sub(r"_+", "_", name).strip("_").lower()


def read_bronze_table(table_name: str) -> pd.DataFrame:
    """Read and structurally clean one Bronze CSV table."""
    path = BRONZE_DIR / f"{table_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Bronze table not found: {path}")

    dataframe = pd.read_csv(path).dropna(axis=0, how="all").dropna(axis=1, how="all")
    dataframe.columns = [to_snake_case(column) for column in dataframe.columns]
    return dataframe.copy()


def clean_text_columns(dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Trim text values while preserving missing values."""
    cleaned = dataframe.copy()
    for column in columns:
        cleaned[column] = cleaned[column].astype("string").str.strip()
    return cleaned


def add_sequential_id(
    dataframe: pd.DataFrame,
    id_column: str,
    prefix: str,
) -> pd.DataFrame:
    """Add a deterministic technical key when the source does not provide one."""
    with_id = dataframe.copy()
    if id_column not in with_id:
        with_id.insert(
            0,
            id_column,
            [f"{prefix}{index:04d}" for index in range(1, len(with_id) + 1)],
        )
    return with_id


def assert_foreign_keys(
    dataframe: pd.DataFrame,
    column: str,
    valid_ids: set[str],
    table_name: str,
    required: bool = True,
) -> None:
    """Validate a logical CSV foreign key against its referenced IDs."""
    values = dataframe[column].dropna().astype(str)
    unknown_ids = set(values) - valid_ids
    assert not unknown_ids, (
        f"{table_name}.{column} references unknown IDs: "
        + ", ".join(sorted(unknown_ids))
    )
    if required:
        assert dataframe[column].notna().all(), f"{table_name}.{column} must not contain null values."


# %% [markdown]
# ## Read, clean, and resolve relationship keys
#
# `Todos` is a source shorthand for a shared expense, not a traveler. Its
# nullable `debtor_traveler_id` is intentional; `is_shared_expense` describes
# that business rule. Gold expands shared expenses across trip participants.

# %%
trips = read_bronze_table("trips").rename(columns={"id": "trip_id"})
travelers = read_bronze_table("travelers").rename(columns={"id": "traveler_id"})
expenses = read_bronze_table("expenses")
payments = read_bronze_table("payments")

trips = clean_text_columns(trips, ["trip_id", "trip", "destination"])
travelers = clean_text_columns(travelers, ["traveler_id", "traveler"])
expenses = clean_text_columns(expenses, ["trip_id", "debtor", "lander"])
payments = clean_text_columns(payments, ["trip_id", "debtor", "lander"])

expenses = add_sequential_id(expenses, "expense_id", "E")
payments = add_sequential_id(payments, "payment_id", "P")

real_travelers = travelers.loc[travelers["traveler"].str.casefold() != "todos"].copy()
traveler_lookup = (
    real_travelers.assign(traveler_key=real_travelers["traveler"].str.casefold())
    .set_index("traveler_key")["traveler_id"]
)


def resolve_traveler_id(name: object) -> object:
    """Return the traveler ID for a source name, or missing for `Todos`."""
    if pd.isna(name) or str(name).casefold() == "todos":
        return pd.NA
    return traveler_lookup.get(str(name).casefold(), pd.NA)


for table in (expenses, payments):
    table["lender_traveler_id"] = table["lander"].map(resolve_traveler_id)
    table["debtor_traveler_id"] = table["debtor"].map(resolve_traveler_id)

expenses["is_shared_expense"] = expenses["debtor"].str.casefold().eq("todos")
expenses = expenses.drop(columns=["debtor", "lander"])
payments = payments.drop(columns=["debtor", "lander"])

for table in (expenses, payments):
    for column in ("monto", "monto_lps", "monto_usd", "rate"):
        if column in table:
            table[column] = pd.to_numeric(table[column], errors="coerce")

expenses = expenses.rename(columns={
    "date": "expense_date", "type": "expense_type", "rate": "exchange_rate",
    "monto": "amount_original", "monto_lps": "amount_lps", "monto_usd": "amount_usd",
})
payments = payments.rename(columns={
    "rate": "exchange_rate", "monto": "amount_original",
    "monto_lps": "amount_lps", "monto_usd": "amount_usd",
})


# %% [markdown]
# ## Derive trip participation
#
# The source has no trip-registration table. A traveler is therefore treated
# as a participant when they appear as a payer or specific debtor in an
# expense or payment. This bridge determines who receives a `Todos` share.

# %%
trip_traveler_pairs = pd.concat(
    [
        expenses[["trip_id", "lender_traveler_id"]].rename(columns={"lender_traveler_id": "traveler_id"}),
        expenses[["trip_id", "debtor_traveler_id"]].rename(columns={"debtor_traveler_id": "traveler_id"}),
        payments[["trip_id", "lender_traveler_id"]].rename(columns={"lender_traveler_id": "traveler_id"}),
        payments[["trip_id", "debtor_traveler_id"]].rename(columns={"debtor_traveler_id": "traveler_id"}),
    ],
    ignore_index=True,
).dropna().drop_duplicates().sort_values(["trip_id", "traveler_id"])

trip_travelers = trip_traveler_pairs.reset_index(drop=True)
trip_travelers.insert(0, "trip_traveler_id", [f"TT{index:04d}" for index in range(1, len(trip_travelers) + 1)])


# %% [markdown]
# ## Validate Silver relationships

# %%
assert trips["trip_id"].is_unique, "Trip IDs must be unique."
assert travelers["traveler_id"].is_unique, "Traveler IDs must be unique."
assert expenses["expense_id"].is_unique, "Expense IDs must be unique."
assert payments["payment_id"].is_unique, "Payment IDs must be unique."
assert trip_travelers["trip_traveler_id"].is_unique, "Trip traveler IDs must be unique."
assert not real_travelers.empty, "At least one real traveler is required."

trip_ids = set(trips["trip_id"])
traveler_ids = set(real_travelers["traveler_id"])
for table_name, table in {"expenses": expenses, "payments": payments}.items():
    assert_foreign_keys(table, "trip_id", trip_ids, table_name)
    assert_foreign_keys(table, "lender_traveler_id", traveler_ids, table_name)
    assert_foreign_keys(table, "debtor_traveler_id", traveler_ids, table_name, required=False)

unresolved_specific_debtors = expenses.loc[
    ~expenses["is_shared_expense"] & expenses["debtor_traveler_id"].isna()
]
assert unresolved_specific_debtors.empty, "Specific expense debtors must resolve to a traveler ID."
assert_foreign_keys(trip_travelers, "trip_id", trip_ids, "trip_travelers")
assert_foreign_keys(trip_travelers, "traveler_id", traveler_ids, "trip_travelers")
assert not trip_travelers.duplicated(["trip_id", "traveler_id"]).any(), "A traveler can appear only once per trip."

print("Silver relational validations passed.")


# %% [markdown]
# ## Write Silver CSVs

# %%
SILVER_DIR.mkdir(parents=True, exist_ok=True)
silver_tables = {
    "trips.csv": trips,
    "travelers.csv": real_travelers,
    "expenses.csv": expenses,
    "payments.csv": payments,
    "trip_travelers.csv": trip_travelers,
}

for filename, dataframe in silver_tables.items():
    output_file = SILVER_DIR / filename
    dataframe.to_csv(output_file, index=False)
    print(f"Wrote {output_file}")

print("Silver transformation completed successfully.")
