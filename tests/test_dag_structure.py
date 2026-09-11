"""
DAG structure tests using Airflow's real DagBag — loaded the same way the
scheduler would load them, so a broken import or a renamed callable fails
here rather than silently at runtime in the container.

Skipped gracefully if apache-airflow isn't installed. It deliberately is
not part of the default test extra: Airflow's bundled providers pin
transitive dependencies that conflict with this project's own pins, so it
runs as a separate isolated CI job (see .github/workflows/ci.yml) rather
than alongside the main suite.
"""
import os
from pathlib import Path

import pytest

pytest.importorskip("airflow")

os.environ.setdefault("AIRFLOW_HOME", "/tmp/airflow_pit_test_home")
Path(os.environ["AIRFLOW_HOME"]).mkdir(parents=True, exist_ok=True)

from airflow.models import DagBag  # noqa: E402

DAG_FOLDER = str(Path(__file__).resolve().parents[1] / "airflow" / "dags")

EXPECTED_DAGS = {
    "pit_fundamentals_historical_backfill": "discover_parse_map_validate_load",
    "pit_fundamentals_new_filing_poll": "poll_parse_map_validate_load",
}


@pytest.fixture(scope="module")
def dag_bag():
    return DagBag(dag_folder=DAG_FOLDER, include_examples=False)


def test_dag_folder_has_no_import_errors(dag_bag):
    assert dag_bag.import_errors == {}


def test_expected_dags_are_present(dag_bag):
    assert set(EXPECTED_DAGS) <= set(dag_bag.dags)


@pytest.mark.parametrize("dag_id,task_id", sorted(EXPECTED_DAGS.items()))
def test_each_dag_has_its_expected_task(dag_bag, dag_id, task_id):
    dag = dag_bag.dags[dag_id]
    assert [t.task_id for t in dag.tasks] == [task_id]


def test_backfill_dag_is_manual_trigger_only(dag_bag):
    """A full historical backfill hits SEC EDGAR hard and should never fire
    on a timer by accident."""
    assert dag_bag.dags["pit_fundamentals_historical_backfill"].schedule_interval is None


def test_poll_dag_is_scheduled_and_retries(dag_bag):
    dag = dag_bag.dags["pit_fundamentals_new_filing_poll"]
    assert dag.schedule_interval is not None
    assert dag.default_args.get("retries", 0) >= 1


def test_dag_callables_reference_real_orchestration_functions(dag_bag):
    """DagBag parsing alone won't catch a renamed orchestration function,
    because the DAG modules import them lazily inside the task callable.
    This asserts the names actually exist."""
    from pit_fundamentals_store import orchestration

    assert callable(orchestration.historical_backfill)
    assert callable(orchestration.new_filing_poll)
