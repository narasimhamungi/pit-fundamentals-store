# Architecture

```text
EDGAR full index / RSS
        -> filing discovery
        -> XBRL-derived facts
        -> canonical concept mapping
        -> validation
        -> transactional bitemporal load
        -> PostgreSQL tstzrange + GiST
        -> fundamentals_asof(cik, concept, as_of)
```

Airflow orchestrates the stages. Core transformations remain reusable Python modules.
