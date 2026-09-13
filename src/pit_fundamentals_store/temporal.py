from datetime import UTC, datetime
import logging

from .models import NormalizedFact, TemporalFact

logger = logging.getLogger(__name__)


def key_for_fact(f: NormalizedFact):
    return (f.cik, f.concept, f.period_start, f.period_end, f.unit)


def build_temporal_versions(facts: list[NormalizedFact]) -> list[TemporalFact]:
    groups = {}
    for f in facts:
        groups.setdefault(key_for_fact(f), []).append(f)
    out = []
    for versions in groups.values():
        versions.sort(key=lambda x: (x.filed_at, x.source_accession, x.raw_concept))

        # Collapse same-instant duplicates (typically the same fact reached
        # via more than one XBRL tag alias within a single filing) before
        # building intervals. Without this, two entries sharing filed_at
        # produce a zero-width [filed_at, filed_at) interval: it violates
        # fact_effective (effective_to > effective_from), and even if it
        # didn't, a zero-width knowledge_time range is never matched by any
        # as_of query — a silently unreachable row, which is worse than a
        # loud constraint failure.
        deduped = []
        for f in versions:
            if deduped and deduped[-1].filed_at == f.filed_at:
                if deduped[-1].value != f.value:
                    logger.warning(
                        "Same-instant conflicting values for cik=%s concept=%s "
                        "period_end=%s filed_at=%s: keeping %s (%s), dropping %s (%s)",
                        f.cik, f.concept, f.period_end, f.filed_at,
                        deduped[-1].raw_concept, deduped[-1].value,
                        f.raw_concept, f.value,
                    )
                # else: identical value via a different XBRL alias — an
                # expected duplicate, not worth a warning.
                continue
            deduped.append(f)

        for i, f in enumerate(deduped):
            nxt = deduped[i + 1].filed_at if i + 1 < len(deduped) else None
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
