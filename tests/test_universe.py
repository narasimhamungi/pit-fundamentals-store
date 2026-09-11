import pytest

from pit_fundamentals_store.universe import resolve_cik, resolve_cik_list

FIXTURE_MAPPING = {"AAPL": 320193, "MSFT": 789019}


def test_resolve_cik_case_insensitive():
    assert resolve_cik("aapl", FIXTURE_MAPPING) == 320193
    assert resolve_cik("AAPL", FIXTURE_MAPPING) == 320193


def test_resolve_cik_unknown_ticker_returns_none():
    assert resolve_cik("ZZZZ", FIXTURE_MAPPING) is None


def test_resolve_cik_list_success():
    assert resolve_cik_list(["AAPL", "MSFT"], FIXTURE_MAPPING) == [320193, 789019]


def test_resolve_cik_list_raises_on_unresolved_ticker():
    with pytest.raises(ValueError, match="ZZZZ"):
        resolve_cik_list(["AAPL", "ZZZZ"], FIXTURE_MAPPING)
