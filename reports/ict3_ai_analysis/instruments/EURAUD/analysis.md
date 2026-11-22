# EURAUD — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `EURAUD`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BEARISH** · estado: **WAIT_CONTEXT** · motivo: `h4_against_short`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=M5_M1_LOADED`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BEARISH | ver chart_objects.json por TF |
| H4 | BULLISH | ver chart_objects.json por TF |
| H1 | BULLISH | ver chart_objects.json por TF |
| M15 | BEARISH | 125 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": -1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 1.64832, "pdl": 1.632, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795131000, "pdl_m15_open": 1795055400, "m15_count": 95, "events": [{"kind": "break", "level": "PDH", "high": 1.64936, "low": 1.6473, "close": 1.64919, "close_side": "PDH", "time": 1795137300}, {"kind": "late_return", "level": "PDH", "high": 1.64979, "low": 1.64787, "close": 1.648, "close_side": null, "time": 1795139100}, {"kind": "sweep", "level": "PDH", "high": 1.64845, "low": 1.64773, "close": 1.64777, "close_side": null, "time": 1795140000}, {"kind": "sweep", "level": "PDH", "high": 1.64909, "low": 1.64725, "close": 1.64762, "close_side": null, "time": 1795140900}, {"kind": "break", "level": "PDH", "high": 1.64909, "low": 1.64737, "close": 1.64906, "close_side": "PDH", "time": 1795141800}, {"kind": "late_return", "level": "PDH", "high": 1.64967, "low": 1.64736, "close": 1.64782, "close_side": null, "time": 1795144500}, {"kind": "break", "level": "PDH", "high": 1.64875, "low": 1.64752, "close": 1.64849, "close_side": "PDH", "time": 1795145400}, {"kind": "late_return", "level": "PDH", "high": 1.64914, "low": 1.64768, "close": 1.6479, "close_side": null, "time": 1795147200}, {"kind": "sweep", "level": "PDH", "high": 1.64887, "low": 1.64764, "close": 1.64788, "close_side": null, "time": 1795148100}, {"kind": "sweep", "level": "PDH", "high": 1.6489, "low": 1.64682, "close": 1.64769, "close_side": null, "time": 1795149000}, {"kind": "break", "level": "PDH", "high": 1.64924, "low": 1.64735, "close": 1.6486, "close_side": "PDH", "time": 1795149900}, {"kind": "late_return", "level": "PDH", "high": 1.64951, "low": 1.64736, "close": 1.6479, "close_side": null, "time": 1795150800}, {"kind": "break", "level": "PDH", "high": 1.65084, "low": 1.64784, "close": 1.65038, "close_side": "PDH", "time": 1795151700}, {"kind": "late_return", "level": "PDH", "high": 1.6496, "low": 1.64747, "close": 1.64781, "close_side": null, "time": 1795153500}, {"kind": "sweep", "level": "PDH", "high": 1.64869, "low": 1.6479, "close": 1.64816, "close_side": null, "time": 1795160700}, {"kind": "sweep", "level": "PDH", "high": 1.64841, "low": 1.64681, "close": 1.64821, "close_side": null, "time": 1795176000}, {"kind": "sweep", "level": "PDH", "high": 1.6484, "low": 1.64671, "close": 1.64749, "close_side": null, "time": 1795176900}, {"kind": "break", "level": "PDH", "high": 1.64958, "low": 1.64743, "close": 1.6494, "close_side": "PDH", "time": 1795187700}, {"kind": "late_return", "level": "PDH", "high": 1.64878, "low": 1.64711, "close": 1.64798, "close_side": null, "time": 1795190400}, {"kind": "break", "level": "PDH", "high": 1.64976, "low": 1.64793, "close": 1.64915, "close_side": "PDH", "time": 1795193100}, {"kind": "late_return", "level": "PDH", "high": 1.64926, "low": 1.64639, "close": 1.64654, "close_side": null, "time": 1795194000}, {"kind": "break", "level": "PDH", "high": 1.6504, "low": 1.64605, "close": 1.65032, "close_side": "PDH", "time": 1795194900}]}`
- Niveles reconstruidos: **17** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **604** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **125**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **6** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 479, "horizontal_lines": 17, "event_markers": 15} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **33** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h4_against_short`.
- Niveles de referencia: PDH=1.64832, PDL=1.632, LAST_FRIDAY_HIGH=1.65903, LAST_FRIDAY_LOW=1.64391, PDH=1.62734, PDH=1.62734, PDH=1.63008, PDH=1.63008.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795054200, "m1_first_closed": 1795186200, "events_requested": 1}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/EURAUD_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
