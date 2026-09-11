# Troubleshooting

## PostgreSQL
`docker compose ps` and `docker compose logs postgres`.

## Airflow
`docker compose logs airflow-init`, `docker compose logs airflow-scheduler`.

## SEC
Verify a descriptive `SEC_USER_AGENT`, outbound HTTPS, and the configured delay.

## Arelle
`pip install -e ".[xbrl]"` then validate an instance with `pit_fundamentals_store.arelle_adapter.validate_instance`.

## Tests
`pytest tests/test_core.py -q`; database integration is opt-in with `RUN_DB_INTEGRATION=1`.

## Logs
`logs/pit_fundamentals_store.log`.
