# UKOUSD — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `UKOUSD`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BEARISH** · estado: **WAIT_CONTEXT** · motivo: `h4_against_short`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=NOT_REQUESTED_NO_M15_RETEST`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BEARISH | ver chart_objects.json por TF |
| H4 | BULLISH | ver chart_objects.json por TF |
| H1 | BULLISH | ver chart_objects.json por TF |
| M15 | BEARISH | 128 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": -1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 94.525, "pdl": 92.248, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795104000, "pdl_m15_open": 1795057200, "m15_count": 83, "events": [{"kind": "break", "level": "PDL", "high": 92.812, "low": 92.14, "close": 92.155, "close_side": "PDL", "time": 1795170600}, {"kind": "late_return", "level": "PDL", "high": 92.405, "low": 91.928, "close": 92.3, "close_side": null, "time": 1795181400}, {"kind": "break", "level": "PDL", "high": 92.584, "low": 92.218, "close": 92.223, "close_side": "PDL", "time": 1795182300}, {"kind": "late_return", "level": "PDL", "high": 92.504, "low": 92.168, "close": 92.382, "close_side": null, "time": 1795183200}, {"kind": "sweep", "level": "PDL", "high": 92.82, "low": 92.246, "close": 92.397, "close_side": null, "time": 1795184100}, {"kind": "sweep", "level": "PDL", "high": 92.694, "low": 91.881, "close": 92.251, "close_side": null, "time": 1795187700}, {"kind": "gap", "level": "PDL", "high": 92.606, "low": 92.211, "close": 92.424, "close_side": null, "time": 1795188600}, {"kind": "break", "level": "PDL", "high": 92.549, "low": 92.162, "close": 92.227, "close_side": "PDL", "time": 1795189500}, {"kind": "late_return", "level": "PDL", "high": 92.458, "low": 92.168, "close": 92.338, "close_side": null, "time": 1795190400}, {"kind": "break", "level": "PDL", "high": 92.348, "low": 92.001, "close": 92.216, "close_side": "PDL", "time": 1795191300}, {"kind": "late_return", "level": "PDL", "high": 92.735, "low": 92.166, "close": 92.676, "close_side": null, "time": 1795202100}, {"kind": "sweep", "level": "PDL", "high": 92.666, "low": 92.179, "close": 92.268, "close_side": null, "time": 1795203000}, {"kind": "sweep", "level": "PDL", "high": 92.635, "low": 92.238, "close": 92.456, "close_side": null, "time": 1795203900}, {"kind": "sweep", "level": "PDL", "high": 92.692, "low": 92.237, "close": 92.447, "close_side": null, "time": 1795205700}]}`
- Niveles reconstruidos: **16** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **715** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **128**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **6** · estado(s): ACCEPTANCE_LOST, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 587, "horizontal_lines": 16, "event_markers": 17} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **23** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h4_against_short`.
- Niveles de referencia: PDH=94.525, PDL=92.248, LAST_FRIDAY_HIGH=93.92, LAST_FRIDAY_LOW=90.926, PDH=97.148, PDH=98.51, PDH=98.51, PDL=97.154.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/UKOUSD_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
