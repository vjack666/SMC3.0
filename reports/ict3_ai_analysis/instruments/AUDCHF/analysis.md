# AUDCHF — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `AUDCHF`
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
| M15 | BEARISH | 130 |

- Estructura LTF: `{"bars": 120, "bos_dir": 1, "momentum": 1, "trend": "BULLISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.56696, "pdl": 0.56113, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795054500, "pdl_m15_open": 1795114800, "m15_count": 95, "events": [{"kind": "sweep", "level": "PDL", "high": 0.56176, "low": 0.56028, "close": 0.56171, "close_side": null, "time": 1795134600}, {"kind": "sweep", "level": "PDL", "high": 0.56183, "low": 0.56103, "close": 0.56177, "close_side": null, "time": 1795139100}, {"kind": "break", "level": "PDL", "high": 0.56159, "low": 0.56053, "close": 0.56062, "close_side": "PDL", "time": 1795142700}, {"kind": "late_return", "level": "PDL", "high": 0.56122, "low": 0.56051, "close": 0.56117, "close_side": null, "time": 1795143600}, {"kind": "sweep", "level": "PDL", "high": 0.56157, "low": 0.56059, "close": 0.56118, "close_side": null, "time": 1795144500}, {"kind": "break", "level": "PDL", "high": 0.56135, "low": 0.56078, "close": 0.56083, "close_side": "PDL", "time": 1795145400}, {"kind": "late_return", "level": "PDL", "high": 0.56132, "low": 0.56072, "close": 0.56127, "close_side": null, "time": 1795148100}, {"kind": "sweep", "level": "PDL", "high": 0.56166, "low": 0.56085, "close": 0.56138, "close_side": null, "time": 1795149000}, {"kind": "break", "level": "PDL", "high": 0.5615, "low": 0.5606, "close": 0.561, "close_side": "PDL", "time": 1795149900}, {"kind": "late_return", "level": "PDL", "high": 0.56149, "low": 0.56058, "close": 0.5613, "close_side": null, "time": 1795150800}, {"kind": "break", "level": "PDL", "high": 0.56133, "low": 0.56002, "close": 0.56019, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 0.56143, "low": 0.56046, "close": 0.56123, "close_side": null, "time": 1795153500}, {"kind": "sweep", "level": "PDL", "high": 0.56173, "low": 0.56112, "close": 0.56166, "close_side": null, "time": 1795154400}, {"kind": "sweep", "level": "PDL", "high": 0.5617, "low": 0.56108, "close": 0.5613, "close_side": null, "time": 1795155300}, {"kind": "sweep", "level": "PDL", "high": 0.5614, "low": 0.56109, "close": 0.56122, "close_side": null, "time": 1795156200}, {"kind": "sweep", "level": "PDL", "high": 0.56147, "low": 0.56111, "close": 0.5613, "close_side": null, "time": 1795157100}, {"kind": "break", "level": "PDL", "high": 0.56134, "low": 0.56085, "close": 0.56099, "close_side": "PDL", "time": 1795158900}, {"kind": "late_return", "level": "PDL", "high": 0.56171, "low": 0.56082, "close": 0.56159, "close_side": null, "time": 1795161600}, {"kind": "break", "level": "PDL", "high": 0.56131, "low": 0.56051, "close": 0.56067, "close_side": "PDL", "time": 1795175100}, {"kind": "late_return", "level": "PDL", "high": 0.56153, "low": 0.5609, "close": 0.56117, "close_side": null, "time": 1795178700}, {"kind": "break", "level": "PDL", "high": 0.5612, "low": 0.56037, "close": 0.56083, "close_side": "PDL", "time": 1795179600}]}`
- Niveles reconstruidos: **16** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **630** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **130**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 500, "horizontal_lines": 16, "event_markers": 11} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **36** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h1_opposes_short`.
- Niveles de referencia: PDH=0.56696, PDL=0.56113, LAST_FRIDAY_HIGH=0.56286, LAST_FRIDAY_LOW=0.55461, PDL=0.56676, PDL=0.56676, PDL=0.56489, PDL=0.56489.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/AUDCHF_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
