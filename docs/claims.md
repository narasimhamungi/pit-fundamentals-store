# Claims ledger

Generated 2026-11-04 from the repo's own README (architecture section read; full validation section not read this pass).

| Claim | Tag | Evidence |
|---|---|---|
| Bitemporal SEC EDGAR XBRL fundamentals store separating valid time (when a fact economically applies) from knowledge time (when the filing made it public) | Demonstrated — architectural design, consistent with quant-data-sdk and Trellis both depending on this repo's point-in-time correctness | README "Core architecture" |
| PostgreSQL `tstzrange` + GiST index for bitemporal storage | Demonstrated | README architecture diagram |
| Prevents later amendments/restatements from leaking into historical research and backtests | Demonstrated — this is the stated design goal; quant-data-sdk's README independently corroborates this repo resolves point-in-time joins correctly | cross-repo consistency with quant-data-sdk |

## Action
Only the architecture section was read this pass — not the test/validation section. Given quant-data-sdk, Trellis-adjacent repos and the whole point-in-time story in this portfolio rests on this repo's correctness, flag for a deeper pass (test count, validation against a known restatement like Nike/Trellis's AAPL FY2009 example) before treating this ledger as complete.
