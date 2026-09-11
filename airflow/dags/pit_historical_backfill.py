from datetime import datetime

from airflow.operators.python import PythonOperator

from airflow import DAG


def run():
    from pit_fundamentals_store.orchestration import historical_backfill

    historical_backfill()


with DAG(
    "pit_fundamentals_historical_backfill",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sec", "xbrl", "bitemporal"],
) as dag:
    PythonOperator(task_id="discover_parse_map_validate_load", python_callable=run)
