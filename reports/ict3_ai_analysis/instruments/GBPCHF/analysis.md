# GBPCHF — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `GBPCHF`
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
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BULLISH | 115 |

- Estructura LTF: `{"bars": 120, "bos_dir": 1, "momentum": 1, "trend": "BULLISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 1.10929, "pdl": 1.10414, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795079700, "pdl_m15_open": 1795114800, "m15_count": 95, "events": [{"kind": "break", "level": "PDL", "high": 1.10458, "low": 1.10328, "close": 1.10357, "close_side": "PDL", "time": 1795133700}, {"kind": "late_return", "level": "PDL", "high": 1.10424, "low": 1.10143, "close": 1.10423, "close_side": null, "time": 1795134600}, {"kind": "sweep", "level": "PDL", "high": 1.10427, "low": 1.10393, "close": 1.10417, "close_side": null, "time": 1795135500}, {"kind": "break", "level": "PDL", "high": 1.10451, "low": 1.10405, "close": 1.10405, "close_side": "PDL", "time": 1795136400}, {"kind": "late_return", "level": "PDL", "high": 1.10466, "low": 1.10391, "close": 1.10461, "close_side": null, "time": 1795137300}, {"kind": "break", "level": "PDL", "high": 1.10458, "low": 1.10348, "close": 1.10351, "close_side": "PDL", "time": 1795142700}, {"kind": "late_return", "level": "PDL", "high": 1.10429, "low": 1.10381, "close": 1.1042, "close_side": null, "time": 1795154400}, {"kind": "break", "level": "PDL", "high": 1.10429, "low": 1.10386, "close": 1.10402, "close_side": "PDL", "time": 1795155300}, {"kind": "boundary_close", "level": "PDL", "high": 1.1042, "low": 1.10364, "close": 1.10414, "close_side": null, "time": 1795165200}, {"kind": "gap", "level": "PDL", "high": 1.10523, "low": 1.10376, "close": 1.10515, "close_side": null, "time": 1795166100}, {"kind": "sweep", "level": "PDL", "high": 1.10547, "low": 1.10405, "close": 1.10421, "close_side": null, "time": 1795167000}, {"kind": "sweep", "level": "PDL", "high": 1.10478, "low": 1.10391, "close": 1.10473, "close_side": null, "time": 1795167900}, {"kind": "sweep", "level": "PDL", "high": 1.10509, "low": 1.10359, "close": 1.10418, "close_side": null, "time": 1795169700}, {"kind": "sweep", "level": "PDL", "high": 1.10483, "low": 1.10392, "close": 1.10452, "close_side": null, "time": 1795170600}, {"kind": "sweep", "level": "PDL", "high": 1.10469, "low": 1.1038, "close": 1.10416, "close_side": null, "time": 1795171500}, {"kind": "sweep", "level": "PDL", "high": 1.10446, "low": 1.10373, "close": 1.10426, "close_side": null, "time": 1795172400}, {"kind": "boundary_close", "level": "PDL", "high": 1.10467, "low": 1.10394, "close": 1.10414, "close_side": null, "time": 1795173300}, {"kind": "break", "level": "PDL", "high": 1.10474, "low": 1.10393, "close": 1.104, "close_side": "PDL", "time": 1795174200}]}`
- Niveles reconstruidos: **15** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **546** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **115**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTED_BREAK_WAIT_RETEST, EXPANSION_NO_ENTRY, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 431, "horizontal_lines": 15, "event_markers": 12} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **22** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h4_against_short`.
- Niveles de referencia: PDH=1.10929, PDL=1.10414, LAST_FRIDAY_HIGH=1.10547, LAST_FRIDAY_LOW=1.09714, PDH=1.10598, PDH=1.10941, PDH=1.10964, PDH=1.10964.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BEARISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/GBPCHF_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
