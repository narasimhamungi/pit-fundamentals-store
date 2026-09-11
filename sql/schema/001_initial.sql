CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE IF NOT EXISTS company(cik BIGINT PRIMARY KEY,ticker TEXT,company_name TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS filing(
 accession_number TEXT PRIMARY KEY,cik BIGINT NOT NULL REFERENCES company(cik),form TEXT NOT NULL,filing_date DATE NOT NULL,
 report_date DATE,primary_document TEXT,source_url TEXT NOT NULL,retrieved_at TIMESTAMPTZ NOT NULL,UNIQUE(cik,accession_number));
CREATE TABLE IF NOT EXISTS fundamental_fact(
 fact_id BIGSERIAL PRIMARY KEY,cik BIGINT NOT NULL REFERENCES company(cik),concept TEXT NOT NULL,raw_concept TEXT NOT NULL,
 period_start DATE,period_end DATE NOT NULL,value NUMERIC NOT NULL,unit TEXT NOT NULL,source_accession TEXT NOT NULL REFERENCES filing(accession_number),
 filing_type TEXT NOT NULL,source_url TEXT NOT NULL,valid_time TSTZRANGE NOT NULL,knowledge_time TSTZRANGE NOT NULL,
 filed_at TIMESTAMPTZ NOT NULL,effective_from TIMESTAMPTZ NOT NULL,effective_to TIMESTAMPTZ,
 dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT fact_period CHECK(period_start IS NULL OR period_start<=period_end),
 CONSTRAINT fact_effective CHECK(effective_to IS NULL OR effective_to>effective_from),
 CONSTRAINT fact_filed CHECK(filed_at=effective_from),
 -- NULLS NOT DISTINCT is load-bearing, not a style choice. Instant facts
 -- (balance-sheet items: assets, liabilities, equity, cash) have no
 -- period_start, so period_start IS NULL for all of them. Under SQL's
 -- default NULLS DISTINCT semantics, NULL != NULL, so a plain UNIQUE
 -- constraint never fires for those rows and ON CONFLICT DO NOTHING below
 -- silently inserts a duplicate on every re-run — verified empirically
 -- against Postgres 16: a second identical load produced 4 rows from 2.
 -- That breaks idempotency for exactly the facts the DAGs re-ingest
 -- daily, and duplicates would then double every point-in-time query
 -- result. Requires Postgres 15+ (docker-compose pins postgres:16-alpine).
 UNIQUE NULLS NOT DISTINCT (source_accession,cik,concept,raw_concept,period_start,period_end,unit,value));
CREATE INDEX IF NOT EXISTS ix_fact_logical ON fundamental_fact(cik,concept,period_end);
CREATE INDEX IF NOT EXISTS ix_fact_filed ON fundamental_fact(filed_at);
CREATE INDEX IF NOT EXISTS ix_fact_knowledge_gist ON fundamental_fact USING GIST(knowledge_time);

CREATE OR REPLACE FUNCTION fundamentals_asof(p_cik BIGINT,p_concept TEXT,p_as_of TIMESTAMPTZ)
RETURNS TABLE(cik BIGINT,concept TEXT,raw_concept TEXT,period_start DATE,period_end DATE,value NUMERIC,unit TEXT,filed_at TIMESTAMPTZ,source_accession TEXT,source_url TEXT)
LANGUAGE sql STABLE AS $$
SELECT f.cik,f.concept,f.raw_concept,f.period_start,f.period_end,f.value,f.unit,f.filed_at,f.source_accession,f.source_url
FROM fundamental_fact f WHERE f.cik=p_cik AND f.concept=p_concept AND f.knowledge_time @> p_as_of
ORDER BY f.period_end,f.filed_at;
$$;

-- Named fundamentals_LATEST, deliberately not fundamentals_asof. This view
-- returns the most recently filed version of each fact — the restated,
-- current-best value. That is the OPPOSITE of point-in-time. It previously
-- shared the name `fundamentals_asof` with the function above (legal in
-- Postgres, since functions and relations are separate namespaces), which
-- meant `SELECT * FROM fundamentals_asof` silently returned the
-- look-ahead-biased answer to anyone who assumed the name meant what it
-- says. Use this for "what does Apple's FY2009 net income look like today";
-- use fundamentals_asof(cik, concept, as_of) for "what was knowable on date X".
CREATE OR REPLACE VIEW fundamentals_latest AS
SELECT DISTINCT ON(cik,concept,period_start,period_end,unit) *
FROM fundamental_fact ORDER BY cik,concept,period_start,period_end,unit,filed_at DESC;
