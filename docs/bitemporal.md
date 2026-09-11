# Bitemporal Model

**Valid time** is when the fact economically applies: duration facts use `period_start`/`period_end`; instant facts use the period end.

**Knowledge time** is when the filing made the value public. It is stored as `tstzrange(effective_from,effective_to,'[)')`.

Example:

```text
2009-10-27  original 10-K  net income $5.704bn
2010-01-25  10-K/A        net income $8.235bn
```

`as_of=2009-12-01` returns the original. `as_of=2010-02-01` returns the amendment.

The GiST index supports `knowledge_time @> as_of`. This prevents future-information leakage in backtests.
