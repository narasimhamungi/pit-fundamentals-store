-- Point-in-time: what was knowable on a given date.
-- Before Apple's 10-K/A restatement (filed 2010-01-25) -> 5,704,000,000
SELECT * FROM fundamentals_asof(320193,'net_income','2009-12-01T00:00:00Z');

-- After the restatement -> 8,235,000,000. Same company, same fiscal period,
-- different answer depending only on when you asked. This is the whole point.
SELECT * FROM fundamentals_asof(320193,'net_income','2010-02-01T00:00:00Z');

-- Current-best (restated) view, for contrast. NOT point-in-time: this always
-- returns the latest filed version, which is the look-ahead-biased answer if
-- you use it to backtest. Named fundamentals_latest so that's unambiguous.
SELECT cik,concept,period_end,value,unit,filed_at,source_accession
FROM fundamentals_latest WHERE cik=320193 ORDER BY concept,period_end;
