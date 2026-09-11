from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pit_fundamentals_store.mapping import resolve_concept
from pit_fundamentals_store.models import NormalizedFact
from pit_fundamentals_store.temporal import build_temporal_versions, point_in_time


def mk(filed, value, i):
    return NormalizedFact(
        320193,
        "AAPL",
        "Apple Inc.",
        "revenue",
        "Revenues",
        date(2023, 1, 1),
        date(2023, 12, 31),
        filed,
        Decimal(value),
        "USD",
        f"a{i}",
        "10-K",
        "fixture",
    )


def test_aliases():
    assert resolve_concept("Revenues").canonical == "revenue"
    assert resolve_concept("SalesRevenueNet").canonical == "revenue"


def test_restatement():
    b = mk(datetime(2024, 2, 15, tzinfo=UTC), 100, 1)
    a = mk(datetime(2025, 2, 20, tzinfo=UTC), 110, 2)
    rows = build_temporal_versions([b, a])
    assert rows[0].knowledge_time_end == rows[1].knowledge_time_start
    assert point_in_time(rows, 320193, "revenue", datetime(2024, 6, 1, tzinfo=UTC))[0].value == 100
    assert point_in_time(rows, 320193, "revenue", datetime(2025, 3, 1, tzinfo=UTC))[0].value == 110


def test_no_future_leak_reference_case():
    # Deterministic reference test always runs; the Hypothesis property test below runs
    # when the test extra is installed.
    base = datetime(2020, 1, 1, tzinfo=UTC)
    rows = build_temporal_versions(
        [mk(base + timedelta(days=o), i, i) for i, o in enumerate([0, 100, 200])]
    )
    dt = base + timedelta(days=150)
    got = point_in_time(rows, 320193, "revenue", dt)
    assert all(r.knowledge_time_start <= dt for r in got)


def test_hypothesis_property():
    __import__("pytest").importorskip("hypothesis")
    from hypothesis import given
    from hypothesis import strategies as st

    @given(
        st.lists(st.integers(0, 3650), min_size=1, max_size=8, unique=True), st.integers(0, 3650)
    )
    def prop(offsets, asof):
        base = datetime(2020, 1, 1, tzinfo=UTC)
        rows = build_temporal_versions(
            [mk(base + timedelta(days=o), i, i) for i, o in enumerate(sorted(offsets))]
        )
        dt = base + timedelta(days=asof)
        got = point_in_time(rows, 320193, "revenue", dt)
        assert all(r.knowledge_time_start <= dt for r in got)

    prop()


def test_aapl_golden():
    facts = [
        NormalizedFact(
            320193,
            "AAPL",
            "Apple Inc.",
            "net_income",
            "NetIncomeLoss",
            None,
            date(2009, 9, 26),
            datetime(2009, 10, 27, tzinfo=UTC),
            Decimal("5704000000"),
            "USD",
            "0001193125-09-214859",
            "10-K",
            "sec",
        ),
        NormalizedFact(
            320193,
            "AAPL",
            "Apple Inc.",
            "net_income",
            "NetIncomeLoss",
            None,
            date(2009, 9, 26),
            datetime(2010, 1, 25, tzinfo=UTC),
            Decimal("8235000000"),
            "USD",
            "0001193125-10-012091",
            "10-K/A",
            "sec",
        ),
    ]
    rows = build_temporal_versions(facts)
    assert point_in_time(rows, 320193, "net_income", datetime(2009, 12, 1, tzinfo=UTC))[
        0
    ].value == Decimal("5704000000")
    assert point_in_time(rows, 320193, "net_income", datetime(2010, 2, 1, tzinfo=UTC))[
        0
    ].value == Decimal("8235000000")
