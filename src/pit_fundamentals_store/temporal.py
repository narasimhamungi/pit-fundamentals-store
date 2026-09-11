from datetime import UTC, datetime

from .models import NormalizedFact, TemporalFact


def key_for_fact(f: NormalizedFact):
    return (f.cik, f.concept, f.period_start, f.period_end, f.unit)


def build_temporal_versions(facts: list[NormalizedFact]) -> list[TemporalFact]:
    groups = {}
    for f in facts:
        groups.setdefault(key_for_fact(f), []).append(f)
    out = []
    for versions in groups.values():
        versions.sort(key=lambda x: (x.filed_at, x.source_accession, x.raw_concept))
        for i, f in enumerate(versions):
            nxt = versions[i + 1].filed_at if i + 1 < len(versions) else None
            out.append(
                TemporalFact(
                    f.cik,
                    f.ticker,
                    f.company_name,
                    f.concept,
                    f.period_start,
                    f.period_end,
                    f.filed_at,
                    nxt,
                    f.value,
                    f.unit,
                    f.source_accession,
                    f.filing_type,
                    f.raw_concept,
                    f.source_url,
                )
            )
    return out


def point_in_time(
    facts: list[TemporalFact], cik: int, concept: str, as_of: datetime
) -> list[TemporalFact]:
    as_of = as_of.astimezone(UTC)
    return sorted(
        [
            f
            for f in facts
            if f.cik == cik
            and f.concept == concept
            and f.knowledge_time_start <= as_of
            and (f.knowledge_time_end is None or as_of < f.knowledge_time_end)
        ],
        key=lambda f: (f.period_end, f.knowledge_time_start),
    )
