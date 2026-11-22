# US30 — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `US30`
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
| M15 | BEARISH | 135 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 50583.01, "pdl": 48982.73, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795095000, "pdl_m15_open": 1795131900, "m15_count": 91, "events": [{"kind": "break", "level": "PDL", "high": 49028.63, "low": 48961.63, "close": 48965.13, "close_side": "PDL", "time": 1795158900}, {"kind": "late_return", "level": "PDL", "high": 49024.63, "low": 48945.33, "close": 48987.13, "close_side": null, "time": 1795159800}, {"kind": "break", "level": "PDL", "high": 48992.13, "low": 48931.33, "close": 48949.13, "close_side": "PDL", "time": 1795160700}, {"kind": "late_return", "level": "PDL", "high": 49033.13, "low": 48942.63, "close": 48996.33, "close_side": null, "time": 1795161600}, {"kind": "sweep", "level": "PDL", "high": 49054.63, "low": 48981.33, "close": 49020.13, "close_side": null, "time": 1795162500}, {"kind": "sweep", "level": "PDL", "high": 49039.13, "low": 48981.63, "close": 49004.13, "close_side": null, "time": 1795163400}, {"kind": "break", "level": "PDL", "high": 49029.13, "low": 48955.63, "close": 48971.13, "close_side": "PDL", "time": 1795164300}, {"kind": "late_return", "level": "PDL", "high": 49019.13, "low": 48946.13, "close": 49009.13, "close_side": null, "time": 1795165200}, {"kind": "sweep", "level": "PDL", "high": 49020.63, "low": 48952.13, "close": 49009.63, "close_side": null, "time": 1795166100}, {"kind": "break", "level": "PDL", "high": 49032.13, "low": 48951.13, "close": 48973.13, "close_side": "PDL", "time": 1795167000}, {"kind": "late_return", "level": "PDL", "high": 49089.13, "low": 48961.13, "close": 49038.13, "close_side": null, "time": 1795167900}, {"kind": "sweep", "level": "PDL", "high": 49081.63, "low": 48978.63, "close": 49004.13, "close_side": null, "time": 1795176000}, {"kind": "break", "level": "PDL", "high": 49029.13, "low": 48934.63, "close": 48934.63, "close_side": "PDL", "time": 1795185900}, {"kind": "late_return", "level": "PDL", "high": 48996.63, "low": 48893.13, "close": 48994.13, "close_side": null, "time": 1795190400}, {"kind": "sweep", "level": "PDL", "high": 49196.98, "low": 48969.99, "close": 49169.13, "close_side": null, "time": 1795198500}, {"kind": "break", "level": "PDL", "high": 49085.27, "low": 48872.78, "close": 48882.91, "close_side": "PDL", "time": 1795200300}]}`
- Niveles reconstruidos: **17** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **682** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **135**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **6** · estado(s): ACCEPTED_BREAK_WAIT_RETEST, EXPANSION_NO_ENTRY, POI_INVALID, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 547, "horizontal_lines": 17, "event_markers": 16} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **16** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h4_against_short`.
- Niveles de referencia: PDH=50583.01, PDL=48982.73, LAST_FRIDAY_HIGH=49585.13, LAST_FRIDAY_LOW=47992.52, PDL=52218.91, PDL=52218.91, PDL=52007.82, PDL=52007.82.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795050600, "m1_first_closed": 1795186080, "events_requested": 2}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/US30_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
