from contextlib import contextmanager
from datetime import UTC, datetime, time
from pathlib import Path

import psycopg

from .config import get_settings


@contextmanager
def connection():
    # connect_timeout=10 is load-bearing, not a nicety: without it, an
    # unreachable/misconfigured database falls back to the OS-level TCP
    # timeout, not libpq's. Confirmed against a real run on Windows: 5
    # connection attempts against a port nothing was listening on took
    # 21 minutes combined to fail, instead of failing in seconds.
    with psycopg.connect(get_settings().database_url, connect_timeout=10) as conn:
        yield conn


def _schema_candidates() -> list[Path]:
    """Locate sql/schema/001_initial.sql across install modes.

    Editable/dev installs resolve it relative to the source tree; Docker and
    other non-editable installs must set SCHEMA_PATH (see docker-compose.yml)
    since the sql/ directory is not packaged with the wheel.
    """
    candidates = []
    settings = get_settings()
    if settings.schema_path:
        candidates.append(Path(settings.schema_path))
    candidates.append(Path(__file__).resolve().parents[2] / "sql/schema/001_initial.sql")
    return candidates


def initialise_schema():
    for path in _schema_candidates():
        if path.exists():
            sql = path.read_text()
            with connection() as conn:
                conn.execute(sql)
            return
    tried = ", ".join(str(c) for c in _schema_candidates())
    raise FileNotFoundError(
        f"Could not locate sql/schema/001_initial.sql (tried: {tried}). "
        "Set the SCHEMA_PATH environment variable to an absolute path."
    )


_UPSERT_COMPANY = """
INSERT INTO company(cik, ticker, company_name) VALUES (%s, %s, %s)
ON CONFLICT (cik) DO UPDATE
SET ticker = COALESCE(EXCLUDED.ticker, company.ticker),
    company_name = EXCLUDED.company_name
"""

_INSERT_FILING = """
INSERT INTO filing(
    accession_number, cik, form, filing_date, report_date,
    primary_document, source_url, retrieved_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (accession_number) DO NOTHING
"""

_INSERT_FACT = """
INSERT INTO fundamental_fact(
    cik, concept, raw_concept, period_start, period_end, value, unit,
    source_accession, filing_type, source_url,
    valid_time, knowledge_time, filed_at, effective_from, effective_to
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    tstzrange(%s, %s, '[)'), tstzrange(%s, %s, '[)'), %s, %s, %s
)
ON CONFLICT (
    source_accession, cik, concept, raw_concept, period_start, period_end, unit, value
) DO NOTHING
RETURNING fact_id
"""


def _as_datetime(d):
    return datetime.combine(d, time.min, UTC)


def _valid_time_bounds(period_start, period_end):
    """Duration facts: [period_start, period_end). Instant facts: [period_end, )."""
    if period_start:
        return _as_datetime(period_start), _as_datetime(period_end)
    return _as_datetime(period_end), None


class BitemporalLoader:
    def load(self, filings, facts):
        filings = list(filings)
        facts = list(facts)
        if not facts:
            return 0
        with connection() as conn:
            for f in filings:
                conn.execute(_UPSERT_COMPANY, (f.cik, f.ticker, f.company_name))
                conn.execute(
                    _INSERT_FILING,
                    (
                        f.accession_number,
                        f.cik,
                        f.form,
                        f.filing_date,
                        f.report_date,
                        f.primary_document,
                        f.source_url,
                        f.retrieved_at,
                    ),
                )
            n = 0
            for f in facts:
                valid_from, valid_to = _valid_time_bounds(f.period_start, f.period_end)
                cur = conn.execute(
                    _INSERT_FACT,
                    (
                        f.cik,
                        f.concept,
                        f.raw_concept,
                        f.period_start,
                        f.period_end,
                        f.value,
                        f.unit,
                        f.source_accession,
                        f.filing_type,
                        f.source_url,
                        valid_from,
                        valid_to,
                        f.knowledge_time_start,
                        f.knowledge_time_end,
                        f.knowledge_time_start,
                        f.knowledge_time_start,
                        f.knowledge_time_end,
                    ),
                )
                if cur.fetchone():
                    n += 1
            return n