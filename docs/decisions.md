# Engineering Decisions

- **Trellis reference:** inspected without modifying it; canonical concepts use explicit alias sets and retain raw concepts.
- **XBRL:** SEC companyfacts is the scalable normalized XBRL-derived path; Arelle is included as an open-source raw-instance validation adapter.
- **Bitemporal model:** knowledge time uses `tstzrange` with `[effective_from,effective_to)`; later filings close prior intervals.
- **PIT API:** a parameterized PostgreSQL function is used because ordinary views cannot accept parameters; a latest-state view is also supplied.
- **Kafka:** excluded because EDGAR's feed frequency does not justify it.
- **Idempotency:** accession number plus logical fact uniqueness and transaction boundaries make retries safe.
- **Testing:** live SEC data is not required for CI; fixtures prove the PIT invariant deterministically.
