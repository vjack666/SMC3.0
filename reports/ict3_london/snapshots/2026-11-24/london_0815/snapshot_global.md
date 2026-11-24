# ICT 3.0 London 08:15 snapshot

- snapshot_id: `london0815_20261124_1795508100_f91651feed`
- London date: `2026-11-24`
- cutoff (UTC): `1795508100` (2026-11-24T08:15:00Z)
- cutoff (Europe/London): `2026-11-24T08:15:00+00:00`
- cutoff (America/Guayaquil): `2026-11-24T03:15:00-05:00`
- broker clock offset: `7200` s; engine cutoff: `1795515300` (2026-11-24T10:15:00Z in MT5 encoded clock)
- generated_at (UTC): `1795508100` (2026-11-24T08:15:00Z)
- engine revision: `f453bf2a9d35997cec774048a7ead25237399ac9`; mode: `OBSERVE_ONLY_NO_ORDER`
- schema: `ict3-london-snapshot/1.0`; engine schema: `['0.2-research']`
- symbols: requested=33, exported=33, stale=0, unavailable=0
- validation: **PASS**
- hashes: see [manifest.json](manifest.json) for file counts, sizes and SHA-256.

Read `manifest.json` for `coverage_by_symbol_tf` and `freshness_by_symbol_tf`; per-symbol detail is under `instruments/<SYM>/`. `entry_authorized` and `mode` are engine values copied verbatim. No lifecycle flags are invented.

## Where to start

1. Open [validation](validation.json) and check the session date above.
2. Read the instrument summaries; open detailed JSON only as needed.
3. Use [data quality](data_quality.json) and [manifest](manifest.json) for provenance.

[AUDCAD](instruments/AUDCAD/analysis.md) | [AUDCHF](instruments/AUDCHF/analysis.md) | [AUDJPY](instruments/AUDJPY/analysis.md) | [AUDUSD](instruments/AUDUSD/analysis.md) | [CADCHF](instruments/CADCHF/analysis.md) | [CADJPY](instruments/CADJPY/analysis.md) | [EURAUD](instruments/EURAUD/analysis.md) | [EURCAD](instruments/EURCAD/analysis.md) | [EURCHF](instruments/EURCHF/analysis.md) | [EURGBP](instruments/EURGBP/analysis.md) | [EURJPY](instruments/EURJPY/analysis.md) | [EURNZD](instruments/EURNZD/analysis.md) | [EURUSD](instruments/EURUSD/analysis.md) | [GBPAUD](instruments/GBPAUD/analysis.md) | [GBPCAD](instruments/GBPCAD/analysis.md) | [GBPCHF](instruments/GBPCHF/analysis.md) | [GBPJPY](instruments/GBPJPY/analysis.md) | [GBPNZD](instruments/GBPNZD/analysis.md) | [GBPUSD](instruments/GBPUSD/analysis.md) | [GER30](instruments/GER30/analysis.md) | [NDX100](instruments/NDX100/analysis.md) | [NZDCAD](instruments/NZDCAD/analysis.md) | [NZDCHF](instruments/NZDCHF/analysis.md) | [NZDJPY](instruments/NZDJPY/analysis.md) | [NZDUSD](instruments/NZDUSD/analysis.md) | [SPX500](instruments/SPX500/analysis.md) | [UKOUSD](instruments/UKOUSD/analysis.md) | [US30](instruments/US30/analysis.md) | [USDCAD](instruments/USDCAD/analysis.md) | [USDCHF](instruments/USDCHF/analysis.md) | [USDJPY](instruments/USDJPY/analysis.md) | [USOUSD](instruments/USOUSD/analysis.md) | [XAUUSD](instruments/XAUUSD/analysis.md)

## Publication provenance

Recovered offline from the original November 24 export. The prior validation failed only on the package size limit. Instrument and feed files are unchanged; no data was fetched or recalculated. The 08:15 London cutoff is unchanged.
