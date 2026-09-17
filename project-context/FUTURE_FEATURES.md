# Future Features

This document records the next planned capabilities for the Trip Expense
Management project. They are intentionally deferred until the current
Bronze-to-Gold CSV pipeline remains stable.

## 1. Replace CSV storage with a database

Move Bronze, Silver, and Gold storage from local CSV files to a relational
database while preserving the current table names, keys, and SQL models.

Investigate two deployment paths:

- Local replication using Docker Compose and PostgreSQL, so contributors can
  run the complete stack on their own computer.
- A managed cloud database, selected based on cost, free-tier availability,
  security, and compatibility with Power BI refresh.

The Gold SQL layer should require only minimal changes because DuckDB SQL is
already used to build the reporting tables.

## 2. Create a portfolio-safe mock-data version

Maintain two configurations of the same pipeline:

- **Personal version:** uses real trip and expense data for personal tracking.
- **Portfolio version:** uses generated, representative data that preserves
  the schema, business rules, and reporting behavior without exposing real
  financial details, locations, trips, or identities.

The mock-data process should replace traveler names with fictional identities
and generate believable trips, expenses, payment activity, and shared-expense
allocations. The public repository must contain only the portfolio-safe data.

## 3. Read source data from Google Sheets

Replace the current local Excel-export input with a Google Sheets integration.

The extraction layer should authenticate securely, read the expected source
sheets, and write the same Bronze CSV structure currently produced by
`extract_bronze.py`. This keeps downstream Silver and Gold transformations
independent of the source-access mechanism.

Credentials must be stored outside the repository, using environment variables
and a local `.env` file that remains ignored by Git.

## 4. Add a project GitHub Pages site

Create a lightweight public project page that includes:

- A clear project overview and architecture diagram.
- The technologies and data-modeling decisions used in the project.
- A link or embedded view of the public Power BI report.
- A link to the repository and setup instructions.

The page should use portfolio-safe data only and provide a clean URL for
sharing the project.

## Suggested implementation order

1. Create and validate the portfolio-safe mock dataset.
2. Add the GitHub Pages project site and public Power BI report.
3. Integrate Google Sheets as the Bronze source.
4. Add a local PostgreSQL/Docker Compose implementation.
5. Evaluate and adopt a cloud database when hosting and refresh requirements
   are defined.
