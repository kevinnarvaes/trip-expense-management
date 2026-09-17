# CODING_STYLE.md

## 1. General

Write code that is:

- clear
- explicit
- maintainable
- reasonably concise
- easy to inspect
- easy to test
- appropriate for a technical portfolio

Prefer readability over cleverness. Avoid code golf and unnecessary abstraction.

## 2. Python

Python is the primary language.

Use modern, idiomatic Python.

Prefer:

```python
from pathlib import Path
```

over manual filesystem string concatenation.

Use type hints for functions when practical.

Example:

```python
def create_expense_shares(
    expenses: pd.DataFrame,
    travelers: pd.DataFrame,
) -> pd.DataFrame:
    """Create one share record per responsible traveler."""
```

## 3. Naming

Use `snake_case` for variables, functions, and modules.

Use PascalCase for classes if classes become necessary.

Prefer descriptive names such as:

```python
participant_count
amount_lps
expense_shares
```

over vague names when precision matters.

## 4. Functions

Give functions one clear responsibility.

Prefer:

```python
read_bronze_table()
create_expense_shares()
create_balances()
write_silver_tables()
```

over one giant `main()` function.

Functions should have clear inputs and outputs and avoid hidden side effects.

Do not create abstractions merely for the sake of abstraction.

## 5. Comments

Comments should explain **why**, not merely repeat **what**.

Bad:

```python
# Loop through expenses
for expense in expenses:
```

Good:

```python
# Expand "Todos" into one row per real traveler because the source uses
# "Todos" as a human-friendly shorthand rather than a real participant.
```

Use comments for business rules, assumptions, and non-obvious implementation choices.

Do not comment every line.

## 6. Docstrings

Reusable functions should have concise docstrings explaining their purpose.

Do not write enormous docstrings for trivial functions.

## 7. Pandas

Pandas is appropriate for the current CSV implementation.

Prefer readable transformations with meaningful intermediate variables.

Good:

```python
paid = (
    expenses.groupby(["Trip ID", "Lander"])["Monto LPS"]
    .sum()
    .rename("Paid LPS")
    .reset_index()
)
```

Avoid unnecessarily compressed expressions.

## 8. Data Types and Money

Be explicit about types when correctness depends on them.

Use:

```python
pd.to_numeric(series, errors="coerce")
```

when appropriate.

Keep currencies explicit:

```text
amount_lps
amount_usd
share_lps
share_usd
```

When production database storage is introduced, prefer exact numeric/decimal types for monetary values.

## 9. Paths

Use `pathlib.Path`.

Prefer:

```python
OUTPUT_DIR / "expenses.csv"
```

over string concatenation.

Centralize input/output configuration.

Do not scatter hard-coded paths throughout the project.

## 10. Configuration and Secrets

Never commit:

- API keys
- passwords
- tokens
- service-account credentials
- private connection strings
- real personal expense data

Use environment variables and a local `.env` file when needed.

Keep `.env` ignored.

Provide `.env.example` when environment variables are introduced.

## 11. Error Handling

Fail loudly when important business rules are violated.

Prefer specific errors:

```python
raise ValueError(
    f"Expense {expense_id} references unknown debtor '{debtor}'."
)
```

Never silently ignore important failures.

Avoid:

```python
except Exception:
    pass
```

Handle expected recoverable cases explicitly.

## 12. Validation

Validation should be explicit and meaningful.

Good:

```python
assert travelers["ID"].is_unique, "Traveler IDs must be unique."
```

Messages should explain what failed and identify the affected record where possible.

## 13. Jupyter-Compatible Python

Pipeline scripts should use `# %%` cells when they are intended to work as notebooks.

Example:

```python
# %% [markdown]
# 1. Setup

# %%
from pathlib import Path
```

Use Markdown cells for:

- purpose
- architecture
- business rules
- transformation explanations
- validation explanations
- output descriptions

Do not maintain duplicate `.py` and `.ipynb` files unless there is a specific reason.

## 14. Script Organization

Pipeline scripts should generally follow:

```text
1. Setup

1.1 Configuration
1.2 Utility functions

2. Data Sources

2.1 Read source
2.2 Inspect source

3. Transformations

3.1 ...
3.2 ...

4. Validations

4.1 ...
4.2 ...

5. Data Writing

5.1 ...
5.2 ...
```

Use Markdown cells for numbered sections and subsections.

This is both executable documentation and portfolio documentation.

## 15. SQL Style

When SQL is introduced, use uppercase SQL keywords.

```sql
SELECT
    trip_id,
    traveler_id,
    SUM(amount_lps) AS total_amount_lps
FROM fact_expenses
GROUP BY
    trip_id,
    traveler_id;
```

Put selected columns on separate lines.

Use descriptive CTE names:

```sql
WITH expense_totals AS (
    ...
),
traveler_balances AS (
    ...
)
SELECT
    ...
```

Use explicit joins:

```sql
FROM expenses AS e
INNER JOIN travelers AS t
    ON e.traveler_id = t.traveler_id
```

Document complex business logic with SQL comments.

## 16. Python vs SQL Responsibilities

Avoid duplicating the same transformation logic in Python and SQL.

### Python

Prefer for:

- source extraction
- API interaction
- file handling
- source normalization
- procedural transformations
- pipeline validation
- external-system interfaces

### SQL

Prefer for:

- joins
- relational transformations
- aggregations
- warehouse modeling
- analytical datasets
- Gold-layer transformations

### Airflow

Prefer for:

- scheduling
- dependencies
- retries
- orchestration
- task execution

Do not put complex business transformations directly into DAG definitions.

## 17. Airflow Style

When Airflow is introduced, DAG files should primarily describe orchestration.

Conceptually:

```text
extract
   ↓
transform
   ↓
load
   ↓
validate
```

Reusable Python/SQL code should contain actual data logic.

The DAG should answer:

> What runs, in what order, and when?

The transformation code should answer:

> What happens to the data?

## 18. Testing

Tests should focus on behavior and business rules.

Prioritize:

- `Todos` expands to all real travelers
- a specific debtor receives the full expense
- unknown debtors fail
- unknown trips fail
- expense shares reconcile
- trip balances reconcile
- identifiers are unique

Use small deterministic fixtures.

## 19. Documentation

Documentation should be:

- direct
- technical
- structured
- honest about implementation status
- explicit about trade-offs

Avoid marketing language and exaggerated claims.

Prefer:

> The current implementation uses CSV files to simulate Bronze and Silver storage. PostgreSQL is planned for a later iteration.

## 20. Markdown

Use:

- clear headings
- short paragraphs
- tables for comparisons
- code blocks for examples
- diagrams when they clarify architecture

For simple architecture:

```text
Google Sheets
     ↓
Bronze
     ↓
Silver
     ↓
Gold
     ↓
Power BI
```

Keep documentation useful rather than decorative.

## 21. Commit Messages

Use concise, descriptive commit messages.

Preferred:

```text
Add bronze extraction pipeline
Add silver expense transformations
Add expense reconciliation tests
Add initial gold SQL model
Add Airflow pipeline DAG
```

Avoid:

```text
stuff
changes
update
final
final final
```

The Git history should communicate how the project evolved.

## 22. Refactoring

Do not refactor unrelated code during a feature change.

If refactoring is necessary:

1. Explain why.
2. Keep the scope focused.
3. Preserve behavior.
4. Run tests.

## 23. Dependencies

Do not add packages when the standard library or an existing dependency is sufficient.

Before adding a dependency, consider:

- Does it solve a real problem?
- Is it maintained?
- Is it necessary?
- Does it improve reproducibility?

Keep `requirements.txt` understandable.

## 24. Portfolio Principle

A reviewer should be able to trace:

```text
source
  ↓
extraction
  ↓
bronze
  ↓
transformation
  ↓
silver
  ↓
SQL
  ↓
gold
  ↓
BI
```

The repository should demonstrate engineering decisions, not merely the use of many technologies.

## 25. Final Rule

When multiple approaches are valid, prefer the one that is:

1. simpler
2. clearer
3. easier to test
4. easier to explain
5. easier to replace later

Optimize for demonstrable engineering quality, not architectural complexity.
