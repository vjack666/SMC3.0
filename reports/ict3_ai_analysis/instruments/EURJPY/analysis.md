# EURJPY — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `EURJPY`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BEARISH** · estado: **WAIT_CONTEXT** · motivo: `short_in_discount`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=M5_M1_LOADED`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BEARISH | ver chart_objects.json por TF |
| H4 | BEARISH | ver chart_objects.json por TF |
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BEARISH | 129 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 176.072, "pdl": 174.718, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795092300, "pdl_m15_open": 1795064400, "m15_count": 95, "events": [{"kind": "break", "level": "PDL", "high": 174.779, "low": 174.622, "close": 174.676, "close_side": "PDL", "time": 1795147200}, {"kind": "late_return", "level": "PDL", "high": 174.724, "low": 174.629, "close": 174.723, "close_side": null, "time": 1795150800}, {"kind": "break", "level": "PDL", "high": 174.741, "low": 174.61, "close": 174.63, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 174.76, "low": 174.612, "close": 174.727, "close_side": null, "time": 1795153500}, {"kind": "sweep", "level": "PDL", "high": 174.771, "low": 174.707, "close": 174.748, "close_side": null, "time": 1795157100}, {"kind": "break", "level": "PDL", "high": 174.761, "low": 174.658, "close": 174.692, "close_side": "PDL", "time": 1795158900}, {"kind": "late_return", "level": "PDL", "high": 174.742, "low": 174.665, "close": 174.731, "close_side": null, "time": 1795159800}, {"kind": "break", "level": "PDL", "high": 174.73, "low": 174.614, "close": 174.643, "close_side": "PDL", "time": 1795160700}, {"kind": "late_return", "level": "PDL", "high": 174.796, "low": 174.632, "close": 174.741, "close_side": null, "time": 1795161600}, {"kind": "break", "level": "PDL", "high": 174.896, "low": 174.666, "close": 174.716, "close_side": "PDL", "time": 1795169700}]}`
- Niveles reconstruidos: **17** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **639** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **129**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **6** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, EXPANSION_NO_ENTRY, POI_INVALID, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 510, "horizontal_lines": 17, "event_markers": 14} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **27** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `short_in_discount`.
- Niveles de referencia: PDH=176.072, PDL=174.718, LAST_FRIDAY_HIGH=175.345, LAST_FRIDAY_LOW=173.733, PDL=176.24, PDL=175.927, PDL=175.927, PDL=175.218.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BEARISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795054200, "m1_first_closed": 1795186200, "events_requested": 1}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/EURJPY_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
