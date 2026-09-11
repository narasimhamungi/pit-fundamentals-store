from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator

from airflow import DAG


def run():
    from pit_fundamentals_store.orchestration import new_filing_poll

    new_filing_poll()


with DAG(
    "pit_fundamentals_new_filing_poll",
    start_date=datetime(2026, 1, 1),
    schedule=timedelta(hours=6),
    catchup=False,
    default_args={"retries": 2},
) as dag:
    PythonOperator(task_id="poll_parse_map_validate_load", python_callable=run)
