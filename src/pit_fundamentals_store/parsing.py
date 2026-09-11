from datetime import UTC, date, datetime, time
from decimal import Decimal

from .mapping import resolve_concept
from .models import NormalizedFact


def _dt(s: str) -> datetime:
    return datetime.combine(date.fromisoformat(s), time.min, tzinfo=UTC)


class CompanyFactsParser:
    """Normalize SEC's XBRL-derived companyfacts representation."""

    def parse(self, payload: dict) -> list[NormalizedFact]:
        cik = int(payload["cik"])
        company = payload.get("entityName", f"CIK {cik}")
        out = []
        for ns, concepts in payload.get("facts", {}).items():
            if ns != "us-gaap":
                continue
            for raw, cp in concepts.items():
                rule = resolve_concept(raw)
                if rule is None:
                    continue
                for unit, entries in cp.get("units", {}).items():
                    for e in entries:
                        if (
                            "end" not in e
                            or "val" not in e
                            or "filed" not in e
                            or not e.get("accn")
                        ):
                            continue
                        accn_path = e["accn"].replace("-", "")
                        source_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn_path}/"
                        out.append(
                            NormalizedFact(
                                cik,
                                None,
                                company,
                                rule.canonical,
                                raw,
                                date.fromisoformat(e["start"]) if e.get("start") else None,
                                date.fromisoformat(e["end"]),
                                _dt(e["filed"]),
                                Decimal(str(e["val"])),
                                unit,
                                e["accn"],
                                e.get("form", "UNKNOWN"),
                                source_url,
                                e.get("fy"),
                                e.get("fp"),
                                rule.instant,
                            )
                        )
        return out

    @staticmethod
    def deduplicate_filing_facts(facts):
        seen = set()
        out = []
        for f in facts:
            k = (
                f.cik,
                f.concept,
                f.raw_concept,
                f.period_start,
                f.period_end,
                f.filed_at,
                f.value,
                f.unit,
                f.source_accession,
            )
            if k not in seen:
                seen.add(k)
                out.append(f)
        return out
