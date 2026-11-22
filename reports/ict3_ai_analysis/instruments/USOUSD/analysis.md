# USOUSD — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `USOUSD`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BEARISH** · estado: **WAIT_CONTEXT** · motivo: `h1_opposes_short`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=NOT_REQUESTED_NO_M15_RETEST`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BEARISH | ver chart_objects.json por TF |
| H4 | BEARISH | ver chart_objects.json por TF |
| H1 | BULLISH | ver chart_objects.json por TF |
| M15 | BEARISH | 141 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": -1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 85.148, "pdl": 82.902, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795104000, "pdl_m15_open": 1795095000, "m15_count": 83, "events": [{"kind": "break", "level": "PDL", "high": 83.186, "low": 82.431, "close": 82.56, "close_side": "PDL", "time": 1795171500}, {"kind": "late_return", "level": "PDL", "high": 83.179, "low": 82.728, "close": 83.104, "close_side": null, "time": 1795180500}, {"kind": "break", "level": "PDL", "high": 83.403, "low": 82.605, "close": 82.665, "close_side": "PDL", "time": 1795193100}, {"kind": "late_return", "level": "PDL", "high": 83.3, "low": 82.8, "close": 82.948, "close_side": null, "time": 1795194900}, {"kind": "break", "level": "PDL", "high": 82.943, "low": 82.452, "close": 82.822, "close_side": "PDL", "time": 1795195800}, {"kind": "late_return", "level": "PDL", "high": 83.261, "low": 82.761, "close": 83.182, "close_side": null, "time": 1795197600}, {"kind": "sweep", "level": "PDL", "high": 83.296, "low": 82.821, "close": 83.293, "close_side": null, "time": 1795198500}, {"kind": "break", "level": "PDL", "high": 83.342, "low": 82.801, "close": 82.851, "close_side": "PDL", "time": 1795199400}, {"kind": "late_return", "level": "PDL", "high": 83.312, "low": 82.77, "close": 83.262, "close_side": null, "time": 1795200300}, {"kind": "sweep", "level": "PDH", "high": 85.25, "low": 84.898, "close": 85.146, "close_side": null, "time": 1795215600}, {"kind": "gap", "level": "PDH", "high": 85.197, "low": 84.87, "close": 85.009, "close_side": null, "time": 1795216500}]}`
- Niveles reconstruidos: **20** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **738** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **141**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **7** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 597, "horizontal_lines": 20, "event_markers": 16} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **29** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h1_opposes_short`.
- Niveles de referencia: PDH=85.148, PDL=82.902, LAST_FRIDAY_HIGH=85.25, LAST_FRIDAY_LOW=81.967, PDH=88.91, PDL=86.019, PDL=86.019, PDH=89.301.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/USOUSD_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
