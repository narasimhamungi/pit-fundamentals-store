"""
Integration tests against a real PostgreSQL instance.

Skipped unless RUN_DB_INTEGRATION=1. These specifically cover things a
mock cannot: SQL constraint semantics, range containment, and the
NULL-handling behaviour of the unique constraint — the last of which
hid a real duplicate-insert bug that unit tests passed straight through.
"""
import os
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest


def _require_db():
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("Set RUN_DB_INTEGRATION=1")


def _aapl_fixture():
    """The AAPL FY2009 restatement: original 10-K then the 10-K/A that
    restated net income upward. period_start is None (instant-style fact),
    which is exactly the case the unique constraint must still dedupe."""
    from pit_fundamentals_store.models import FilingMetadata, NormalizedFact

    facts = [
        NormalizedFact(
            320193, "AAPL", "Apple Inc.", "net_income", "NetIncomeLoss", None,
            date(2009, 9, 26), datetime(2009, 10, 27, tzinfo=UTC),
            Decimal("5704000000"), "USD", "0001193125-09-214859", "10-K",
            "https://www.sec.gov/Archives/edgar/data/320193/000119312509214859/d10k.htm",
        ),
        NormalizedFact(
            320193, "AAPL", "Apple Inc.", "net_income", "NetIncomeLoss", None,
            date(2009, 9, 26), datetime(2010, 1, 25, tzinfo=UTC),
            Decimal("8235000000"), "USD", "0001193125-10-012091", "10-K/A",
            "https://www.sec.gov/Archives/edgar/data/320193/000119312510012091/d10ka.htm",
        ),
    ]
    filings = [
        FilingMetadata(
            320193, "AAPL", "Apple Inc.", "0001193125-09-214859", "10-K",
            date(2009, 10, 27), date(2009, 9, 26), None,
            facts[0].source_url, datetime(2009, 10, 27, tzinfo=UTC),
        ),
        FilingMetadata(
            320193, "AAPL", "Apple Inc.", "0001193125-10-012091", "10-K/A",
            date(2010, 1, 25), date(2009, 9, 26), None,
            facts[1].source_url, datetime(2010, 1, 25, tzinfo=UTC),
        ),
    ]
    return filings, facts


@pytest.fixture
def clean_facts():
    """Remove this CIK's rows before and after, so these tests are
    independent of each other and of whatever else is in the database.

    _require_db() here is load-bearing, not redundant with the check
    inside each test function: pytest resolves a fixture BEFORE the test
    body runs, so without this guard the fixture attempted a real DB
    connection regardless of RUN_DB_INTEGRATION, turning "gracefully
    skipped" into a hard connection error for anyone running the suite
    without a database configured. Confirmed against a real run."""
    _require_db()
    from pit_fundamentals_store.database import connection

    def _wipe():
        with connection() as c:
            c.execute("DELETE FROM fundamental_fact WHERE cik = 320193")
            c.execute("DELETE FROM filing WHERE cik = 320193")
            c.execute("DELETE FROM company WHERE cik = 320193")

    _wipe()
    yield
    _wipe()


@pytest.mark.integration
def test_postgres():
    _require_db()
    from pit_fundamentals_store.database import connection

    with connection() as c:
        assert c.execute("select 1").fetchone()[0] == 1


@pytest.mark.integration
def test_load_is_idempotent_with_null_period_start(clean_facts):
    """Regression test for a real bug found against live Postgres.

    period_start IS NULL for every instant fact (balance-sheet items).
    Under SQL's default NULLS DISTINCT semantics NULL != NULL, so the
    original plain UNIQUE constraint never fired for these rows and
    ON CONFLICT DO NOTHING silently inserted a duplicate on every re-run —
    turning 2 rows into 4, and doubling every point-in-time query result.
    The schema now uses UNIQUE NULLS NOT DISTINCT. If that is ever
    reverted, this test fails.
    """
    _require_db()
    from pit_fundamentals_store.database import BitemporalLoader, connection
    from pit_fundamentals_store.temporal import build_temporal_versions

    filings, facts = _aapl_fixture()
    temporal = build_temporal_versions(facts)

    first = BitemporalLoader().load(filings, temporal)
    assert first == 2

    second = BitemporalLoader().load(filings, temporal)
    assert second == 0, "re-loading identical facts must insert nothing"

    with connection() as c:
        count = c.execute(
            "SELECT count(*) FROM fundamental_fact WHERE cik = 320193"
        ).fetchone()[0]
    assert count == 2, f"expected 2 rows after two identical loads, found {count}"


@pytest.mark.integration
def test_asof_function_returns_the_value_knowable_at_that_time(clean_facts):
    """The core PIT guarantee, exercised through real SQL range containment
    rather than the Python implementation."""
    _require_db()
    from pit_fundamentals_store.database import BitemporalLoader, connection
    from pit_fundamentals_store.temporal import build_temporal_versions

    filings, facts = _aapl_fixture()
    BitemporalLoader().load(filings, build_temporal_versions(facts))

    with connection() as c:
        before = c.execute(
            "SELECT value FROM fundamentals_asof(%s,%s,%s)",
            (320193, "net_income", datetime(2009, 12, 1, tzinfo=UTC)),
        ).fetchall()
        after = c.execute(
            "SELECT value FROM fundamentals_asof(%s,%s,%s)",
            (320193, "net_income", datetime(2010, 6, 1, tzinfo=UTC)),
        ).fetchall()

    assert [r[0] for r in before] == [Decimal("5704000000")]
    assert [r[0] for r in after] == [Decimal("8235000000")]


@pytest.mark.integration
def test_knowledge_time_has_no_gap_or_overlap_at_the_restatement_boundary(clean_facts):
    """knowledge_time ranges are '[)' — half-open. At the exact instant the
    amendment was filed the new value must already apply, and exactly one
    row must match at every instant: no gap, no double-count."""
    _require_db()
    from pit_fundamentals_store.database import BitemporalLoader, connection
    from pit_fundamentals_store.temporal import build_temporal_versions

    filings, facts = _aapl_fixture()
    BitemporalLoader().load(filings, build_temporal_versions(facts))

    restatement_instant = datetime(2010, 1, 25, tzinfo=UTC)
    one_second_before = datetime(2010, 1, 24, 23, 59, 59, tzinfo=UTC)

    with connection() as c:
        at_boundary = c.execute(
            "SELECT value FROM fundamentals_asof(%s,%s,%s)",
            (320193, "net_income", restatement_instant),
        ).fetchall()
        just_before = c.execute(
            "SELECT value FROM fundamentals_asof(%s,%s,%s)",
            (320193, "net_income", one_second_before),
        ).fetchall()

    assert len(at_boundary) == 1, "exactly one version must apply at any instant"
    assert len(just_before) == 1
    assert at_boundary[0][0] == Decimal("8235000000")
    assert just_before[0][0] == Decimal("5704000000")


@pytest.mark.integration
def test_fundamentals_latest_returns_restated_not_point_in_time(clean_facts):
    """fundamentals_latest is the current-best view — it must return the
    restated figure. This is the look-ahead-biased answer by design; the
    test exists to pin the distinction from fundamentals_asof(), since the
    two previously shared a name."""
    _require_db()
    from pit_fundamentals_store.database import BitemporalLoader, connection
    from pit_fundamentals_store.temporal import build_temporal_versions

    filings, facts = _aapl_fixture()
    BitemporalLoader().load(filings, build_temporal_versions(facts))

    with connection() as c:
        rows = c.execute(
            "SELECT value FROM fundamentals_latest WHERE cik = 320193"
        ).fetchall()

    assert [r[0] for r in rows] == [Decimal("8235000000")]
