# ICT 3.0 engine — forensic source map (READ-ONLY audit)

Project root: `C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0`
Pinned ICT 2.0 authority: `REVISION = "f453bf2a9d35997cec774048a7ead25237399ac9"` (`ict.py:19-20`); `engine()` hard-fails if `SOURCE/.git/HEAD` differs (`ict.py:30-42`).
Mode invariant across the whole ICT3 stack: `OBSERVE_ONLY_NO_ORDER`, `entry_authorized=False`; no fills/lots/P&L/positions. `ict3_contract.FORBIDDEN_KEYS` and `ict3_oos.FORBIDDEN_KEYS` enforce this.

Method: direct source reading only; no source modified, no MT5 connection opened, no credentials used.

---

## 1. Operative / Partial / Experimental / Pending (with evidence)

| Module | Status | Evidence |
|---|---|---|
| `ict.py` `engine/read_bars/closed_frame/analyze_cached/analyze_bars/ict_chart/replay` | **OPERATIVE** (the live engine). Called by HTTP `smc.py:86-95` (`/api/chart`,`/api/ict`), by `motor_smc/servicio.py:10,227` panel refresh, by `test_ict.py` and 8+ `test_ict3_*` suites. | `ict_chart` → `analyze_bars` → `analyze_cached`; `@lru_cache(maxsize=20)` on `analyze_cached` (`ict.py:386`). |
| `ict.py` `classify_range_bar`, `daily_liquidity`, `daily_break_studies`, `break_event_id`, `last_friday_reference`, `candidate_pois`, `zone_payload`, `parent_event`, `ict3_payload` | **OPERATIVE** — all called inside `analyze_cached`/`analyze_bars` (`ict.py:424-462, 493-495`). | `ict3_payload` builds the versioned block; `daily_break_studies` is the event producer. |
| `ict3_link.py` (`associate_pois`, `advance_state`, `build_ict3_link`, `link_breaks`, `CAUSAL_IMPULSE_RULE`) | **OPERATIVE** — `ict.py:15,334` imports/calls `link_breaks(accepted, zones, m15, cutoff)`; state machine M15 fully implemented. | Modules docstring "solo observación"; 5 states; `DEFAULT_OBSERVATION_WINDOWS=(4,8,16,32)`. |
| `ict3_confirm.py` (`attach_confirmations`, `_closed_bars`, `_pivots`, `_structure`, `_defense`, `_stop`, `_known_liquidity`, `_target_policy`) | **OPERATIVE** — `ict.py:16,483` calls it; M5/M1 evidence appended on demand. | C1–C8 rules in docstring `ict3_confirm.py:21-84`. |
| `ict3_contract.py` (`describe`, `validate`, `assert_valid`, `classify_wait`, `Field`, `CATALOG`) | **OPERATIVE as validator/dictionary only** — pure, no producer. Imported by `test_ict3_contract_dictionary.py`, `test_ict3_cutoff_asof.py`; used by docs generation. Not called from the live HTTP path (`grep` shows no import in `smc.py`/`ict.py`). | `CONTRACT_VERSION="1.0"`, `SCHEMA_VERSION="0.2-research"`. |
| `poi_history.py` (`analyze_poi_history`, `zone_lifecycle`, `scan_poi_history`) | **OPERATIVE** on the historical D1 endpoint `GET /api/history` (`smc.py:108-111`), independent of the `ict3` block. D1 FVG/OB candidates + `untouched/retested/wick_breach/invalidated_by_close`. | `poi_history.py:40-120`; 2-year window `window_start()`. |
| `motor_smc/servicio.py` (`MarketPanel`) + `motor_smc/mt5_feed.py` | **OPERATIVE** — background panel polling, stale detection, on-demand `analyze_bars`. `mt5_feed.py` is a 53-line read helper, nothing more. | `servicio.py:9-13,184-255`; `mt5_feed.py:9-53`. |
| `ict22.py` (`book22_setups`, Session/Observer) | **OPERATIVE but annotation-only** — exposed in `result["book22"]`; produces `discarded/waiting/qualified` setups with `entry`, `sl`, `tp`, `rr` used as *chart annotations only* (module docstring `ict22.py:1`). It is the legacy Book 22 layer, not the `ict3` contract. | `ict.py:438-443`, `ict.py:464`. |
| `ict3_oos.py` | **EXPERIMENTAL / PROTOCOL-ONLY**. Pure deterministic synthetic generator; `build_report()` emits `declared_synthetic=True`, `real_coverage=REAL_COVERAGE_PENDING`; `refuse_execution_metrics()` raises. Not wired into any HTTP endpoint. | `ict3_oos.py:1-22,46-47,453-501`; only imported by `test_ict3_oos.py`. |
| `ict3_simulation.py` | **EXPERIMENTAL / REPORT-GENERATOR**. Standalone `main()` that writes `docs/research/ICT3_SIMULACION_26_PARES.md` from MT5 max-history replay of `daily_break_studies` only; "not a backtest" (`ict3_simulation.py:1-5`). Writes a docs file when run; not part of the live analysis path. | `M15_REQUEST=5000`, `D1_REQUEST=2000`; script never imported by `smc.py`. |
| Fase 8 integration status | **PENDING (marked `[~]`)** — `REVISION_FASE_08_CORRECCIONES.md:40-54`: MT5 freshness remains blocked (`state=stale`, `REAL_COVERAGE_PENDING`); tests 161/161 + UI 13/13; "Fase 8 permanece `[~]` ... solo `[x]` con evidencia". | `PLAN_HERMES_REVISION_IA.md:63-77,204-209`. |
| `docs/ict3/00_INDICE_PLAN_CONTINUO_HERMES.md` | all 8 phases shown `[ ]` — stale index; authoritative statuses live in `PLAN_HERMES_REVISION_IA.md` (Tareas 1-7 `[x]`, Tarea 8 `[~]`). | Discrepancy noted in §10. |

---

## 2. Exact JSON schema of `ict_chart()` / `analyze_cached()`

`ict_chart(settings, symbol, frame, cutoff=None)` (`ict.py:467-483`):
- If `symbol not in MT5_SYMBOLS`: `{"enabled": false, "reason": "ICT automático se aplica al universo confirmado de MT5."}`.
- Else reads bars for `tuple(dict.fromkeys((*PROFILE, frame)))`, calls `analyze_bars(symbol, frame, source, cutoff)`, then conditionally loads M5/M1 and returns `attach_confirmations(result, lower, as_of, loader_error=...)`.

`analyze_bars` (`ict.py:486-495`) = `analyze_cached(...)` minus `ltf_zones` and `sequence`, plus `friday_reference`.

`analyze_cached` top-level keys (`ict.py:446-464`):

| key | type | source/meaning |
|---|---|---|
| `enabled` | bool | always `True` |
| `source` | str | `REVISION` sha |
| `symbol` | str | query symbol |
| `frame` | str | selected TF (`M15` typical) |
| `time_basis` | str | `"Reloj MT5"` |
| `asof` | int epoch | `decision_epoch`: cutoff if given else last closed M15 |
| `latest_closed` | int/null | last closed bar of selected frame |
| `bias` | str | `snapshot["direction_label"]` (`BULLISH`/`BEARISH`/`RANGING`) |
| `status` | str | daily_motor status e.g. `WAIT_RETEST`, `OBSERVABLE_SETUP` |
| `context_reason` | str | `snapshot["context"]["reason"]` |
| `regime` | object | `snapshot["context"]["regime_stack"]` |
| `structure` | object | `snapshot["ltf"]["structure"]` `{trend,bos_dir,momentum,bars}` |
| `retest` | str/object | `snapshot["ltf"]["retest_state"]` |
| `sequence` | object | feed sequence; **removed** by `analyze_bars` |
| `last_closed_by_tf` | object | `{tf: closed_epoch}` for PROFILE |
| `ltf_zones` | list | zone_payloads M15; **removed** by `analyze_bars` |
| `marks` | list | zone payloads for selected frame, `related` flag set |
| `pois` | list | `candidate_pois(...)` top 3, `kind:POI` + base FVG/OB + parent/anchor/evaluated |
| `daily_liquidity` | object/null | `daily_liquidity()` result (see §5) |
| `ict3_breaks` | list | flat legacy `daily_break_studies` output, unchanged |
| `ict3` | object | versioned block, see below |
| `book22` | list | Book22 annotation setups |
| `friday_reference` | object/null | added by `analyze_bars` from `last_friday_reference()` |

### Full nested `ict3` block

Producer `ict3_payload()` (`ict.py:331-383`) returns `{schema_version:"0.2-research", mode:"OBSERVE_ONLY_NO_ORDER", events:[...]}`; `attach_confirmations()` (`ict3_confirm.py:371-388`) adds `load` and reasserts `mode` on block and each event. Contract mirror: `ict3_contract.TOP_LEVEL / EVENT / LOAD / COVERAGE / TRANSITION / LIQUIDITY` (`ict3_contract.py:53-130`), doc form in `CONTRATO_ICT3_DICCIONARIO.md` and `FASE_05_DICCIONARIO_CAMPOS.md`.

Top level:
- `schema_version` str, `mode` str, `events` list[object], `load` object.

`events[]` base keys built by `ict3_payload`:
- `event_id` str — deterministic sha256 id.
- `symbol` str; `session_open` int; `observed_at` int; `state_time` int; `accept_time` int|null.
- `level_name` str (`PDH`/`PDL`); `level` number; `direction` int (+1/-1).
- `force` object: `{body_ratio:number, body_multiple:number|null, close_extension:number|null, close_location:number, strong:bool}`.
- `link_state` str (`accepted_with_poi` / `accepted_without_poi`); `current_state` str.
- `retest_at` int|null; `poi_candidates` list; `primary_poi` str|object|null; `transition_history` list; `window_results` object; `observation_windows` list[int] `[4,8,16,32]`.
- `pending_evidence` list[str]; `wait_reason` str; `entry_authorized` bool always `false`; `mode` str always `OBSERVE_ONLY_NO_ORDER`.
- `poi_candidates[]` (`ict3_link._new_candidate`): `{zone_id:str, kind:str 'FVG'|'OB', direction:int, low:number, high:number, confirmed_at:int|null, first_touch_at:int|null, association_reason:str|null, rejected_reason:str|null}`.
- `window_results` map keyed `"4","8","16","32"` → `{window_bars:int, retest_within:bool, state:str, bars_observed:int, window_complete:bool, horizon:int|null}`.
- `transition_history[]`: `{from:str, to:str, at:int, reason:str}`.

Confirmation sub-block (`CONFIRMATION_FIELDS`, added by `attach_confirmations` only to events that were in `RETESTING_POI` and not terminal — all-or-nothing):
`confirmation_state` str (`WAIT_M5_M1_CONFIRMATION`|`M5_STRUCTURE_CONFIRMED`), `defense_at` int|null, `m5_structure_kind` str|null (`BOS|CHOCH|MSS`), `m5_structure_at` int|null, `m1_structure_kind` str|null, `m1_structure_at` int|null, `stop_basis` str (`ORIGIN_SWING_INTACT|M5_REACTION_EXTREME|M1_CONFIRMED_EXTREME|NO_STRUCTURAL_STOP`), `stop_price` number|null, `stop_observed_at` int|null, `target_policy_status` str (`NO_STRUCTURAL_REFERENCE|NO_STOP_NO_RISK_UNIT|NO_KNOWN_LIQUIDITY_AT_CUTOFF|TP1_BELOW_3R|TP2_BELOW_5R|SATISFIED_TP1_3R_TP2_5R`), `target_price` number|null, `target_liquidity` list `{kind:'BROKEN_LEVEL'|'M5_SWING'|'M1_SWING', price:number, observed_at:int}`, plus `reason` str appended by `_finish` (`FASE_05_DICCIONARIO_CAMPOS.md:115` documents `reason`; it is not in `EVENT` catalog).

`load` object: `{m5_loaded:bool, m1_loaded:bool, last_closed_m5:int|null, last_closed_m1:int|null, coverage:{m5_bars_closed:int, m1_bars_closed:int, m5_first_closed:int|null, m1_first_closed:int|null, events_requested:int}, load_reason:str}`.
`load_reason` values: `NOT_REQUESTED_NO_M15_RETEST`, `LOWER_SOURCE_UNAVAILABLE`, `LOWER_SOURCE_MALFORMED`, `LOWER_SOURCE_ERROR: …`, `NO_CLOSED_M5_BARS_AT_CUTOFF`, `M1_BARS_UNAVAILABLE_M5_USED`, `M5_M1_LOADED`.

`ict3_contract.classify_wait()` yields `SIN_RETEST|DATOS_AUSENTES|EVIDENCIA_INSUFICIENTE|SIN_ESPERA`.

---

## 3. POI types, lifecycle, authority_tf / origin_tf

- Canonical `ObjectType` (`market_object.py:16-28`): `BOS, CHOCH, FVG, ORDER_BLOCK, LIQUIDITY, SWEEP, DISPLACEMENT, RETURN, CONTRACT, CANDLE, BREAKER, BPR`. `ict3` uses only **FVG** and **OB** (`_zone_kind`: `FVG` → `FVG`, `ORDER_BLOCK|OB` → `OB`; `oos.POI_TYPES=("FVG","OB")`).
- `Role`: `POI|REFINEMENT|EXECUTION|CONTEXT`. `_POI_TFS={"D1","H4","H1"}` and `__post_init__` rejects `role==POI` outside those TFs (`market_object.py:48,110-114`). Therefore M15 zones consumed by `ict3_link` (it demands `origin_tf=="M15"`, `ict3_link.py:260`) are canonical **REFINEMENT** objects surfaced as `poi_candidates`; the word POI here is the ICT3 observation label, not the ICT2 `Role.POI`.
- `MarketObject` lifecycle (`ObjectState`, `market_object.py:38-76`): `CREATED → ACTIVE → PARTIALLY_MITIGATED → MITIGATED` and `INVALIDATED / EXPIRED / CONSUMED`; terminal = `{MITIGATED, INVALIDATED, EXPIRED, CONSUMED}`. `ltf_canonical_feed._touch_state` sets `ACTIVE → PARTIALLY_MITIGATED` on first closed bar after `tradable_time` whose range overlaps the zone (`ltf_canonical_feed.py:46-56`).
- `poi_history.zone_lifecycle` (D1, separate endpoint) states: `untouched → retested → wick_breach → invalidated_by_close` (`poi_history.py:40-65`), with `contact_bars`, `contact_episodes`, `contact_dates`.
- ICT3 break/link states (`ict3_link.py:95-99`, `ict3_confirm.py:91-95`):
  - `BREAK_CANDIDATE`, `FAILED_BREAK` — from `daily_break_studies` (`ict.py:239,247`).
  - `ACCEPTED_BREAK_WAIT_RETEST` → `RETESTING_POI | ACCEPTANCE_LOST | POI_INVALID | EXPANSION_NO_ENTRY`; `RETESTING_POI → POI_INVALID | OBSERVABLE_SETUP`. Terminal: `ACCEPTANCE_LOST`, `POI_INVALID`, `EXPANSION_NO_ENTRY`, `OBSERVABLE_SETUP`. Deterministic precedence per closed M15 bar: loss of broken daily level → POI structural boundary → geometric retest (`ict3_link.py:406-420`). `confirmation_state` values `WAIT_M5_M1_CONFIRMATION / M5_STRUCTURE_CONFIRMED` are a separate axis, not `current_state`.
  - `OBSERVABLE_SETUP` still has `entry_authorized=False` (`ict3_confirm.py:494-504`).
- `origin_tf`: mandatory "layer stamp" (`market_object.py:111-112`), set from the detector's `timeframe` (`fvg.py:24,30`; `ob.py:35`). `daily_motor._canonical_zone_state` consumes only `obj.origin_tf == exec_tf` and `tradable <= decision_time` (`daily_motor.py:182-195`); `ict3_link.associate_pois` only `origin_tf.upper()=="M15"`.
- `authority_tf`: **not an ICT3 field**. It appears only in the pinned ICT2 Wyckoff adapter/types (`Wyckoff/adapter.py:46,63-88`, `types.py:99,115`) and in `daily_motor._wyckoff_payload` (`daily_motor.py:328,340`). With `ict.py` never passing `wyckoff_snapshot`, its ICT3 value is `null` inside an unavailable Wyckoff payload.

---

## 4. Liquidity types and daily / weekly / monthly level definitions

**Actually implemented in ICT3 (`ict.py`):**
- `daily_liquidity()` (`ict.py:117-144`) — PDH/PDL = high/low of the **previous broker D1 session** (`previous_daily` takes last two D1 rows `<= cutoff`), M15 candles of the **current session** classified by `classify_range_bar` (`ict.py:86-114`) into kinds: `both`, `gap`, `break`, `late_return`, `sweep`, `boundary_close`, `touch`; output `{pdh,pdl,source_open,session_open,pdh_m15_open,pdl_m15_open,m15_count,events[]}`.
- `last_friday_reference()` (`ict.py:147-160`) — newest fully closed **Friday D1** high/low, exposed only as `friday_reference` by `analyze_bars`. This is a weekly anchor reference, not a weekly PDH/PDL series.
- `ict3_confirm._known_liquidity()` — `BROKEN_LEVEL` (level at `accept_time`), `M5_SWING`, `M1_SWING` (confirmed pivots), all with `observed_at <= cutoff`.
- **No weekly and no monthly liquidity level definitions exist in code** (targeted grep for `weekly|monthly|PDW|PWH|PWL|PMH|PML` over project `.py` returned no implementation hits; only a prose mention in `docs/ict3/01_RUPTURA_FUERTE_LIQUIDEZ_DIARIA.md:183` of "niveles diarios o semanales ya cerrados"). The only `ict3_oos` levels are `LEVELS=("PDH","PDL")`.
- The pinned ICT2 source contains BSL/SSL detectors (`detectors/liquidity.py`, `engine/liquidity_levels.py`, `engine/liquidity_internal_external.py`, `engine/micro.py`) with IRL/ERL classification — **not imported** by `ict.py.engine()`, therefore not part of the ICT3 engine output.

---

## 5. Event types, IDs, causal relationships, confirmation states

- Break event id (`ict.py:163-171`): `"evt_" + sha256("symbol|session_open|level_name|level|direction|signal_open|signal_close")[:16]` — deterministic per symbol/D1 session/level/side/signal bar.
- Zone id (`ict.py:274-282`): `f"{origin_tf}-{timestamp(confirmation_time)}-{obj.type.value}-{direction}"`.
- Book22 id (`ict22.py:91`): `f"{bar.opened}-{model}-{level_name}"`, models `reversal|turtle_soup|continuation`, statuses `discarded|waiting|qualified`, reasons `no_stop_structure|broken_stop_structure|insufficient_history|no_mss_pivot|no_retest|session_ended|await_reference|reference_invalid|invalid_risk|no_target|below_rr|above_rr|in_range|gap|stop_hit|range_lost|break_lost|no_mss_zone|no_displacement_zone|no_retest` — annotations only.
- Causality: `CAUSAL_IMPULSE_RULE` (`ict3_link.py:101-106`) — FVG `meta["middle_bar"]` / OB `meta["followthrough"]` (fallback `confirmation_bar`) must lie in closed-M15 index window `[signal_bar, accept_bar]`, measured by bar index, **not price proximity**; confirmation may be one bar after impulse but must be `<= cutoff`. Rejection reasons: `not_m15_zone`, `confirmation_time_unavailable`, `confirmed_after_cutoff`, `opposite_direction`, `impulse_bar_unavailable`, `break_sequence_unavailable`, `impulse_before_break_sequence`, `impulse_after_break_sequence`. Primary POI = most recent causal impulse, tie-break by confirmation then `zone_id` (`ict3_link.py:299-302`).
- M15 state causality: `at` of each transition = a closed M15 bar; `EXPANSION_NO_ENTRY` at exact close of widest window (32 bars) is terminal; window results only use transitions `at <= horizon` (`ict3_link.py:375-465`).
- Confirmation states (M5/M1): `WAIT_M5_M1_CONFIRMATION` → `M5_STRUCTURE_CONFIRMED` (when defense + M5 structure) → `OBSERVABLE_SETUP` (only if defense + M5 structure + structural stop + target policy satisfied + known price) (`ict3_confirm.py:462-507`). BOS/CHOCH/MSS classification rule C3: previous confirmed swing low/high broken by a **closed** M5 bar; prior pivot lower/higher → BOS, opposite → CHOCH, none/tie → MSS.

---

## 6. `at` cutoff, no look-ahead, `snapshot_at`

- HTTP `smc.py:92-95`: `cutoff = int(query["at"][0]) if "at" in query else None`, validated `0 < cutoff < 4102444800`, forwarded to `ict_chart`. `/api/history` accepts `at` or `date` (`smc.py:108-111`, `poi_history.date_cutoff`).
- `closed_frame()` (`ict.py:62-74`) requires a successor bar and `closed = min(opened+SECONDS[tf], successor)` and keeps only `closed <= cutoff` — position-zero live bar is never emitted.
- `analyze_cached()` anchors `decision_epoch = cutoff or last-closed-M15` and truncates every context frame to `closed <= decision_epoch` (`ict.py:395-401`); `level_cutoff = max(decision_epoch, last D1 open)` when no explicit cutoff, else `decision_epoch` (`ict.py:426`); `breaks`, `daily_liquidity`, `ict3_payload` all use `level_cutoff`.
- `ict_chart.as_of = cutoff if cutoff is not None else int(time.time())` (`ict.py:475`) is the **wall clock** passed to `attach_confirmations`, whose `_closed_bars` keeps M5/M1 only if `opened + SECONDS[tf] <= cutoff` (`ict3_confirm.py:106-124`).
- Two-clock rule documented in `docs/ict3/CUTOFF_ASOF_REGLA_CAUSAL.md` and `ict3_contract.validate` docstring (`ict3_contract.py:235-258`): `result['asof']` anchors the D1/M15 snapshot; `load.last_closed_m5/m1` and `target_liquidity[].observed_at` may exceed `asof` when MT5 is stale because they obey the construction wall-clock — validating with `asof` produced 4 false positives in US30; with the real construction cutoff, 0.
- **`snapshot_at` does not exist anywhere in the project** (full grep of `.py/.js/.md/.html`, excluding venv/.git, 0 hits). The concept is expressed as `at` (HTTP param), `cutoff` (function arg), `decision_epoch` / `result['asof']` (M15 anchor), and `decision_time` in pinned engine. `ict3_oos.verify_prefix_invariance` demonstrates `prefix_to_t == full_series_at_t`.

---

## 7. M5/M1 confirmation integration

`ict_chart` computes `needs_lower = any(event.current_state == "RETESTING_POI" for event in result["ict3"]["events"])` (`ict.py:473-474`). Only then does it call `read_bars(settings, symbol, ("M5","M1"))`; otherwise `loader_error="NOT_REQUESTED_NO_M15_RETEST"` and the whole confirmation block stays empty (`load.events_requested=0`). `attach_confirmations` ignores terminal states (`_TERMINAL`) and non-retesting events, sets `entry_authorized=False`/`mode` on all events, and on loader failure emits `WAIT_M5_M1_CONFIRMATION` with explicit `load_reason` and no invented pivots. M1 is corroboration only — `_structure` results feed `m1_structure_kind/at` but never replace M5; stop authority order is ORIGIN_SWING_INTACT > M5_REACTION_EXTREME > M1_CONFIRMED_EXTREME > NO_STRUCTURAL_STOP. Target policy uses an informative `R = |structural reference - stop|` (reference = defense M5 close else M5 structure close, never an entry); TP1≥3R, TP2≥5R.

---

## 8. AHF / Wyckoff / Market State / Setup Builder — explicit status

- **AHF** (`Adaptive Hierarchical MTF Funnel`): **EXISTS in the pinned ICT2 source** (`motor_smc/fuentes/ict2/engine/ahf.py`, states incl. `WAIT_D1/WAIT_H4/WAIT_H1/WAIT_LTF/SETUP_READY`, `AHFEvent`), but is **NOT operative in ICT 3.0**: `ict.py.engine()` imports only `engine.bos`, `engine.daily_motor`, `engine.ltf_canonical_feed`, `engine.plan.dealing_range_pd`, `tools.displacement` (`ict.py:36-42`). `build_daily_motor_snapshot` receives no `navigation_snapshot` from `ict.py`, so `snapshot["navigation"]` is `available:false, state:null` (`daily_motor.py:242-253,390`).
- **Wyckoff**: **EXISTS in the pinned source** (`engine/Wyckoff/{adapter,classifier,effort_result,events,phases,types}.py`, `build_wyckoff_snapshot(authority_tf="D1")`), and `daily_motor` exposes a `wyckoff` key. `ict.py` never passes `wyckoff_snapshot`, so ICT3 output is `{available:false, phase:"UNKNOWN", authority_tf:null, volume_mode:"UNAVAILABLE", explanation:"wyckoff_snapshot_unavailable"}` (`daily_motor.py:320-352,365,393,525`).
- **Market State**: the canonical `MarketState` / context_state engine exists in the pinned source (`daily_motor._context_state_payload`, `context.market_state`, `constraints allow_long/allow_short`) but `ict.py` passes neither `context_state` nor `context_snapshot`; `snapshot["context"]["state"]="DERIVED_STACK"`, `market_state=None`, gating falls back to `top_down_allows_trade(...)` on the derived D1/H4/H1 stack (`daily_motor.py:400-432,528-540`). No "MarketState" object is produced or exposed by ICT3.
- **Setup Builder**: **NO module named `setup_builder` / `SetupBuilder` exists** (project-wide grep: 0 hits). `SETUP_READY` exists only as an AHF state in the unused pinned source. The operative ICT3 substitutes are `candidate_pois()` (top-3 candidate POIs), `book22_setups()` (legacy annotation setups), and the `OBSERVABLE_SETUP` observation state — none builds an order, size or fill.

---

## 9. Discrepancies docs vs code

1. `docs/ict3/00_INDICE_PLAN_CONTINUO_HERMES.md:18-25` marks all 8 phases `[ ]`, while `PLAN_HERMES_REVISION_IA.md:63-70` marks Tareas 1-7 `[x]` and Tarea 8 `[~]`; the index is stale.
2. `REVISION_FASE_08_CORRECCIONES.md:5` "suite local pasa 161/161", but point 1 (fresh MT5 quote) is a delivered **blocker**, not a pass; Fase 8 remains `[~]`. Live ICT3 output is stale (`state=stale`, `REAL_COVERAGE_PENDING`).
3. `CONTRATO_ICT3_DICCIONARIO.md` / `ict3_contract.EVENT` omit `reason` (added by `attach_confirmations._finish`) and omit the nested shapes of `force`, `poi_candidates`, `window_results`; `FASE_05_DICCIONARIO_CAMPOS.md` documents `reason` but not all `pending_evidence` strings actually emitted (`STRUCTURAL_STOP_NOT_DEFINED` placeholder is stripped from processed events; `RETEST_EVIDENCE_INCOMPLETE`, `M5_M1_CONFIRMATION_NOT_COMPLETE`, `DEFENSE_NOT_CONFIRMED_M5`, `M5_STRUCTURE_NOT_CONFIRMED`, `NO_STRUCTURAL_STOP`, `TARGET_POLICY_*`, `BREAK_INVALIDATED`, `CAUSAL_POI_NOT_CONFIRMED`, `NO_RETEST_WITHIN_COMPARABLE_WINDOWS` are produced in code).
4. `ict3_contract.EVENT.confirmation_state` doc says only `WAIT_M5_M1_CONFIRMATION|M5_STRUCTURE_CONFIRMED`; `M5_STRUCTURE_CONFIRMED` is set when defense+M5 structure exist, while full `OBSERVABLE_SETUP` additionally requires stop + target policy — a state transition subtlety the doc flattens.
5. `ict3_simulation.py` "Mejoras siguientes" proposes adding `RETESTING_POI`, `OBSERVABLE_SETUP`, `EXPANSION_NO_ENTRY`, `INVALIDATED` to the payload — these already exist in `ict3_link`/`ict3_confirm`; the simulation doc text lags the engine.
6. `docs/ict3/01_RUPTURA_FUERTE_LIQUIDEZ_DIARIA.md:183` mentions weekly closed levels ("niveles diarios o semanales ya cerrados") but only a Friday D1 reference and PDH/PDL are implemented; no weekly/monthly level engine.
7. `ict3_contract.validate` docstring notes that using `result['asof']` as `cutoff` on a no-`at` payload yields false "post-cutoff" issues; docs uniformly say "ningún instante publicado es posterior al corte" without stating which clock, hence the US30 4-issue episode.
8. `snapshot_at` appears in no doc or code; anyone expecting that key/field will not find it. The equivalent is `at` / `cutoff` / `asof`.
