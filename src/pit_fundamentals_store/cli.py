import argparse
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from .logging_config import configure_logging
from .models import NormalizedFact
from .temporal import build_temporal_versions, point_in_time


def aapl_demo():
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
            "https://www.sec.gov/Archives/edgar/data/320193/000119312509214859/d10k.htm",
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
            "https://www.sec.gov/Archives/edgar/data/320193/000119312510012091/d10ka.htm",
        ),
    ]
    rows = build_temporal_versions(facts)
    b = point_in_time(rows, 320193, "net_income", datetime(2009, 12, 1, tzinfo=UTC))[0]
    a = point_in_time(rows, 320193, "net_income", datetime(2010, 2, 1, tzinfo=UTC))[0]
    price = Decimal("190")
    shares = Decimal("893000000")
    pe_before = price * shares / b.value
    pe_after = price * shares / a.value
    text = (
        f"AAPL PIT demo\n"
        f"Before: {b.value} via {b.source_accession}\n"
        f"After: {a.value} via {a.source_accession}\n"
        f"Illustrative P/E before={pe_before:.2f}x after={pe_after:.2f}x\n"
    )
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/aapl_pit_demo.txt").write_text(text)
    print(text)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    sub.add_parser("aapl-demo")
    i = sub.add_parser("ingest-company")
    i.add_argument("--cik", type=int, required=True)
    i.add_argument("--start", default="2010-01-01")
    i.add_argument("--end", default="2026-12-31")
    a = p.parse_args()
    log = configure_logging()
    if a.cmd == "init-db":
        from .database import initialise_schema

        initialise_schema()
        log.info("operation=database_initialise status=success")
    elif a.cmd == "aapl-demo":
        aapl_demo()
    else:
        from .orchestration import ingest_cik

        loaded = ingest_cik(a.cik, date.fromisoformat(a.start), date.fromisoformat(a.end))
        log.info("operation=ingest_company cik=%s loaded=%s", a.cik, loaded)


if __name__ == "__main__":
    main()
