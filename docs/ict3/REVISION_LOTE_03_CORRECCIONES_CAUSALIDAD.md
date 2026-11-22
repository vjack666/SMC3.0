# Revisión Lote Hermes 03 — corrección causal M5/M1

**Estado:** corrección aplicada y validada por Hermes. Sin operaciones, sin
credenciales y sin cambios en `data/`.

## Hallazgo

La implementación de confirmaciones M5/M1 pasó la suite (`89 tests / OK`) y
mantiene el modo observacional. Sin embargo, el cálculo del stop estructural
podía usar un pivote cuyo extremo se formó antes del retest pero cuyas dos
velas de confirmación cerraron después del retest. También podía usar un
extremo de reacción cuyo pivote todavía no estaba confirmado al final del
intervalo evaluado. Ambos casos introducían información futura en una
revisión histórica.

## Corrección aplicada y validada

En `ict3_confirm.py`:

1. `ORIGIN_SWING_INTACT` (`_origin_swing`, líneas 213-233) exige
   `p["at"] < retest_at` **y** `p["confirmed_at"] <= retest_at` (líneas
   220-222). Un pivote formado antes pero confirmado después del retest queda
   fuera: no era conocible en ese instante.
2. `M5_REACTION_EXTREME` y `M1_CONFIRMED_EXTREME` (`_reaction_pivot`, líneas
   236-243) exigen `p["at"] >= start`, `p["confirmed_at"] >= start` y
   `p["confirmed_at"] <= end` cuando hay `end`. `start` es `retest_at`; `end`
   es el cierre de la estructura M5/M1 o, en su defecto, el `cutoff`.
3. Se conserva la precedencia de stop, la regla de no inventar datos y
   `entry_authorized=False` / `mode=OBSERVE_ONLY_NO_ORDER` en todos los
   eventos. `_finish` (340-349) mantiene `pending_evidence`, `wait_reason` y
   `reason` sin reescribir estados terminales.

Evidencia causal concreta (serie sintética `late_confirmation_bars`): el pivote
`1.190` se forma en `T0` y se confirma en `T0+600`, después del retest
(`T0+300`). Con la corrección, serie completa y prefijo hasta el retest
coinciden en `stop_basis=ORIGIN_SWING_INTACT`, `stop_price=1.198` (pivote
`1.198`, confirmado en `T0-600`). Sin la corrección, la serie completa habría
elegido `1.190` y el replay habría divergido.

## Verificación requerida y resultado

- Ejecutar `python -m unittest discover -v`: **107 tests / OK** (89 previos +
  18 nuevos).
- Prueba de replay del pivote confirmado después del retest: no cambia
  `stop_basis` ni `stop_price` (1.198 en prefijo y serie completa).
- Mismo cutoff → mismo `stop_basis`, `stop_price`, `target_policy_status` y
  estado al evaluar prefijo o serie completa.
- EURUSD, GBPJPY y US30 sin `entry`, `order`, `fill`, `lots`, `volume`, `pnl`
  ni `entry_authorized=true`.
- Carga M5/M1 solo con `RETESTING_POI`; sin retest no se llama `read_bars`
  de marcos inferiores.

## Contrato de `ict3.load` (documentación de observabilidad)

Lo produce `attach_confirmations` (`ict3_confirm.py:378-430`). Tipos
verificados en `test_ict3_causality.LoadContractTests`.

| Campo | Tipo | Significado |
|---|---|---|
| `m5_loaded` | `bool` | `True` si existe al menos una vela M5 cerrada `<= cutoff`. |
| `m1_loaded` | `bool` | `True` si existe al menos una vela M1 cerrada `<= cutoff`. |
| `last_closed_m5` | `int \| None` | Cierre nominal de la última vela M5 observable; `None` si no hay. |
| `last_closed_m1` | `int \| None` | Cierre nominal de la última vela M1 observable; `None` si no hay. |
| `coverage.m5_bars_closed` | `int` | Número de velas M5 cerradas usadas. |
| `coverage.m1_bars_closed` | `int` | Número de velas M1 cerradas usadas. |
| `coverage.m5_first_closed` | `int \| None` | Cierre M5 más antiguo del conjunto observable. |
| `coverage.m1_first_closed` | `int \| None` | Cierre M1 más antiguo del conjunto observable. |
| `coverage.events_requested` | `int` | Eventos en `RETESTING_POI` que pidieron confirmación. |
| `load_reason` | `str` | Motivo de carga/espera, según la catalogación siguiente. |

Valores de `load_reason`: `NOT_REQUESTED_NO_M15_RETEST`,
`LOWER_SOURCE_ERROR: <motivo>`, `LOWER_SOURCE_UNAVAILABLE`,
`LOWER_SOURCE_MALFORMED`, `NO_CLOSED_M5_BARS_AT_CUTOFF`, `M5_M1_LOADED`,
`M1_BARS_UNAVAILABLE_M5_USED`.

### Campos M5/M1 del evento (cierre, cobertura, cutoff, razón de espera)

| Campo | Tipo | Regla causal |
|---|---|---|
| `confirmation_state` | `str` | `WAIT_M5_M1_CONFIRMATION` o `M5_STRUCTURE_CONFIRMED`. Nunca autoriza entrada. |
| `defense_at` | `int \| None` | Cierre M5 de la primera defensa tras `retest_at`; `<= cutoff`. |
| `m5_structure_kind` / `m1_structure_kind` | `str \| None` | `BOS` / `CHOCH` / `MSS` por cierre, con pivotes confirmados antes de la vela que rompe. |
| `m5_structure_at` / `m1_structure_at` | `int \| None` | Cierre de la vela de ruptura; `<= cutoff`. |
| `stop_basis` | `str` | `ORIGIN_SWING_INTACT`, `M5_REACTION_EXTREME`, `M1_CONFIRMED_EXTREME` o `NO_STRUCTURAL_STOP`. |
| `stop_price` | `float \| None` | Precio informativo del pivote causal; `None` sin stop. No es una entrada. |
| `stop_observed_at` | `int \| None` | Instante en que el pivote del stop era conocible; `<= cutoff`. |
| `target_policy_status` | `str` | `SATISFIED_TP1_3R_TP2_5R`, `TP1_BELOW_3R`, `TP2_BELOW_5R` u otros estados pendientes. |
| `target_price` | `float \| None` | Liquidez conocida más cercana; `None` si no aplica. |
| `target_liquidity` | `list[dict]` | `{kind, price, observed_at}` con `observed_at <= cutoff`; `kind` es `BROKEN_LEVEL`, `M5_SWING` o `M1_SWING`. |
| `pending_evidence` | `list[str]` | Pendientes explícitos; nunca se inventa estructura. |
| `wait_reason` | `str` | Unión de `pending_evidence`; `OBSERVATION_ONLY` si no hay pendientes. |
| `reason` | `str` | Motivo de la última transición o del estado de espera. |

### Cutoff y velas futuras

`_closed_bars` (`106-124`) solo admite filas con `opened + SECONDS[tf] <= cutoff`
y descarta velas vacías/de relleno. `_pivots` (`139-153`) confirma un swing solo
cuando `i+2` ya cerró. Por tanto, un prefijo que termina en `t` y la serie
completa evaluada en `t` ven exactamente las mismas velas. Las pruebas
`test_no_future_candle_is_exposed_at_cutoff` y
`test_prefix_equals_full_for_every_confirmation_field` verifican que
`last_closed_*`, `defense_at`, `*_structure_at`, `stop_observed_at`,
`state_time` y todo `target_liquidity[].observed_at` son `<= cutoff` y que la
liquidez lejana (por ejemplo `1.250`) no aparece en un corte temprano.

## Pruebas añadidas

- `test_ict3_causality.py` (8 pruebas): correcciones 1 y 2, replay del pivote
  confirmado tarde, tipos del contrato `load`, sin velas futuras,
  EURUSD/GBPJPY/US30 en modo observacional.
- `test_ict3_replay_causal.py` (6 pruebas, con `subTest` parametrizados):
  prefijo vs serie completa en todos los campos, defensa, CHOCH/BOS/MSS,
  stop por autoridad, liquidez y política TP1≥3R/TP2≥5R, caso sin M1 y caso
  con error de MT5.
- `test_ict3_http_integration.py` (4 pruebas): `GET /api/ict` para EURUSD,
  GBPJPY y US30 contra un `LocalServer` efímero, carga bajo demanda
  (sin `RETESTING_POI` no se llama `read_bars` M5/M1), error de MT5 y
  `OBSERVE_ONLY_NO_ORDER` en la respuesta.

## Evidencia de ejecución

Comando: `.venv/Scripts/python.exe -m unittest discover -v`

Resultado: `Ran 107 tests in 1.224s` — `OK`. El bridge de trabajo se activó con
`{"active":true,"task":"Lote 03 corrección + Lote 04"}` y se cierra con
`{"active":false,"task":""}` al entregar el informe; no se implementó polling
ni se consultó `/api/inbox`.

## Riesgos y límites

- Las velas y los eventos de prueba son sintéticos: validan la lógica causal,
  no un estado de mercado real. No se conectó a MT5 ni se usaron credenciales.
- `end` del intervalo de reacción depende de la estructura M5/M1 detectada; si
  no hay estructura se usa `cutoff`, que sigue siendo una marca conocible.
- `EventSource('/api/events')` y el `fs.watch`+debounce del servidor del bridge
  son responsabilidad del proceso del bridge; este lote no modifica esa
  interfaz ni añade temporizadores propios.
- No se cambió ningún archivo de `data/`, ni se crearon órdenes, fills, lotes,
  volumen, P&L ni posiciones. Verificado: ejecutar solo los 18 tests nuevos no
  altera los mtimes de `data/`.

No se solicita operar MT5 ni cambiar credenciales. La salida sigue siendo
investigación observacional ICT 3.0.
