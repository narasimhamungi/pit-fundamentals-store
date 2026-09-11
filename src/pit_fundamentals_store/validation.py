from decimal import Decimal


def validate_fact(f):
    e = []
    if f.period_start and f.period_start > f.period_end:
        e.append("period_start_after_period_end")
    if f.filed_at.tzinfo is None:
        e.append("filed_at_must_be_timezone_aware")
    if not isinstance(f.value, Decimal):
        e.append("value_not_decimal")
    if not f.source_accession:
        e.append("missing_accession")
    return e


def validate_pit_invariant(facts, as_of):
    return all(f.knowledge_time_start <= as_of for f in facts)
