from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class FilingMetadata:
    cik: int
    ticker: str | None
    company_name: str
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None
    primary_document: str | None
    source_url: str
    retrieved_at: datetime


@dataclass(frozen=True)
class NormalizedFact:
    cik: int
    ticker: str | None
    company_name: str
    concept: str
    raw_concept: str
    period_start: date | None
    period_end: date
    filed_at: datetime
    value: Decimal
    unit: str
    source_accession: str
    filing_type: str
    source_url: str
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    instant: bool = False


@dataclass(frozen=True)
class TemporalFact:
    cik: int
    ticker: str | None
    company_name: str
    concept: str
    period_start: date | None
    period_end: date
    knowledge_time_start: datetime
    knowledge_time_end: datetime | None
    value: Decimal
    unit: str
    source_accession: str
    filing_type: str
    raw_concept: str
    source_url: str
