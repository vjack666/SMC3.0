# Fase 5 — Diccionario de campos del bloque `ict3`

Contrato de solo lectura del bloque versionado expuesto por `GET /api/ict`.
Describe el esquema **ya producido** por `ict.ict3_payload` +
`ict3_confirm.attach_confirmations` sobre los resultados de
`ict.analyze_cached`. No define rutas nuevas y no modifica `ict.py`, `smc.py`
ni `data/`.

- `schema_version`: `0.2-research`
- `mode`: `OBSERVE_ONLY_NO_ORDER` (invariante en bloque y en cada evento)
- Claves prohibidas en **cualquier** nivel: `entry`, `order`, `fill`, `lots`,
  `volume`, `pnl` (y, por extensión, `position`, `cash_value`, `balance`,
  `equity`, `margin`, `ticket`, `deal`). Ninguna aparece nunca.
- Tiempos: epoch Unix en segundos, derivado de velas **cerradas** con
  `closed <= cutoff`. Ningún instante publicado es posterior al corte.
- Precios: unidades del activo (pips/precio MT5); `número` = `int | float`,
  nunca `bool`.

## 1. Bloque `ict3` (nivel superior)

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `schema_version` | `str` | — | no | `ict3_payload` (interno) | Versión del contrato. Hoy `0.2-research`. |
| `mode` | `str` | — | no | `ict3_payload`, reafirmado por `attach_confirmations` | Siempre `OBSERVE_ONLY_NO_ORDER`. |
| `events` | `list[objeto]` | — | no | `daily_break_studies` → `ict3_link.link_breaks` → `attach_confirmations` | Uno por ruptura diaria aceptada; puede estar vacío. |
| `load` | `objeto` | — | no | `attach_confirmations` | Estado de la carga M5/M1 bajo demanda. |

## 2. Eventos — campos base

Presentes en **todo** evento. El subbloque de confirmación (§3) aparece solo
en eventos que alcanzaron `RETESTING_POI`, como bloque todo-o-nada.

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `event_id` | `str` | — | no | `daily_break_studies` / `break_event_id` | Identificador determinista de la ruptura. |
| `symbol` | `str` | — | no | parámetro `symbol` de la consulta | Activo observado (p. ej. `EURUSD`). |
| `session_open` | `int` | epoch s | no | D1 (`day[0]`) | Apertura de la sesión diaria que contiene la ruptura. |
| `observed_at` | `int` | epoch s | no | M15 cerrada (`bar.closed`) | Primer cierre fuera del nivel: cuándo se conoció el evento. |
| `state_time` | `int` | epoch s | no | máquina de estados; `attach_confirmations` lo actualiza si pasa a `OBSERVABLE_SETUP` | Instante del estado actual. |
| `accept_time` | `int` | epoch s | sí | M15 cerrada | Segundo cierre fuera: aceptación de la ruptura. `null` si nunca se aceptó. |
| `level_name` | `str` | — | no | D1 | `PDH` o `PDL`. |
| `level` | `número` | precio | no | D1 (máx./mín. de la sesión anterior) | Nivel de liquidez roto. |
| `direction` | `int` | `+1`/`-1` | no | D1 + M15 | Sentido de la ruptura. |
| `force` | `objeto` | — | no | cuerpo/rango de la vela M15 de señal | Medidas de fuerza (§2.1). |
| `link_state` | `str` | — | no | `ict3_link.associate_pois` | `accepted_with_poi` o `accepted_without_poi`. No cambia `current_state`. |
| `current_state` | `str` | — | no | máquina de estados M15; `attach_confirmations` | `ACCEPTED_BREAK_WAIT_RETEST`, `RETESTING_POI`, `ACCEPTANCE_LOST`, `POI_INVALID`, `EXPANSION_NO_ENTRY` u `OBSERVABLE_SETUP`. |
| `retest_at` | `int` | epoch s | sí | M15 cerrada | Cierre de la primera vela que toca la POI primaria tras su confirmación. `null` si no hubo retest. |
| `poi_candidates` | `list[objeto]` | — | no | `ict3_link.associate_pois` (FVG/OB ICT 2.0) | Zonas canónicas con auditoría de asociación (§2.2). |
| `primary_poi` | `str` \| `objeto` \| `null` | — | sí | `ict3_link` (`zone_id`), o id heredado | Zona elegida por impulso causal más reciente, nunca por precio. |
| `transition_history` | `list[objeto]` | — | no | `ict3_link.advance_state` (+ `attach_confirmations`) | Transiciones ordenadas (§4). |
| `window_results` | `objeto` | — | no | `ict3_link.advance_state` | Resultado comparable por ventana (§2.3). |
| `observation_windows` | `list[int]` | velas M15 | no | `ict3_link` | Ventanas usadas, por defecto `[4, 8, 16, 32]`. No son normativas. |
| `pending_evidence` | `list[str]` | — | no | `ict3_payload` + `attach_confirmations` | Evidencia que falta; nunca se inventa. Ver §6. |
| `wait_reason` | `str` | — | no | motor | Unión de `pending_evidence` con `; `, o `OBSERVATION_ONLY` si no falta nada. |
| `entry_authorized` | `bool` | — | no | política | **Siempre `False`.** No autoriza entrada ni orden. |
| `mode` | `str` | — | no | política (`attach_confirmations`) | **Siempre `OBSERVE_ONLY_NO_ORDER`.** |

### 2.1 `force` — medidas de la vela de señal

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `body_ratio` | `número` | ratio `0..1` | no | cuerpo/rango M15 | `abs(close-open)/rango`. |
| `body_multiple` | `número` | × rango medio | sí | cuerpo / rango medio de 14 velas | `null` si no hay rango medio. |
| `close_extension` | `número` | × rango medio | sí | cierre respecto al nivel | `null` si no hay rango medio. |
| `close_location` | `número` | ratio `0..1` | no | posición del cierre en la vela | Dónde cerró la vela dentro de su rango. |
| `strong` | `bool` | — | no | umbrales `0.70 / 1.5 / 0.50` | `true` si cuerpo, rango y extensión superan umbral. |

### 2.2 Elemento de `poi_candidates`

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `zone_id` | `str` | — | no | objeto FVG/OB (`id`) | Identificador de la zona canónica. |
| `kind` | `str` | — | no | `type.value` | `FVG` u `OB`. |
| `direction` | `int` | `+1`/`-1` | no | objeto FVG/OB | Debe coincidir con la ruptura. |
| `low` | `número` | precio | no | `zone_low` | Límite inferior de la zona. |
| `high` | `número` | precio | no | `zone_high` | Límite superior de la zona. |
| `confirmed_at` | `int` | epoch s | sí | `confirmation_time` | Cuándo era conocible; `null` si no disponible. |
| `first_touch_at` | `int` | epoch s | sí | recomputado sobre velas cerradas | Primer toque tras la confirmación. |
| `association_reason` | `str` | — | sí | `CAUSAL_IMPULSE_RULE` | Por qué es candidata válida; `null` si se rechazó. |
| `rejected_reason` | `str` | — | sí | `ict3_link` | `not_m15_zone`, `confirmed_after_cutoff`, `opposite_direction`, `impulse_bar_unavailable`, `impulse_before_break_sequence`, etc. |

### 2.3 Elemento de `window_results`

Claves: `"4"`, `"8"`, `"16"`, `"32"` (ventanas M15 posteriores a la aceptación).

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `window_bars` | `int` | velas | no | ancho de ventana | Número de velas comparadas. |
| `state` | `str` | — | no | transiciones `at <= horizon` | Estado observable dentro de esa ventana. |
| `retest_within` | `bool` | — | no | transiciones | Si hubo transición a `RETESTING_POI` dentro del horizonte. |
| `bars_observed` | `int` | velas | no | marco cerrado | Velas realmente disponibles. |
| `window_complete` | `bool` | — | no | marco cerrado | Si la ventana está completa al corte. |
| `horizon` | `int` | epoch s | sí | cierre de la última vela de la ventana | `null` si la ventana no está completa. |

## 3. Eventos — subbloque de confirmación M5/M1

Aparece **completo o no aparece**. Se añade cuando `attach_confirmations`
procesa un evento en `RETESTING_POI`. Ningún campo crea entrada, stop
operativo, objetivo monetario ni lotaje.

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `confirmation_state` | `str` | — | no | M5/M1 | `WAIT_M5_M1_CONFIRMATION` o `M5_STRUCTURE_CONFIRMED`. |
| `defense_at` | `int` | epoch s | sí | M5 cerrada | Cierre de la primera vela que defiende la POI/nivel tras el retest. |
| `m5_structure_kind` | `str` | `BOS`/`CHOCH`/`MSS` | sí | M5 cerrada (regla C3) | Estructura confirmada **por cierre**, no por mecha. |
| `m5_structure_at` | `int` | epoch s | sí | M5 cerrada | Cierre de la vela de ruptura M5. |
| `m1_structure_kind` | `str` | `BOS`/`CHOCH`/`MSS` | sí | M1 cerrada | Corroboración opcional; nunca sustituye a M5. |
| `m1_structure_at` | `int` | epoch s | sí | M1 cerrada | Cierre de la vela de ruptura M1. |
| `stop_basis` | `str` | — | no | swing causal (regla C5) | `ORIGIN_SWING_INTACT` > `M5_REACTION_EXTREME` > `M1_CONFIRMED_EXTREME` > `NO_STRUCTURAL_STOP`. |
| `stop_price` | `número` | precio | sí | swing causal | Precio **informativo**; no es una entrada y no implica orden. |
| `stop_observed_at` | `int` | epoch s | sí | swing causal | Instante en que el pivote ya era conocible (sin look-ahead). |
| `target_policy_status` | `str` | — | no | liquidez conocida al corte | `NO_STRUCTURAL_REFERENCE`, `NO_STOP_NO_RISK_UNIT`, `NO_KNOWN_LIQUIDITY_AT_CUTOFF`, `TP1_BELOW_3R`, `TP2_BELOW_5R`, `SATISFIED_TP1_3R_TP2_5R`. Observacional, nunca promesa. |
| `target_price` | `número` | precio | sí | liquidez conocida | Nivel de liquidez conocido más cercano. |
| `target_liquidity` | `list[objeto]` | — | no | M5/M1 cerradas | Niveles `{kind, price, observed_at}` (§3.1). |
| `reason` | `str` | — | no | `attach_confirmations._finish` | Motivo explícito del estado de confirmación; se añade solo a eventos procesados. |

### 3.1 Elemento de `target_liquidity`

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `kind` | `str` | — | no | estructura | `BROKEN_LEVEL`, `M5_SWING` o `M1_SWING`. |
| `price` | `número` | precio | no | estructura | Precio de la liquidez conocida. |
| `observed_at` | `int` | epoch s | no | estructura | Instante en que era conocible (`<= cutoff`). |

## 4. `transition_history` — elemento

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `from` | `str` | — | no | máquina de estados | Estado anterior. |
| `to` | `str` | — | no | máquina de estados | Estado nuevo. |
| `at` | `int` | epoch s | no | vela M15 cerrada (`<= cutoff`) | Instante de la transición. |
| `reason` | `str` | — | no | motor | `first_touch_after_confirmation`, `m15_close_back_inside_level_before_retest`, `close_through_structural_boundary_against_direction`, `no_retest_within_max_observation_window_comparable_results`, `retest_defense_m5_structure_stop_and_known_liquidity`. |

Transiciones posibles: `ACCEPTED_BREAK_WAIT_RETEST` → `RETESTING_POI` /
`ACCEPTANCE_LOST` / `POI_INVALID` / `EXPANSION_NO_ENTRY`; `RETESTING_POI` →
`POI_INVALID` / `OBSERVABLE_SETUP`. `EXPANSION_NO_ENTRY`,
`ACCEPTANCE_LOST`, `POI_INVALID` y `OBSERVABLE_SETUP` son terminales: no se
reescriben. `OBSERVABLE_SETUP` **sigue siendo solo observación**
(`entry_authorized=False`).

## 5. `load` — carga M5/M1 bajo demanda

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `m5_loaded` | `bool` | — | no | velas M5 cerradas | `true` si hay al menos una vela M5 cerrada `<= cutoff`. |
| `m1_loaded` | `bool` | — | no | velas M1 cerradas | Igual para M1 (corroboración). |
| `last_closed_m5` | `int` | epoch s | sí | velas M5 cerradas | Último cierre M5 observable; `null` si no se cargó. |
| `last_closed_m1` | `int` | epoch s | sí | velas M1 cerradas | Último cierre M1 observable; `null` si no se cargó. |
| `coverage` | `objeto` | — | no | velas M5/M1 cerradas | Conteo y primeros cierres (§5.1). |
| `load_reason` | `str` | — | no | carga bajo demanda | `NOT_REQUESTED_NO_M15_RETEST`, `LOWER_SOURCE_UNAVAILABLE`, `LOWER_SOURCE_MALFORMED`, `LOWER_SOURCE_ERROR: …`, `NO_CLOSED_M5_BARS_AT_CUTOFF`, `M1_BARS_UNAVAILABLE_M5_USED` o `M5_M1_LOADED`. |

### 5.1 `load.coverage`

| Campo | Tipo | Unidad | Nulo | Procedencia | Significado |
|---|---|---|---|---|---|
| `m5_bars_closed` | `int` | velas | no | M5 cerradas | Velas M5 usadas. |
| `m1_bars_closed` | `int` | velas | no | M1 cerradas | Velas M1 usadas. |
| `m5_first_closed` | `int` | epoch s | sí | M5 cerradas | Cierre M5 más antiguo usado. |
| `m1_first_closed` | `int` | epoch s | sí | M1 cerradas | Cierre M1 más antiguo usado. |
| `events_requested` | `int` | eventos | no | máquina de estados | Eventos en `RETESTING_POI` que pidieron carga. |

## 6. Casos de espera legítima

Un consumidor nuevo distingue sin adivinar entre **sin retest**, **datos
ausentes** y **evidencia insuficiente** cruzando `current_state`,
`pending_evidence`, `confirmation_state` y `load.load_reason`. En los cuatro
casos `entry_authorized` es `False` y no se inventan datos.

| Caso | Señales | `load_reason` | Qué falta (nunca se fabrica) |
|---|---|---|---|
| **Sin retest** | `current_state = ACCEPTED_BREAK_WAIT_RETEST`; `retest_at = null`; sin subbloque de confirmación; `pending_evidence` contiene `RETEST_NOT_OBSERVED` o `CAUSAL_POI_NOT_CONFIRMED` | `NOT_REQUESTED_NO_M15_RETEST` | No se piden M5/M1: no hay contacto con la POI. `coverage.events_requested = 0`. |
| **Sin M5** | `current_state = RETESTING_POI`; subbloque presente en `WAIT_M5_M1_CONFIRMATION`; `pending_evidence` con `M5_M1_CONFIRMATION_NOT_LOADED`; `defense_at`, `stop_price`, `target_price` en `null` | `LOWER_SOURCE_UNAVAILABLE`, `LOWER_SOURCE_MALFORMED`, `LOWER_SOURCE_ERROR: …`, `NO_CLOSED_M5_BARS_AT_CUTOFF` o `M1_BARS_UNAVAILABLE_M5_USED` | No hay velas M5 cerradas utilizables al corte. Se explica con `reason`; jamás se rellena un pivote. |
| **Sin stop** | `stop_basis = NO_STRUCTURAL_STOP`, `stop_price = null`, `stop_observed_at = null`; `pending_evidence` con `STRUCTURAL_STOP_NOT_DEFINED` (base) o `NO_STRUCTURAL_STOP` (tras cargar M5) | `M5_M1_LOADED` o el motivo de espera anterior | No hay swing causal íntegro ni extremo M5/M1 confirmado. El evento **permanece en espera**, no se invalida. |
| **Sin liquidez** | `target_policy_status` en `NO_STRUCTURAL_REFERENCE`, `NO_STOP_NO_RISK_UNIT` o `NO_KNOWN_LIQUIDITY_AT_CUTOFF`; `target_price = null`; `target_liquidity = []`; `pending_evidence` con `TARGET_POLICY_<estado>` | `M5_M1_LOADED` o motivo de espera | No hay liquidez conocida al corte a `>=3R`/`>=5R`. `TP1_BELOW_3R` / `TP2_BELOW_5R` también son espera: liquidez demasiado cercana, sin promesa de objetivo. |

Otros estados legítimos, no ambiguos: `EXPANSION_NO_ENTRY` (`pending` =
`NO_RETEST_WITHIN_COMPARABLE_WINDOWS`, sin retest en las ventanas
comparables) y `ACCEPTANCE_LOST` / `POI_INVALID` (`BREAK_INVALIDATED`).
Con evidencia completa el estado pasa a `OBSERVABLE_SETUP` y
`wait_reason = OBSERVATION_ONLY`, pero `entry_authorized` sigue siendo
`False`: el setup es **observable**, no operable.

## 7. Qué se conserva en `ict3_breaks`

`analyze_cached` mantiene `result["ict3_breaks"]` **sin cambios** para los
consumidores anteriores: es la lista plana de estudios de ruptura diaria
(`daily_break_studies`), anterior al bloque versionado, y
`attach_confirmations` no la toca. Campos conservados:

`event_id`, `session_open`, `source_open`, `level_name`, `level`, `direction`,
`signal_open`, `signal_close`, `body_ratio`, `body_multiple`,
`close_extension`, `close_location`, `strong_body`, `strong_range`,
`strong_extension`, `strong`, `state`, `observed_at`, `state_time`,
`accept_time`, `accept_open`, `failure_time`.

No gana campos de `ict3`, ni campos de orden/entrada. `ict3` y `ict3_breaks`
conviven en el mismo resultado: un cliente antiguo sigue leyendo el formato
previo y un cliente nuevo usa `ict3` para distinguir espera de ausencia de
datos.

## 8. Verificación

```bash
.venv/Scripts/python.exe -m unittest test_ict3_schema -v
```

La suite construye payloads reales con `analyze_cached` +
`attach_confirmations` (ruptura diaria, retest causal, con y sin M5/M1) y
comprueba campos obligatorios, tipos, invariante `entry_authorized=False`,
ausencia de claves de trading en todos los niveles, conservación de
`ict3_breaks` y que ningún instante supera el corte.
