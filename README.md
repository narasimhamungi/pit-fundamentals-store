# pit-fundamentals-store

**Point-in-Time / Bitemporal SEC EDGAR XBRL Fundamentals Store**

A portfolio-grade Data Engineering project that answers:

> **What did we know about a company's fundamentals as of a particular historical date?**

The project separates:

- **valid time** — when a financial fact economically applies; and
- **knowledge time** — when the filing made that value public.

That distinction prevents later amendments/restatements from leaking into historical research and backtests.

## Core architecture

```text
SEC EDGAR full index / submissions / RSS
                  |
                  v
          filing discovery
                  |
                  v
      SEC XBRL-derived companyfacts
                  |
                  v
       canonical concept mapping
                  |
                  v
             validation
                  |
                  v
     transactional bitemporal load
                  |
                  v
 PostgreSQL: tstzrange + GiST index
                  |
                  v
 fundamentals_asof(cik, concept, as_of)
                  |
                  v
        research / PIT analysis
```

Airflow is the orchestration layer. Kafka is intentionally excluded because the EDGAR filing feed does not justify that operational complexity for this workload.

## Trellis design reference

Trellis was inspected but not modified or imported. Its useful pattern was:

1. explicit canonical concepts;
2. multiple known XBRL aliases per concept;
3. querying all known aliases rather than treating the first tag as globally authoritative; and
4. retaining the raw matched concept for provenance.

This project reimplements that design in `src/pit_fundamentals_store/mapping.py`.

## Repository structure

```text
pit-fundamentals-store/
├── airflow/dags/                 # orchestration
├── src/pit_fundamentals_store/
│   ├── config.py                 # environment configuration
│   ├── logging_config.py          # rotating persistent logs
│   ├── models.py                 # typed data contracts
│   ├── sec.py                    # SEC client
│   ├── parsing.py                # XBRL-derived fact normalization
│   ├── arelle_adapter.py         # optional raw-instance Arelle validation
│   ├── mapping.py                # canonical concept rules
│   ├── temporal.py               # bitemporal interval logic
│   ├── validation.py             # validation invariants
│   ├── database.py               # PostgreSQL loader
│   └── cli.py                    # operational CLI
├── sql/schema/                   # PostgreSQL schema/function/view
├── sql/queries/                  # PIT examples
├── tests/                        # unit/property/integration coverage
├── fixtures/aapl/                # frozen AAPL restatement fixture
├── notebooks/                    # walkthrough material
├── docs/                         # architecture, bitemporal, decisions, troubleshooting
├── outputs/                      # generated evidence
├── logs/                         # persistent project logs
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Quickstart — Docker

### 1. Clone

```bash
git clone <your-github-url>/pit-fundamentals-store.git
cd pit-fundamentals-store
```

### 2. Configure

```bash
cp .env.example .env
```

Set a real SEC User-Agent/contact in `.env`.

### 3. Start infrastructure

```bash
docker compose build
docker compose up -d postgres
docker compose run --rm airflow-init
docker compose up -d airflow-webserver airflow-scheduler
```

Airflow UI:

```text
http://localhost:8080
```

Local development credentials created by the compose bootstrap:

```text
admin / admin
```

Do not expose those credentials beyond local development.

### 4. Initialize the project database

The SQL schema is mounted into PostgreSQL's initialization directory for a fresh volume. For an existing database:

```bash
docker compose exec airflow-scheduler pit-fundamentals init-db
```

### 5. Run a controlled AAPL ingestion

```bash
docker compose exec airflow-scheduler pit-fundamentals ingest-company   --cik 320193   --start 2010-01-01   --end 2026-12-31
```

The ingestion path is rate-limited and accession-idempotent.

### 6. Run the deterministic AAPL PIT demonstration

```bash
docker compose exec airflow-scheduler pit-fundamentals aapl-demo
cat outputs/aapl_pit_demo.txt
```

### 7. Tests

```bash
docker compose exec airflow-scheduler pytest -q
```

Opt into PostgreSQL integration:

```bash
docker compose exec -e RUN_DB_INTEGRATION=1 airflow-scheduler pytest tests/test_integration.py -q
```

### 8. Logs

```bash
tail -f logs/pit_fundamentals_store.log
docker compose logs -f airflow-scheduler
```

### 9. Stop

```bash
docker compose down
```

Remove the local PostgreSQL volume too:

```bash
docker compose down -v
```

## Local Python development

Python 3.11+:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install:

```bash
python -m pip install --upgrade pip
pip install -e ".[test,tooling]"
```

Optional Arelle validation:

```bash
pip install -e ".[xbrl]"
```

## SEC ingestion

`src/pit_fundamentals_store/sec.py` uses SEC public endpoints with a descriptive User-Agent and configured delay.

`src/pit_fundamentals_store/parsing.py` normalizes SEC's XBRL-derived `companyfacts` representation while preserving:

- raw concept;
- canonical concept;
- period;
- value;
- unit;
- filing type;
- filed date;
- accession number;
- source URL.

The full-index/RSS orchestration points live under `airflow/dags/`. The canonical company universe is intentionally configurable; a production S&P 500 backfill should use a dated constituent universe rather than silently substituting today's membership.

## XBRL parser strategy

The scalable ingestion path uses SEC's XBRL-derived companyfacts representation. Arelle is included as an open-source raw-instance XBRL validation adapter in `arelle_adapter.py`.

This split is deliberate: parsing every historical filing through the complete XBRL taxonomy/linkbase graph is substantially heavier than consuming SEC's normalized XBRL facts, while Arelle remains available when raw-instance validation is required.

## Ticker universe resolution

`historical_backfill()` accepts either `SAMPLE_CIKS` (raw CIK numbers) or `TICKERS` (comma-separated tickers, resolved to CIKs at runtime against SEC's free `company_tickers.json` — see `src/pit_fundamentals_store/universe.py`). `TICKERS` takes precedence when set. Unresolvable tickers fail the run loudly rather than being silently dropped.

This resolves *current* ticker → CIK only. It is not a source of dated index membership. Backfilling history using today's constituent list (S&P 500 or otherwise) reintroduces look-ahead bias at the universe-selection level — the same failure class this project exists to prevent at the fundamentals level. A correct historical backfill needs a dated membership source (e.g. Wikipedia's "Selected Changes" table, or a maintained historical-constituents dataset) supplied separately; `universe.py` deliberately does not attempt to derive one.

## Concept mapping

Example:

```text
us-gaap:Revenues
us-gaap:SalesRevenueNet
us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
                  |
                  v
             canonical: revenue
```

Unknown concepts are not silently invented. Only explicit, tested rules are mapped.

## Bitemporal model

Core database fields include:

```text
cik
concept
raw_concept
period_start
period_end
value
unit
filed_at
effective_from
effective_to
source_accession
source_url
valid_time
knowledge_time
```

Knowledge time is represented as:

```sql
tstzrange(effective_from, effective_to, '[)')
```

with a GiST index:

```sql
CREATE INDEX ix_fact_knowledge_gist
ON fundamental_fact USING GIST (knowledge_time);
```

See `docs/bitemporal.md`.

## Point-in-time query

Parameterized PIT interface:

```sql
SELECT *
FROM fundamentals_asof(
    320193,
    'net_income',
    '2009-12-01T00:00:00Z'
);
```

After the amendment:

```sql
SELECT *
FROM fundamentals_asof(
    320193,
    'net_income',
    '2010-02-01T00:00:00Z'
);
```

A parameter-free `fundamentals_latest` view exposes the current-best (restated) state of each fact. It is deliberately *not* named `fundamentals_asof` — it returns the most recently filed version, which is the look-ahead-biased answer if used for backtesting. Use the `fundamentals_asof(...)` function for point-in-time queries and `fundamentals_latest` only when you genuinely want today's restated figures.

## AAPL restatement example

Apple's original 2009 10-K was filed on October 27, 2009. The later 10-K/A amended the original filing to reflect retrospective adoption of revised revenue-recognition accounting.

The SEC filings report:

```text
Original 10-K:
2009 net income = $5.704bn
accession       = 0001193125-09-214859

2010 10-K/A:
2009 net income = $8.235bn
accession       = 0001193125-10-012091
```

The project preserves both states.

Run:

```bash
pit-fundamentals aapl-demo
```

Actual generated evidence:

```text
outputs/aapl_pit_demo.txt
```

The demonstration also calculates an illustrative P/E using the same price/share-count inputs on both sides, isolating the effect of the restated earnings denominator. Those market inputs are demonstration inputs, not claimed SEC fundamentals.

## Testing

### Unit / deterministic core

```bash
pytest tests/test_core.py -q
```

### Property-based PIT invariant

The test uses Hypothesis when the test extra is installed and checks:

```text
every returned fact has filed_at <= as_of
```

### Integration

```bash
RUN_DB_INTEGRATION=1 pytest tests/test_integration.py -q
```

The integration test is intentionally opt-in so ordinary CI does not depend on a live PostgreSQL instance.

### CI

`.github/workflows/ci.yml` runs:

```text
install
-> ruff
-> pytest
```

No SEC credentials or live data are required for CI.

## Logging

Persistent application log:

```text
logs/pit_fundamentals_store.log
```

The rotating logger records timestamp, level, module and operation context. Secrets are not logged.

Airflow task logs remain available through Airflow.

## Idempotency and reliability

The loader uses:

- accession-aware filing identity;
- unique logical source-fact constraints;
- database transactions;
- deterministic temporal interval reconstruction;
- explicit validation;
- Airflow retry support.

A repeated ingestion of the same source fact is a no-op rather than a duplicate.

## Data lineage

Every normalized fact retains enough provenance to answer:

```text
Where did this value come from?
```

The answer includes:

```text
CIK
canonical concept
raw XBRL concept
period
value
unit
filed_at
accession
source URL
```

## Red-team considerations

The design explicitly checks for:

- future-information leakage;
- duplicate source facts;
- restatement history loss;
- instant/duration distinction;
- unmapped concepts;
- invalid temporal ordering;
- network dependence in CI;
- secret leakage in logs/configuration.

Material design decisions are recorded in `docs/decisions.md`.

## Limitations

1. The canonical concept set is intentionally small, not a complete us-gaap ontology.
2. SEC companyfacts is the scalable normalized XBRL-derived path; Arelle is the raw-instance validation path.
3. The current normalized model is aimed at consolidated fundamentals and does not yet model every XBRL dimensional context.
4. A historical S&P 500 universe must be supplied as dated membership data for a true historical constituent backfill.
5. Live SEC ingestion is rate-limited and should be performed in controlled batches.
6. Full Docker/PostgreSQL/Airflow verification requires Docker; the current development environment did not provide Docker.

## Exact operational command reference

```bash
# Setup
cp .env.example .env
python -m venv .venv
pip install -e ".[test,tooling]"

# Infrastructure
docker compose build
docker compose up -d postgres
docker compose run --rm airflow-init
docker compose up -d airflow-webserver airflow-scheduler

# Database
docker compose exec airflow-scheduler pit-fundamentals init-db

# Sample ingestion
docker compose exec airflow-scheduler pit-fundamentals ingest-company --cik 320193 --start 2010-01-01 --end 2026-12-31

# Tests
pytest -q

# Property tests specifically
pytest -q -k hypothesis

# AAPL demo
pit-fundamentals aapl-demo

# Logs
tail -f logs/pit_fundamentals_store.log

# Stop
docker compose down
```

## Portfolio evidence

Only generated evidence should be placed under `outputs/`. The current deterministic evidence file was generated locally from the frozen AAPL fixture.

Target evidence for a full Docker run:

1. Airflow green DAG run;
2. property-based test output;
3. database row counts;
4. PIT query before/after amendment;
5. AAPL walkthrough;
6. logging evidence;
7. CI success.

No screenshots, row counts or CI results should be claimed unless actually produced.

## Related portfolio sequence

1. `marketdata-lakehouse` — multi-source market data and reconciliation.
2. **`pit-fundamentals-store`** — point-in-time fundamentals and restatement integrity.
3. `quant-data-sdk` — local quant-researcher-facing API and SDK.

