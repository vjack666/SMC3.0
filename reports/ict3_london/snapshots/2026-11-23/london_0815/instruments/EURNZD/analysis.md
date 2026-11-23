# EURNZD - ICT 3.0 London 08:15 snapshot

> Built from the real output of `ict.ict_chart` (revision `f453bf2a9d35997cec774048a7ead25237399ac9`). Engine mode: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` is preserved verbatim.

## 1. Identification

- Instrument: `EURNZD`; frame: `M15`; time basis: `Reloj MT5`
- `asof`: 1795428900 (MT5 clock) = 2026-11-23T08:15:00Z real UTC
- Last closed bar: 1795428900 (MT5 clock) = 2026-11-23T08:15:00Z real UTC
- Broker clock offset: `7200` s. `asof` and all last-closed epochs below are MT5 encoded-clock values; subtract the offset to obtain real UTC.
- Last close by TF: D1=1795219200 (2026-11-21T00:00:00Z MT5 clock), H4=1795420800 (2026-11-23T08:00:00Z MT5 clock), H1=1795428000 (2026-11-23T10:00:00Z MT5 clock), M15=1795428900 (2026-11-23T10:15:00Z MT5 clock)
- Bias: **BEARISH**; status: **WAIT_CONTEXT**; reason: `h4_against_short`

## 2. Structure / liquidity / POI / events

| TF | Regime (engine) |
|---|---|
| M15 | BEARISH |
| H4 | BULLISH |
| H1 | BULLISH |
| D1 | BEARISH |

- LTF structure: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BULLISH"}`
- Retest: `"OBSERVED"`
- Liquidity levels: **16**; POI: **536**; ICT events: **6**.
- Event states: ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID
- Chart objects: `{"event_markers": 15, "horizontal_lines": 16, "zones": 428}`.
- No per-zone lifecycle flag is invented; the engine does not expose one. No full OHLC bars are stored.

- Source files: `analysis.json`, `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`.
