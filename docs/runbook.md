# Runbook

1. Copy `.env.example` to `.env`.
2. Set a descriptive SEC User-Agent.
3. Start PostgreSQL and Airflow with Docker Compose.
4. Run a small AAPL ingestion first.
5. Inspect `logs/pit_fundamentals_store.log`.
6. Run unit/property/regression tests.
7. Run the AAPL PIT demonstration.
8. Scale the CIK universe only after the small path is verified.
