# AUDUSD — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `AUDUSD`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BULLISH** · estado: **WAIT_CONTEXT** · motivo: `h4_against_long`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=NOT_REQUESTED_NO_M15_RETEST`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BULLISH | ver chart_objects.json por TF |
| H4 | BEARISH | ver chart_objects.json por TF |
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BULLISH | 129 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.67206, "pdl": 0.66534, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795054500, "pdl_m15_open": 1795131000, "m15_count": 95, "events": [{"kind": "boundary_close", "level": "PDL", "high": 0.66596, "low": 0.66529, "close": 0.66534, "close_side": null, "time": 1795136400}, {"kind": "break", "level": "PDL", "high": 0.66567, "low": 0.665, "close": 0.6651, "close_side": "PDL", "time": 1795137300}, {"kind": "late_return", "level": "PDL", "high": 0.6656, "low": 0.66478, "close": 0.66555, "close_side": null, "time": 1795139100}, {"kind": "sweep", "level": "PDL", "high": 0.666, "low": 0.66508, "close": 0.6659, "close_side": null, "time": 1795140900}, {"kind": "break", "level": "PDL", "high": 0.66555, "low": 0.66485, "close": 0.66493, "close_side": "PDL", "time": 1795142700}, {"kind": "late_return", "level": "PDL", "high": 0.66563, "low": 0.66476, "close": 0.6656, "close_side": null, "time": 1795143600}, {"kind": "sweep", "level": "PDL", "high": 0.66601, "low": 0.66513, "close": 0.6657, "close_side": null, "time": 1795144500}, {"kind": "sweep", "level": "PDL", "high": 0.66586, "low": 0.66529, "close": 0.66536, "close_side": null, "time": 1795145400}, {"kind": "break", "level": "PDL", "high": 0.66579, "low": 0.66506, "close": 0.66514, "close_side": "PDL", "time": 1795146300}, {"kind": "late_return", "level": "PDL", "high": 0.6659, "low": 0.66499, "close": 0.66557, "close_side": null, "time": 1795149000}, {"kind": "boundary_close", "level": "PDL", "high": 0.66578, "low": 0.66516, "close": 0.66534, "close_side": null, "time": 1795149900}, {"kind": "sweep", "level": "PDL", "high": 0.66586, "low": 0.66515, "close": 0.66572, "close_side": null, "time": 1795150800}, {"kind": "break", "level": "PDL", "high": 0.66573, "low": 0.66455, "close": 0.6648, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 0.66608, "low": 0.66521, "close": 0.66596, "close_side": null, "time": 1795153500}, {"kind": "sweep", "level": "PDL", "high": 0.66577, "low": 0.66509, "close": 0.66549, "close_side": null, "time": 1795195800}, {"kind": "sweep", "level": "PDL", "high": 0.66598, "low": 0.6653, "close": 0.66574, "close_side": null, "time": 1795196700}, {"kind": "break", "level": "PDL", "high": 0.66603, "low": 0.66452, "close": 0.66453, "close_side": "PDL", "time": 1795197600}]}`
- Niveles reconstruidos: **17** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **609** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **129**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTANCE_LOST, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 480, "horizontal_lines": 17, "event_markers": 12} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **37** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BULLISH`, estado `WAIT_CONTEXT`, motivo `h4_against_long`.
- Niveles de referencia: PDH=0.67206, PDL=0.66534, LAST_FRIDAY_HIGH=0.66822, LAST_FRIDAY_LOW=0.66083, PDL=0.67979, PDL=0.67979, PDL=0.67689, PDL=0.67689.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BULLISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/AUDUSD_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
