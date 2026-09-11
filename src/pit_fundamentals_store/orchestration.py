from datetime import date

from .config import get_settings
from .database import BitemporalLoader
from .models import FilingMetadata
from .parsing import CompanyFactsParser
from .sec import SECClient
from .temporal import build_temporal_versions
from .validation import validate_fact


def ingest_cik(cik: int, start: date, end: date) -> int:
    payload = SECClient().companyfacts(cik)
    parser = CompanyFactsParser()
    facts = parser.deduplicate_filing_facts(parser.parse(payload))
    facts = [f for f in facts if start <= f.period_end <= end and not validate_fact(f)]
    accessions = sorted({f.source_accession for f in facts})
    filings = []
    for acc in accessions:
        rows = [f for f in facts if f.source_accession == acc]
        filings.append(
            FilingMetadata(
                cik,
                None,
                payload.get("entityName", f"CIK {cik}"),
                acc,
                rows[0].filing_type,
                rows[0].filed_at.date(),
                max(x.period_end for x in rows),
                None,
                rows[0].source_url,
                rows[0].filed_at,
            )
        )
    return BitemporalLoader().load(filings, build_temporal_versions(facts))


def historical_backfill():
    s = get_settings()
    ciks = s.ciks
    if s.ticker_list:
        from .universe import resolve_cik_list

        ciks = resolve_cik_list(s.ticker_list)
    for cik in ciks:
        ingest_cik(cik, date(s.historical_start_year, 1, 1), date(s.historical_end_year, 12, 31))


def new_filing_poll():
    import re

    from .sec import poll_rss

    s = get_settings()
    entries = poll_rss()
    ciks = set()
    for e in entries:
        m = re.search(r"/data/(\d+)/", e.get("id", ""))
        if m:
            ciks.add(int(m.group(1)))
    for cik in sorted(ciks):
        ingest_cik(cik, date(s.historical_start_year, 1, 1), date.today())
