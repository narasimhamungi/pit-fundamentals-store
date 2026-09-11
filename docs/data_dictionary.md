# Data Dictionary

| Field | Meaning |
|---|---|
| `cik` | SEC Central Index Key |
| `concept` | Project canonical concept |
| `raw_concept` | Original XBRL element |
| `period_start` | Duration start; null for instant facts |
| `period_end` | Duration end / instant date |
| `value` | Reported numeric value |
| `unit` | XBRL unit |
| `filed_at` | Filing knowledge timestamp |
| `effective_from` | Knowledge interval start |
| `effective_to` | Knowledge interval end |
| `knowledge_time` | PostgreSQL knowledge-time range |
| `valid_time` | Economic applicability range |
| `source_accession` | SEC filing accession |
| `source_url` | Filing provenance |
