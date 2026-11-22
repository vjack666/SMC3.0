# ICT 3.0 API — Captured Response Schemas

## Capture method

Server: `http://127.0.0.1:8766` (SMC/ICT 3.0 dashboard). Every request was sent with the
exact header `Host: 127.0.0.1:8766` (the server rejects other Host values) and
`curl --max-time 25`. Raw bodies were saved to `api_samples/<name>.raw` and the parsed
bodies re-serialized as pretty JSON (indent=2, UTF-8) to `api_samples/<name>.json`.

All schemas below were derived by walking the **actual** captured JSON with Python.
Only keys/values that were observed are listed. Nothing is inferred or invented.
Notation: `[NULL]` = JSON `null`, `[EMPTY]` = empty string/list/dict.

## Capture results at a glance

| # | Endpoint | File (`api_samples/`) | HTTP | Result |
|---|----------|-----------------------|------|--------|
| a | `/api/market-universe` | `market-universe.json` | 200 | success |
| b | `/api/poi-universe` | `poi-universe.json` | 200 | success |
| c | `/api/ict?symbol=EURUSD&tf=M15` | `ict_EURUSD_M15.json` | 200 | success |
| d | `/api/ict?symbol=EURUSD&tf=H4` | `ict_EURUSD_H4.json` | 200 | success |
| e | `/api/market?symbol=EURUSD&tf=M15` | `market_EURUSD_M15.json` | 200 | success |
| f | `/api/poi-history?summary=1` | `poi-history_summary.json` | **400** | error |
| g | `/api/poi-history?group=forex&summary=1` | `poi-history_group-forex_summary.json` | 200 | success |
| h | `/api/ict?symbol=GBPJPY&tf=M15` | `ict_GBPJPY_M15.json` | 200 | success (data present) |
| i | `/api/openings?symbol=EURUSD` | `openings_EURUSD.json` | **503** | error |
| j | `/api/journal` | `journal.json` | 200 | success |

### Endpoints that returned errors (exact bodies)

* `/api/poi-history?summary=1` → HTTP 400
  `{"error": "Indica entre 1 y 26 símbolos explícitos."}`
  (`summary=1` alone is rejected; explicit symbols are required. Adding
  `group=forex` as in endpoint (g) supplies them and returns 200.)
* `/api/openings?symbol=EURUSD` → HTTP 503
  `{"error": "Esperando una cotización reciente de EURUSD para comprobar la hora de MT5."}`

Both error bodies are a single object with one key `error: str` (populated). The
error text is Spanish and is reproduced verbatim above.

---

## Per-endpoint schemas

### (a) `/api/market-universe` — 200
```
total: int                         (33 in capture)
assets: dict[str, AssetStatus]     (33 keys; symbol -> status object)
  AssetStatus:
    last_closed: int
    error: null                    [NULL on every captured asset]
    checked_at: str                (ISO-8601 UTC timestamp)
intraday: dict[str, IntradayStatus]  (27 keys)
  IntradayStatus:
    state: str
    closed: int
    analyzed: int
    checked_at: str
    analysis_at: str
    errors: dict[str, str]         (often [EMPTY dict]; when populated contains
                                    key "openings" with a str message)
```
Observed: `assets.error` was `null` for all 33 assets; `intraday.errors` was an
empty dict for most symbols and `{ "openings": <str> }` for EURUSD.

### (b) `/api/poi-universe` — 200
```
forex: list[str]                   (26 entries, e.g. EURUSD, GBPJPY, ...)
indices: dict[str, str]            (4: GER40->GER30, NAS100->NDX100, SPX->SPX500, US30->US30)
commodities: dict[str, str]        (3: Oro->XAUUSD, Brent->UKOUSD, "US Oil · WTI"->USOUSD)
```

### (e) `/api/market?symbol=EURUSD&tf=M15` — 200
Wraps a full analysis payload (identical analysis shape to `/api/ict`) plus chart data:
```
symbol: str
frame: str
checked_at: str
last_success: str
last_tick_mt5: int
quote_age: null                    [NULL]
m15_closed: int
chart:
  digits: int
  rows: list[list[int]]            (550 rows of int arrays in capture)
analysis: Analysis                 (same structure as /api/ict top level, see below)
  ... keys: enabled, source, symbol, frame, time_basis, asof, latest_closed,
      bias, status, context_reason, regime, structure, retest, last_closed_by_tf,
      marks, pois, daily_liquidity, ict3_breaks, ict3, book22, friday_reference
analysis_at: str
errors: dict[str, str]             ({"openings": <str>} in capture)
state: str
```
Note: in this payload `ict3` has 3 top-level keys (`schema_version`, `mode`,
`events`) — the `load` block present in the standalone `/api/ict` responses is
**absent** here.

### (f) `/api/poi-history?summary=1` — 400 (error object only)
```
error: str
```

### (g) `/api/poi-history?group=forex&summary=1` — 200
```
results: list[Result]              (26 entries)
  Result:
    symbol: str
    engine_revision: str
    clock: str
    requested_start: str           (ISO-8601)
    cutoff: str                    (ISO-8601)
    first_closed_d1: str           (ISO-8601)
    last_closed_d1: str            (ISO-8601)
    has_history_before_window: bool
    closed_bars: int
    zone_count: int
    candidate_count: int
errors: dict                       [EMPTY dict]
```

### (i) `/api/openings?symbol=EURUSD` — 503 (error object only)
```
error: str
```

### (j) `/api/journal` — REDACTADO

Se omite el esquema del diario de cuenta porque contiene campos privados (datos financieros y de identificación). No es necesario para la interpretación del motor.


## (c)/(d)/(h) `/api/ict` — full analysis and `ict3` schema

Captured for `EURUSD/M15`, `EURUSD/H4`, `GBPJPY/M15`. All three share the same
top-level analysis shape; only leaf counts/values differ.

### Top-level analysis object
```
enabled: bool                     (true)
source: str
symbol: str
frame: str                        (M15 or H4, matches query)
time_basis: str
asof: int                         (epoch seconds)
latest_closed: int
bias: str
status: str
context_reason: str
regime: dict[str, str]            (D1, H1, H4, M15 — all populated)
structure:
  bars: int
  bos_dir: int                    (-1 / 1)
  momentum: int
  trend: str
retest: str
last_closed_by_tf: dict[str, int] (D1, H4, H1, M15)
marks: list[Mark]                 (137 EURUSD/M15, 122 GBPJPY; fewer in H4)
  Mark: id:str, tf:str, kind:str, direction:int, low:float, high:float,
        open:int, confirmed:int, touch:int, related:bool
  observed mark.tf values: M15 (M15 payloads), H4 (H4 payload)
  observed mark.kind values: FVG, OB
pois: list                        [EMPTY in all three captures]
daily_liquidity: DailyLiquidity
ict3_breaks: list[Break]          (10 EURUSD/M15, 12 GBPJPY)
  Break: session_open:int, source_open:int, level_name:str, level:float,
         direction:int, signal_open:int, signal_close:int, body_ratio:float,
         body_multiple:float, close_extension:float, close_location:float,
         strong_body:bool, strong_range:bool, strong_extension:bool, strong:bool,
         state:str, event_id:str, observed_at:int, state_time:int,
         accept_time:int, accept_open:int
ict3: Ict3
book22: list[BookItem]            (34 EURUSD/M15, 30 GBPJPY)
friday_reference:
  high: float
  low: float
  source_open: int
  source_close: int
```

### `daily_liquidity` — liquidity level objects
```
daily_liquidity:
  pdh: float
  pdl: float
  source_open: int
  session_open: int
  pdh_m15_open: int
  pdl_m15_open: int
  m15_count: int
  events: list[LiquidityLevelEvent]
```
`events` was `[EMPTY]` for both EURUSD samples and for the embedded analysis in
`/api/market`; it held 3 objects in `GBPJPY/M15`. The observed liquidity-level
object shape is exactly:
```
LiquidityLevelEvent:
  kind: str            # observed: "sweep", "break"
  level: str           # observed: "PDL"  (string, NOT the float of ict3.events.level)
  high: float
  low: float
  close: float
  close_side: null | str   # null for sweeps; "PDL" observed for one break
  time: int            # epoch seconds
```

### `book22` zone / confirmation fields
The first element does not always carry these, but across array elements the
following keys were observed in `book22` items (in addition to the base keys
`id, model, side, direction, alignment, level, h4_bias, source_d1, tick_size,
first_open, signal_open, signal_close, stop_anchor, stop_basis, sl, status,
reason, evaluated, session_open`):
```
confirmation: int
zone: str            (observed: "FVG")
zone_low: float
zone_high: float
displacement_close: int
```
Additional keys observed only in the GBPJPY `book22` items:
`entry: float`, `reference_open: int`, `reference_spread: float`,
`retest: int`, `retest_level: float`, `rr: float`, `target: str`, `tp: float`.
No `book22` key was observed with a `null` value.

### `ict3` block — every observed key
`ict3` top-level keys: `schema_version`, `mode`, `events`, `load`
(`load` is present in standalone `/api/ict` responses, absent in the `/api/market`
embedded analysis).

```
ict3:
  schema_version: str          # observed: "0.2-research"
  mode: str                    # observed: "OBSERVE_ONLY_NO_ORDER"
  events: list[Event]          # 5 (EURUSD M15), 5 (EURUSD H4), 7 (GBPJPY M15)
  load:                        # only in standalone /api/ict
    m5_loaded: bool
    m1_loaded: bool
    last_closed_m5: null       [NULL in all captures]
    last_closed_m1: null       [NULL in all captures]
    coverage:
      m5_bars_closed: int
      m1_bars_closed: int
      m5_first_closed: null    [NULL]
      m1_first_closed: null    [NULL]
      events_requested: int
    load_reason: str
```

#### `ict3.events[]` — all event fields (22 keys, union across all three captures)
Every event in every capture contained all 22 keys listed below.

| Key | Type | Observed values / notes |
|-----|------|-------------------------|
| `event_id` | str | event identifier |
| `symbol` | str | e.g. EURUSD / GBPJPY |
| `session_open` | int | epoch s |
| `observed_at` | int | epoch s |
| `state_time` | int | epoch s (snapshot time of current state) |
| `accept_time` | int | epoch s |
| `level_name` | str | `PDH`, `PDL` |
| `level` | float | price (note: distinct from `daily_liquidity.events[].level`, a str) |
| `direction` | int | `-1` or `1` |
| `force` | dict | see Force sub-object below |
| `link_state` | str | `accepted_with_poi`, `accepted_without_poi` |
| `current_state` | str | see state values below |
| `retest_at` | int **or null** | int when a retest occurred, `null` otherwise |
| `poi_candidates` | list[ZoneCandidate] | see zone fields below |
| `primary_poi` | str **or null** | e.g. `FVG_M15_46_BEAR`; `null` observed in some events |
| `transition_history` | list[Transition] | see snapshot fields below |
| `window_results` | dict | keyed by `"4"`, `"8"`, `"16"`, `"32"` |
| `observation_windows` | list[int] | `[4, 8, 16, 32]` |
| `pending_evidence` | list[str] | e.g. `["BREAK_INVALIDATED"]` |
| `wait_reason` | str | `BREAK_INVALIDATED`, `CAUSAL_POI_NOT_CONFIRMED` |
| `entry_authorized` | bool | `false` in all captured events |
| `mode` | str | `OBSERVE_ONLY_NO_ORDER` (present in `/api/ict` events; absent in the `/api/market` embedded events, which have 21 keys) |

**Force sub-object** (`force`, 5 keys, all populated, no nulls):
```
body_ratio: float
body_multiple: float
close_extension: float
close_location: float
strong: bool
```

**Link fields.** The only key whose name contains "link" is `link_state`
(values `accepted_with_poi` / `accepted_without_poi`). Linking to POIs is
expressed through `primary_poi` and the `zone_id` of each `poi_candidates`
entry. No other key with "link" in its name was observed anywhere in the
captured payloads.

**Zone fields** — `poi_candidates[]` (each entry = a zone candidate; 137 entries
in EURUSD/M15, 122 in GBPJPY/M15):
```
zone_id: str                 # e.g. FVG_M15_46_BEAR
kind: str                    # FVG, OB
direction: int               # -1 / 1
low: float
high: float
confirmed_at: int
first_touch_at: int or null  # null in captured candidates
association_reason: null or str  # null, or "same_direction; impulse_bar=... in_break_sequence=[...]; confirmed_at=...<=cutoff=..."
rejected_reason: null or str # null, or "impulse_after_break_sequence" / "impulse_before_break_sequence" / "opposite_direction"
```
These are the only "zone" fields inside `ict3`. (The `zone`, `zone_low`,
`zone_high` fields described above live in `book22`, outside the `ict3` block.)

**Snapshot fields.** There is no key literally named `snapshot` anywhere in the
captured payloads (verified by scanning all keys). The point-in-time snapshot
data are carried by:
* `state_time`, `accept_time`, `observed_at`, `retest_at` (epoch-second stamps),
* `transition_history[]`, each entry:
  ```
  from: str
  to: str
  at: int        (epoch s)
  reason: str    # first_touch_after_confirmation,
                 # close_through_structural_boundary_against_direction,
                 # m15_close_back_inside_level_before_retest
  ```
* `window_results` — a dict with keys `"4"`, `"8"`, `"16"`, `"32"` (the four
  observation windows). Each value has exactly 6 keys:
  ```
  window_bars: int       # 4 / 8 / 16 / 32
  retest_within: bool    # true / false observed
  state: str             # see state values below
  bars_observed: int
  window_complete: bool  # true in all captured windows
  horizon: int           (epoch s)
  ```

#### Event / window state values observed (exact strings)
Across `current_state`, `window_results.*.state`, `transition_history.*.to`
and `ict3_breaks[].state`:
```
ACCEPTED_BREAK_WAIT_RETEST
RETESTING_POI
POI_INVALID
ACCEPTANCE_LOST
EXPANSION_NO_ENTRY
```
`current_state` specifically took only: `ACCEPTED_BREAK_WAIT_RETEST`,
`POI_INVALID`, `ACCEPTANCE_LOST`.
`link_state` values: `accepted_with_poi`, `accepted_without_poi`.
`wait_reason` values: `BREAK_INVALIDATED`, `CAUSAL_POI_NOT_CONFIRMED`.
`entry_authorized` was `false` for all captured events.
`level_name` values: `PDH`, `PDL`.

#### Timeframes present
`D1`, `H4`, `H1`, `M15` (as keys of `regime` and `last_closed_by_tf`).
`frame` was `M15` or `H4` per the query. `mark.tf` values observed: `M15`
(in M15 payloads) and `H4` (in the H4 payload). `observation_windows` holds
integer bar windows `4, 8, 16, 32`, not timeframe labels.

#### Null / empty summary for `/api/ict`
* `[NULL]`: `daily_liquidity.events` (empty list in EURUSD samples — empty, not
  null); `daily_liquidity.events[].close_side` (null on sweeps);
  `poi_candidates[].first_touch_at`, `poi_candidates[].association_reason`,
  `poi_candidates[].rejected_reason` (nullable, null values observed);
  `event.retest_at`, `event.primary_poi` (nullable, null values observed);
  `ict3.load.last_closed_m5`, `ict3.load.last_closed_m1`,
  `ict3.load.coverage.m5_first_closed`, `ict3.load.coverage.m1_first_closed`
  (all null in every capture).
* `[EMPTY]`: top-level `pois` (empty list in all captures).
* All other observed leaves were populated.
