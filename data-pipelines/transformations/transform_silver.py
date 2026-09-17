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
# ## 1. Setup
#
# Transform the raw Bronze CSVs into cleaned and derived Silver datasets.
#
# This script represents the **Silver layer** of the medallion architecture.
#
# Pipeline:
#
#     Bronze CSVs -> Python transformations -> Silver CSVs
#
# The source model remains intentionally simple:
#
# - Trips
# - Travelers
# - Expenses
# - Payments
#
# Derived concepts such as expense shares and balances are generated here
# rather than maintained manually in the source spreadsheet.

# %% [markdown]
# ### 1.1 Paramaters

# %%
from pathlib import Path
import re

import pandas as pd


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
BRONZE_DIR = PIPELINES_DIR / "database" / "bronze"
SILVER_DIR = PIPELINES_DIR / "database" / "silver"


# %% [markdown]
# ### 1.2 Utility functions
#
# Keep file reading separate from transformation logic. This makes the
# eventual migration from CSVs to PostgreSQL much easier.

# %%
def to_snake_case(column_name: object) -> str:
    """Convert a source column header to a lowercase snake_case name."""
    name = str(column_name).strip()
    name = name.replace("?", "_flag").replace("%", "_percent")
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    return re.sub(r"_+", "_", name).strip("_").lower()


def read_bronze_table(
    bronze_dir: Path,
    table_name: str,
) -> pd.DataFrame:
    """Read a Bronze CSV table."""
    path = bronze_dir / f"{table_name}.csv"

    if not path.exists():
        raise FileNotFoundError(f"Bronze table not found: {path}")

    dataframe = pd.read_csv(path)
    dataframe.columns = [to_snake_case(column) for column in dataframe.columns]
    return dataframe


# %% [markdown]
# ## 2. Data Sources
#
# The inputs to this layer are the raw CSV files produced by the extraction
# script.

# %% [markdown]
# ### 2.1 Source Definitions

# %%
trips = read_bronze_table(BRONZE_DIR, "trips")
travelers = read_bronze_table(BRONZE_DIR, "travelers")
expenses = read_bronze_table(BRONZE_DIR, "expenses")
payments = read_bronze_table(BRONZE_DIR, "payments")

print("Trips:", trips.shape)
print("Travelers:", travelers.shape)
print("Expenses:", expenses.shape)
print("Payments:", payments.shape)


# %% [markdown]
# ### 2.2 Clean source structure
#
# Normalize column names and identifiers before applying business rules.
# This is the first point at which the source data is intentionally changed.

# %%
def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and remove completely empty rows/columns."""
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all").copy()
    return df


trips = clean_dataframe(trips)
travelers = clean_dataframe(travelers)
expenses = clean_dataframe(expenses)
payments = clean_dataframe(payments)

trips["id"] = trips["id"].astype(str).str.strip()

travelers["id"] = travelers["id"].astype(str).str.strip()
travelers["traveler"] = travelers["traveler"].astype(str).str.strip()

expenses["trip_id"] = expenses["trip_id"].astype(str).str.strip()
expenses["debtor"] = expenses["debtor"].astype(str).str.strip()
expenses["lander"] = expenses["lander"].astype(str).str.strip()

payments["trip_id"] = payments["trip_id"].astype(str).str.strip()
payments["debtor"] = payments["debtor"].astype(str).str.strip()
payments["lander"] = payments["lander"].astype(str).str.strip()

# %% [markdown]
# ## 3. Transformations

# %% [markdown]
# ### 3.1 Create technical expense identifiers
#
# The source spreadsheet does not need to expose a technical expense ID to
# the person entering expenses. The Silver layer creates one for downstream
# processing.

# %%
expenses = expenses.copy()

if "expense_id" not in expenses.columns:
    expenses.insert(
        0,
        "expense_id",
        [f"E{i:04d}" for i in range(1, len(expenses) + 1)],
    )

# %% [markdown]
# ### 3.2 Identify real travelers
#
# `Todos` is a special source value meaning "all travelers", not an actual
# traveler.
#
# It is therefore excluded from the Silver traveler dimension used for
# expense-share calculations.

# %%
real_travelers = travelers[
    travelers["traveler"].str.casefold() != "todos"
].copy()

real_traveler_names = set(
    real_travelers["traveler"].str.casefold()
)

print(f"Real travelers: {len(real_travelers)}")

# %% [markdown]
# ### 3.3 Validate expense participants
#
# Every specific debtor must correspond to a real traveler.
# `Todos` is explicitly permitted.

# %%
specific_debtors = set(
    expenses.loc[
        expenses["debtor"].str.casefold() != "todos",
        "debtor",
    ].str.casefold()
)

unknown_debtors = specific_debtors - real_traveler_names

if unknown_debtors:
    raise ValueError(
        "The following debtors do not exist in Travelers: "
        + ", ".join(sorted(unknown_debtors))
    )


# %% [markdown]
# ### 3.4 Create expense shares
#
# Business rule:
#
# - A specific `Debtor` receives 100% of the expense as their share.
# - `Todos` divides the expense equally among the real travelers who
#   participated in that expense's trip.
#
# This creates the normalized association between an expense and the people
# responsible for it.

# %%
def get_trip_participants(
    expenses: pd.DataFrame,
    real_travelers: pd.DataFrame,
    trip_id: str,
) -> pd.DataFrame:
    """Return real travelers named in the expenses for a given trip."""
    trip_expenses = expenses.loc[expenses["trip_id"] == trip_id]
    participant_names = {
        name.casefold()
        for name in trip_expenses[["debtor", "lander"]].to_numpy().flatten()
        if name.casefold() != "todos"
    }

    return real_travelers.loc[
        real_travelers["traveler"].str.casefold().isin(participant_names)
    ].copy()


def create_expense_shares(
    expenses: pd.DataFrame,
    travelers: pd.DataFrame,
) -> pd.DataFrame:
    """Expand each expense into one row per responsible traveler."""
    real_travelers = travelers[
        travelers["traveler"].str.casefold() != "todos"
    ].copy()

    share_rows = []

    for _, expense in expenses.iterrows():
        expense_id = expense["expense_id"]
        trip_id = str(expense["trip_id"]).strip()
        debtor = str(expense["debtor"]).strip()

        amount_lps = pd.to_numeric(
            expense["monto_lps"],
            errors="coerce",
        )
        amount_usd = pd.to_numeric(
            expense["monto_usd"],
            errors="coerce",
        )

        if debtor.casefold() == "todos":
            participants = get_trip_participants(
                expenses,
                real_travelers,
                trip_id,
            )
        else:
            participants = real_travelers[
                real_travelers["traveler"].str.casefold()
                == debtor.casefold()
            ]

        if participants.empty:
            raise ValueError(
                f"{expense_id}: debtor '{debtor}' could not be "
                "matched to a traveler."
            )

        participant_count = len(participants)

        for _, traveler in participants.iterrows():
            share_rows.append(
                {
                    "expense_id": expense_id,
                    "trip_id": trip_id,
                    "traveler_id": traveler["id"],
                    "debtor": traveler["traveler"],
                    "lander": expense["lander"],
                    "participant_count": participant_count,
                    "share_lps": (
                        amount_lps / participant_count
                        if pd.notna(amount_lps)
                        else None
                    ),
                    "share_usd": (
                        amount_usd / participant_count
                        if pd.notna(amount_usd)
                        else None
                    ),
                }
            )

    return pd.DataFrame(share_rows)


expense_shares = create_expense_shares(
    expenses,
    travelers,
)

display(expense_shares.head(10))


# %% [markdown]
# ### 3.5 Create traveler balances
#
# For each traveler and trip:
#
#     Net Balance = Expense Amount Paid + Payments Sent
#                   - Amount Owed - Payments Received
#
# Positive values indicate that the traveler paid more than their share.
# Negative values indicate that the traveler owes more than they paid.

# %%
def create_balances(
    trips: pd.DataFrame,
    travelers: pd.DataFrame,
    expenses: pd.DataFrame,
    expense_shares: pd.DataFrame,
    payments: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate balances per traveler and trip, including payments."""
    real_travelers = travelers[
        travelers["traveler"].str.casefold() != "todos"
    ].copy()

    paid = (
        expenses.groupby(
            ["trip_id", "lander"],
            dropna=False,
        )["monto_lps"]
        .sum()
        .rename("paid_lps")
        .reset_index()
        .rename(columns={"lander": "traveler"})
    )

    owed = (
        expense_shares.groupby(
            ["trip_id", "debtor"],
            dropna=False,
        )["share_lps"]
        .sum()
        .rename("owed_lps")
        .reset_index()
        .rename(columns={"debtor": "traveler"})
    )

    payments_sent = (
        payments.groupby(["trip_id", "debtor"], dropna=False)["monto_lps"]
        .sum()
        .rename("payment_sent_lps")
        .reset_index()
        .rename(columns={"debtor": "traveler"})
    )

    payments_received = (
        payments.groupby(["trip_id", "lander"], dropna=False)["monto_lps"]
        .sum()
        .rename("payment_received_lps")
        .reset_index()
        .rename(columns={"lander": "traveler"})
    )

    # Only include travelers who participated in each trip. This prevents a
    # traveler such as Dayana, who did not attend a trip, from appearing in
    # that trip's balances.
    participant_balances = []
    for trip_id in trips["id"]:
        participants = get_trip_participants(
            expenses,
            real_travelers,
            trip_id,
        )
        participant_balances.append(
            participants.assign(trip_id=trip_id)[
                ["id", "traveler", "trip_id"]
            ]
        )

    balances = pd.concat(participant_balances, ignore_index=True)

    balances = (
        balances
        .merge(
            paid,
            on=["trip_id", "traveler"],
            how="left",
        )
        .merge(
            owed,
            on=["trip_id", "traveler"],
            how="left",
        )
        .merge(
            payments_sent,
            on=["trip_id", "traveler"],
            how="left",
        )
        .merge(
            payments_received,
            on=["trip_id", "traveler"],
            how="left",
        )
    )

    balances["paid_lps"] = balances["paid_lps"].fillna(0)
    balances["owed_lps"] = balances["owed_lps"].fillna(0)
    balances["payment_sent_lps"] = balances["payment_sent_lps"].fillna(0)
    balances["payment_received_lps"] = balances[
        "payment_received_lps"
    ].fillna(0)
    net_balance_lps = (
        balances["paid_lps"]
        + balances["payment_sent_lps"]
        - balances["owed_lps"]
        - balances["payment_received_lps"]
    )
    balances["net_balance_lps"] = net_balance_lps.where(
        net_balance_lps.abs() >= 0.01,
        0,
    )

    return balances


balances = create_balances(
    trips,
    travelers,
    expenses,
    expense_shares,
    payments,
)

display(balances.head(10))

# %% [markdown]
# ## 4. Validations
#
# Silver is where the data is expected to satisfy business and relational
# rules. Invalid data should fail loudly rather than silently enter the
# analytical layer.

# %% [markdown]
# ### 4.1 Required columns

# %%
required_columns = {
    "Trips": {"id"},
    "Travelers": {"id", "traveler"},
    "Expenses": {
        "trip_id",
        "debtor",
        "lander",
        "monto_lps",
        "monto_usd",
    },
    "Payments": {
        "trip_id",
        "debtor",
        "lander",
        "monto_lps",
        "monto_usd",
    },
}

silver_tables = {
    "Trips": trips,
    "Travelers": travelers,
    "Expenses": expenses,
    "Payments": payments,
}

for table_name, required in required_columns.items():
    actual = set(silver_tables[table_name].columns)
    missing = required - actual

    assert not missing, (
        f"{table_name} is missing required columns: {sorted(missing)}"
    )

print("Required-column validation passed.")

# %% [markdown]
# ### 4.2 Unique identifiers

# %%
assert trips["id"].is_unique, "Trip IDs must be unique."
assert travelers["id"].is_unique, "Traveler IDs must be unique."
assert expenses["expense_id"].is_unique, "Expense IDs must be unique."

print("Identifier validation passed.")

# %% [markdown]
# ### 4.3 Referential integrity

# %%
trip_ids = set(trips["id"])
traveler_names = set(
    real_travelers["traveler"].str.casefold()
)

unknown_trip_ids = set(expenses["trip_id"]) - trip_ids

assert not unknown_trip_ids, (
    "Expenses reference unknown Trip IDs: "
    + ", ".join(sorted(unknown_trip_ids))
)

unknown_payment_trip_ids = set(payments["trip_id"]) - trip_ids

assert not unknown_payment_trip_ids, (
    "Payments reference unknown Trip IDs: "
    + ", ".join(sorted(unknown_payment_trip_ids))
)

unknown_landers = (
    set(expenses["lander"].str.casefold())
    - traveler_names
)

assert not unknown_landers, (
    "Expenses reference unknown Landers: "
    + ", ".join(sorted(unknown_landers))
)

payment_people = set(payments["debtor"].str.casefold()).union(
    payments["lander"].str.casefold()
)
unknown_payment_people = payment_people - traveler_names

assert not unknown_payment_people, (
    "Payments reference unknown travelers: "
    + ", ".join(sorted(unknown_payment_people))
)

print("Referential-integrity validation passed.")

# %% [markdown]
# ### 4.4 Expense-share reconciliation
#
# For every expense:
#
#     Sum of shares = Original expense amount
#
# A cent-level tolerance is used to account for floating-point arithmetic.

# %%
expense_reconciliation = (
    expense_shares
    .groupby("expense_id", as_index=False)["share_lps"]
    .sum()
    .rename(columns={"share_lps": "calculated_lps"})
    .merge(
        expenses[["expense_id", "monto_lps"]],
        on="expense_id",
        how="left",
    )
)

expense_reconciliation["difference"] = (
    expense_reconciliation["calculated_lps"]
    - expense_reconciliation["monto_lps"]
)

assert (
    expense_reconciliation["difference"].abs() < 0.01
).all(), "Expense shares do not reconcile to source amounts."

print("Expense-share reconciliation passed.")

# %% [markdown]
# ## 5. Data Writing
#
# Write the cleaned and derived Silver datasets.
#
# Output:
#
#     silver/
#     ├── trips.csv
#     ├── travelers.csv
#     ├── expenses.csv
#     ├── payments.csv
#     ├── expense_shares.csv
#     └── balances.csv
#
# In a later iteration, this writing layer can be replaced by PostgreSQL.

# %%
def write_silver_tables(
    output_dir: Path,
    trips: pd.DataFrame,
    travelers: pd.DataFrame,
    expenses: pd.DataFrame,
    payments: pd.DataFrame,
    expense_shares: pd.DataFrame,
    balances: pd.DataFrame,
) -> None:
    """Persist Silver datasets as CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "trips.csv": trips,
        "travelers.csv": travelers,
        "expenses.csv": expenses,
        "payments.csv": payments,
        "expense_shares.csv": expense_shares,
        "balances.csv": balances,
    }

    for filename, df in outputs.items():
        output_file = output_dir / filename
        df.to_csv(output_file, index=False)
        print(f"Wrote {output_file}")


write_silver_tables(
    SILVER_DIR,
    trips,
    travelers,
    expenses,
    payments,
    expense_shares,
    balances,
)

print("\nSilver transformation completed successfully.")
