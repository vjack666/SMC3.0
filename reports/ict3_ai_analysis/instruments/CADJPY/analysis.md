# CADJPY — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `CADJPY`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BULLISH** · estado: **WAIT_CONTEXT** · motivo: `h1_opposes_long`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=NOT_REQUESTED_NO_M15_RETEST`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BULLISH | ver chart_objects.json por TF |
| H4 | BULLISH | ver chart_objects.json por TF |
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BULLISH | 128 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": -1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 111.973, "pdl": 111.085, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795102200, "pdl_m15_open": 1795064400, "m15_count": 95, "events": [{"kind": "sweep", "level": "PDL", "high": 111.168, "low": 111.072, "close": 111.11, "close_side": null, "time": 1795147200}, {"kind": "break", "level": "PDL", "high": 111.127, "low": 111.033, "close": 111.076, "close_side": "PDL", "time": 1795148100}, {"kind": "late_return", "level": "PDL", "high": 111.116, "low": 111.04, "close": 111.108, "close_side": null, "time": 1795150800}, {"kind": "break", "level": "PDL", "high": 111.124, "low": 111.009, "close": 111.013, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 111.112, "low": 111.003, "close": 111.09, "close_side": null, "time": 1795153500}, {"kind": "sweep", "level": "PDL", "high": 111.145, "low": 111.083, "close": 111.126, "close_side": null, "time": 1795154400}, {"kind": "break", "level": "PDL", "high": 111.132, "low": 111.053, "close": 111.076, "close_side": "PDL", "time": 1795158900}, {"kind": "late_return", "level": "PDL", "high": 111.124, "low": 111.059, "close": 111.113, "close_side": null, "time": 1795159800}, {"kind": "break", "level": "PDL", "high": 111.114, "low": 111.035, "close": 111.049, "close_side": "PDL", "time": 1795160700}, {"kind": "late_return", "level": "PDL", "high": 111.133, "low": 111.04, "close": 111.114, "close_side": null, "time": 1795161600}, {"kind": "break", "level": "PDL", "high": 111.17, "low": 111.07, "close": 111.07, "close_side": "PDL", "time": 1795167000}, {"kind": "late_return", "level": "PDL", "high": 111.143, "low": 111.064, "close": 111.132, "close_side": null, "time": 1795167900}, {"kind": "break", "level": "PDL", "high": 111.146, "low": 111.044, "close": 111.067, "close_side": "PDL", "time": 1795170600}]}`
- Niveles reconstruidos: **19** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **649** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **128**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTED_BREAK_WAIT_RETEST
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 521, "horizontal_lines": 19, "event_markers": 10} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **29** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BULLISH`, estado `WAIT_CONTEXT`, motivo `h1_opposes_long`.
- Niveles de referencia: PDH=111.973, PDL=111.085, LAST_FRIDAY_HIGH=111.445, LAST_FRIDAY_LOW=110.436, PDL=111.828, PDL=111.828, PDL=111.828, PDL=111.828.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BULLISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/CADJPY_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
