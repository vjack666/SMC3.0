# NDX100 — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `NDX100`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BULLISH** · estado: **WAIT_LTF_CONFIRMATION** · motivo: `ok`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=NOT_REQUESTED_NO_M15_RETEST`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BULLISH | ver chart_objects.json por TF |
| H4 | BULLISH | ver chart_objects.json por TF |
| H1 | BULLISH | ver chart_objects.json por TF |
| M15 | BEARISH | 133 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 27751.62, "pdl": 26356.01, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795105800, "pdl_m15_open": 1795131900, "m15_count": 91, "events": [{"kind": "sweep", "level": "PDL", "high": 26462.97, "low": 26341.28, "close": 26449.2, "close_side": null, "time": 1795139100}, {"kind": "sweep", "level": "PDL", "high": 26459.35, "low": 26353.7, "close": 26373.47, "close_side": null, "time": 1795142700}, {"kind": "sweep", "level": "PDL", "high": 26396.97, "low": 26305.13, "close": 26396.72, "close_side": null, "time": 1795143600}, {"kind": "sweep", "level": "PDL", "high": 26471.72, "low": 26318.7, "close": 26394.36, "close_side": null, "time": 1795144500}, {"kind": "break", "level": "PDL", "high": 26445.84, "low": 26313.78, "close": 26332.2, "close_side": "PDL", "time": 1795146300}, {"kind": "late_return", "level": "PDL", "high": 26410.47, "low": 26305.61, "close": 26408.35, "close_side": null, "time": 1795148100}, {"kind": "break", "level": "PDL", "high": 26410.6, "low": 26316.11, "close": 26321.61, "close_side": "PDL", "time": 1795149000}, {"kind": "late_return", "level": "PDL", "high": 26381.1, "low": 26280.31, "close": 26369.97, "close_side": null, "time": 1795150800}, {"kind": "break", "level": "PDL", "high": 26383.35, "low": 26291.23, "close": 26315.59, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 26433.22, "low": 26314.03, "close": 26405.86, "close_side": null, "time": 1795153500}, {"kind": "sweep", "level": "PDL", "high": 26432.84, "low": 26323.47, "close": 26359.72, "close_side": null, "time": 1795155300}, {"kind": "break", "level": "PDL", "high": 26372.85, "low": 26311.53, "close": 26325.97, "close_side": "PDL", "time": 1795156200}, {"kind": "late_return", "level": "PDL", "high": 26376.09, "low": 26074.09, "close": 26356.48, "close_side": null, "time": 1795194000}, {"kind": "gap", "level": "PDL", "high": 26429.47, "low": 26149.51, "close": 26151.64, "close_side": "PDL", "time": 1795194900}]}`
- Niveles reconstruidos: **18** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **695** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **133**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **6** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 562, "horizontal_lines": 18, "event_markers": 15} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **23** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BULLISH`, estado `WAIT_LTF_CONFIRMATION`, motivo `ok`.
- Niveles de referencia: PDH=27751.62, PDL=26356.01, LAST_FRIDAY_HIGH=26505.38, LAST_FRIDAY_LOW=24907.97, PDL=27911.37, PDL=27911.37, PDL=27606.3, PDL=27606.3.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BULLISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/NDX100_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
