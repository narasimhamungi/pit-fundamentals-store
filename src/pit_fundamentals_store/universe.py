"""Ticker -> CIK resolution against SEC's public company_tickers.json.

Self-contained: no dependency on marketdata-lakehouse. Given a list of
tickers (e.g. from an S&P 500 constituent file), resolves each to its
SEC CIK so orchestration.py can drive ingestion off a ticker universe
instead of hand-maintained CIK numbers.

Caution: this maps CURRENT ticker->CIK only. It does not give dated
index membership. Using today's constituent list to backfill history
is itself a look-ahead-bias risk (the exact failure mode this project
exists to prevent, one level up: index membership instead of
fundamentals). See docs/decisions.md.
"""

from __future__ import annotations

from .config import get_settings
from .logging_config import configure_logging

log = configure_logging()

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def fetch_ticker_cik_map(session=None) -> dict[str, int]:
    """Fetch SEC's ticker->CIK map.

    Format: {"0": {"cik_str": int, "ticker": str, "title": str}, ...}.
    """
    import requests

    s = get_settings()
    session = session or requests.Session()
    session.headers.update({"User-Agent": s.sec_user_agent, "Accept-Encoding": "gzip, deflate"})
    r = session.get(_TICKERS_URL, timeout=s.sec_timeout_seconds)
    r.raise_for_status()
    data = r.json()
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def resolve_cik(ticker: str, mapping: dict[str, int]) -> int | None:
    return mapping.get(ticker.strip().upper())


def resolve_cik_list(tickers: list[str], mapping: dict[str, int] | None = None) -> list[int]:
    """Resolve a list of tickers to CIKs. Raises on any unresolved ticker
    rather than silently dropping it, matching this project's validation
    discipline elsewhere (see validation.py)."""
    mapping = mapping if mapping is not None else fetch_ticker_cik_map()
    ciks = []
    unresolved = []
    for t in tickers:
        cik = resolve_cik(t, mapping)
        if cik is None:
            unresolved.append(t)
        else:
            ciks.append(cik)
    if unresolved:
        log.warning("operation=resolve_cik_list unresolved_tickers=%s", ",".join(unresolved))
        raise ValueError(f"Could not resolve CIK for tickers: {', '.join(unresolved)}")
    return ciks
