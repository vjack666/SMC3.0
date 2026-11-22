# Fase 7 — Protocolo de validación fuera de muestra (OOS)

**Mandato.** Medir estados y cobertura del motor con una evaluación cronológica reproducible. No afirmar rentabilidad. Este documento describe el protocolo implementado en `ict3_oos.py` y cómo reproducirlo. Es complemento de `FASE_07_VALIDACION_OOS.md`.

## 1. Alcance y prohibiciones

- El módulo es **puro**: no importa `MetaTrader5`, no abre conexiones, no lee credenciales, no lee ni escribe `data/`, no toca archivos de producción.
- Todo dato producido es **sintético declarado** (`SYNTHETIC_SOURCE = SYNTHETIC_DECLARED`). La cobertura real se marca **`REAL_COVERAGE_PENDING`** mientras no exista una fuente verificable; el módulo nunca inventa velas reales.
- **Rechazo explícito** de métricas de ejecución: `refuse_execution_metrics(metric)` lanza `ExecutionMetricsForbidden` para `fills`, `lotaje`, `pnl`, `equity_curve`, etc. `assert_no_execution_metrics(obj)` recorre el informe y falla si aparece alguna clave prohibida (`entry`, `order`, `fill`, `lots`, `volume`, `pnl`, `position`, `balance`, `equity`, `margin`, `ticket`, `deal`, …).
- `mode = OBSERVE_ONLY_NO_ORDER` en todo el informe. Los resultados se limitan a estados observados y su frecuencia.

## 2. Inventario por activo y marco

`build_inventory(dataset)` recibe `dataset = {symbol: {frame: candles}}` y emite una fila por `(símbolo, marco)` con:

| Campo | Significado |
|---|---|
| `symbol`, `alias` | Símbolo original y alias legible (`EURUSD → EUR/USD`); sin alias known se usa el símbolo. |
| `frame` | Marco temporal (`D1`, `M15`, `M5`, `M1`). |
| `source` | `SYNTHETIC_DECLARED` o `REAL_COVERAGE_PENDING`. |
| `first_close`, `last_close` | Primer y último cierre en `YYYY-MM-DD HH:MM UTC` (y su epoch). |
| `candles` | Cantidad de velas del marco. |
| `gaps` | Huecos: intervalos entre cierres consecutivos mayores que el paso nominal del marco. |
| `real_coverage` | `REAL_COVERAGE_PENDING` hasta que se entregue una fuente. |

`pending_inventory(symbols, frames)` produce el inventario de cobertura real pendiente sin velas inventadas. `common_coverage(inventory, frames)` computa la intersección de activos y **registra cada exclusión** con motivo `MISSING_FRAMES`. M1 se mide por separado al incluirlo en `frames`.

Ejemplo reproducible con velas sintéticas (`gap_every=5` declara huecos):

```
candles = synthetic_candles("EURUSD", "M15", 21, start_epoch=START, seed=1, gap_every=5)
inventory_entry("EURUSD", "M15", candles)
```

| Símbolo | Alias | Marco | Fuente | Primer cierre | Último cierre | Velas | Huecos |
|---|---|---|---|---|---|---:|---:|
| EURUSD | EUR/USD | M15 | SYNTHETIC_DECLARED | 2026-11-01 00:15 UTC | 2026-11-01 06:15 UTC | 21 | 4 |

## 3. Fecha de separación y parámetros congelados

`FrozenParameters` es un `dataclass(frozen=True)`; cualquier intento de mutación lanza `FrozenInstanceError`. Valores congelados por defecto:

| Parámetro | Valor |
|---|---|
| `separation_date` | `2026-11-15` |
| `windows` | `(4, 8, 16, 32)` velas M15 |
| `force_body_ratio` | `0.70` |
| `force_body_multiple` | `1.5` |
| `force_close_extension` | `0.50` |
| `source_policy` | `SYNTHETIC_DECLARED` |
| `mode` | `OBSERVE_ONLY_NO_ORDER` |

`separate_calibration_evaluation(params, observations)` parte por `observed_date`:

- **calibración**: `observed_date < separation_date`
- **evaluación (OOS)**: `observed_date >= separation_date`

La partición es disjunta y completa: `calibration_evaluation_integrity` verifica `disjoint`, `complete` y `separated`, y reporta los denominadores. En la ejecución de ejemplo con 60 observaciones sintéticas: calibración **42**, evaluación **18**, total **60**; `disjoint=True`, `complete=True`, `separated=True`.

## 4. Agrupación de estados observados

`group_observed_states(observations)` agrupa por seis dimensiones, en este orden:

`symbol` · `level` (`PDH`/`PDL`) · `session` · `poi_type` (`FVG`/`OB`, o `None` si no hay POI) · `window` (4/8/16/32 M15) · `state`.

Vocabulario de estados: `BREAK_CANDIDATE`, `FAILED_BREAK`, `ACCEPTED_BREAK_WAIT_RETEST`, `RETESTING_POI`, `EXPANSION_NO_ENTRY`, `ACCEPTANCE_LOST`, `POI_INVALID`.

La sesión se asigna con un mapa UTC **declarado** (sin DST): `ASIA` 00–07, `LONDON` 07–12, `NEW_YORK` 12–21, `OTHER` el resto. Es una convención de agrupación, no una afirmación de liquidez.

Cada fila lleva su `count`. Además se reportan:

- **Denominadores**: `total`, `by_symbol`, `by_symbol_level`.
- **Cobertura efectiva**: `with_poi`, `complete_window`, `with_poi_and_complete_window`, `total` y `ratio`.

Ejemplo de la ejecución sintética: total 60, con POI 49, ventana completa 51, ambos 43, `ratio = 0.7167`. Todas las filas del ejemplo tienen `count = 1` porque cada combinación de seis dimensiones es única en la muestra; eso es esperable en una muestra pequeña y **no** debe leerse como ventaja estadística.

## 5. Invariancia por cortes causales

`verify_prefix_invariance(candles, frame, cutoffs, reducer=causal_break_states, level=…)` comprueba, para cada corte `t`:

```
reducer(full_series, frame, t) == reducer(prefix_of(full_series, frame, t), frame, t)
```

`prefix_of` conserva solo velas con `close <= t` (`opened + SECONDS[frame] <= t`). El reductor por defecto ignora cualquier vela que cierre después del corte, por lo que la fuga temporal es imposible por construcción. El informe devuelve `invariant`, `cutoffs_checked`, `checks` y `mismatches`. En el ejemplo: `invariant=True`, 8 cortes revisados. `test_leaking_reducer_is_detected` demuestra lo contrario: un reductor que mira la última vela de la serie completa sin respetar `t` produce `mismatches` y `invariant=False`.

Las ventanas incompletas se tratan de forma explícita: se cuentan en `effective_coverage.complete_window` y nunca se promueven a evidencia de una ventana cerrada; `poi_type=None` se conserva como dimensión (`sin POI`), no se descarta.

## 6. Comando de ejecución y reproducibilidad

```bash
cd C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0
.venv/Scripts/python.exe -m unittest test_ict3_oos -v
```

Resultado verificado: **18 pruebas, OK** (0.014 s). Para regenerar el informe y el markdown:

```python
import ict3_oos as oos
report = oos.build_report()          # sin dataset -> inventario REAL_COVERAGE_PENDING
md = oos.render_report(report)       # tablas agregadas y fechas
dataset = {"EURUSD": {"M15": oos.synthetic_candles(
    "EURUSD", "M15", 48, start_epoch=START, seed=2, gap_every=9)}}
report = oos.build_report(dataset=dataset, seed=2)  # fuente SYNTHETIC_DECLARED
```

`build_report` es determinista: dos llamadas con el mismo `dataset` y `seed` devuelven objects iguales (`test_report_with_dataset_is_reproducible`).

## 7. Cobertura real pendiente

No hay fuente real conectada en este entorno, por lo que:

- `report["source"] = REAL_COVERAGE_PENDING`, `report["real_coverage"] = REAL_COVERAGE_PENDING`, `declared_synthetic=True`.
- El inventario real tiene `candles = 0`, `first_close = last_close = None` y no se inventan velas.
- Para completar la Fase 7 con datos reales, el agente de datos debe entregar un `dataset` con firma `{symbol: {frame: candles}}` y declarar su fuente; entonces se recalculan inventario, partición (con la misma fecha congelada salvo decisión explícita), agrupación e invariancia. Las credenciales y los datos privados quedan fuera del informe.

## 8. Entregable

Archivos nuevos de esta fase (sin modificar producción ni `data/`):

- `ict3_oos.py` — protocolo y utilidades de simulación/cobertura.
- `test_ict3_oos.py` — 18 pruebas sin MT5, servidor ni escrituras.
- `docs/ict3/FASE_07_PROTOCOLO_OOS.md` — este documento.

Aceptación: otra persona reproduce los conteos con las mismas fuentes declaradas; los resultados no se convierten en ventaja estadística ni en métrica de rentabilidad.
