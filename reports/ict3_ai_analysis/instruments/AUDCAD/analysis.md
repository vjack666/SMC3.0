# AUDCAD — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `AUDCAD`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BULLISH** · estado: **WAIT_CONTEXT** · motivo: `h4_against_long`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=M5_M1_LOADED`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BULLISH | ver chart_objects.json por TF |
| H4 | BEARISH | ver chart_objects.json por TF |
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BULLISH | 133 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BULLISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.96312, "pdl": 0.95329, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795054500, "pdl_m15_open": 1795114800, "m15_count": 95, "events": [{"kind": "sweep", "level": "PDL", "high": 0.95437, "low": 0.95324, "close": 0.9543, "close_side": null, "time": 1795139100}, {"kind": "boundary_close", "level": "PDL", "high": 0.95442, "low": 0.95321, "close": 0.95329, "close_side": null, "time": 1795142700}, {"kind": "sweep", "level": "PDL", "high": 0.95414, "low": 0.95306, "close": 0.95411, "close_side": null, "time": 1795143600}, {"kind": "break", "level": "PDL", "high": 0.95423, "low": 0.95275, "close": 0.95307, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 0.95399, "low": 0.95308, "close": 0.95356, "close_side": null, "time": 1795152600}, {"kind": "break", "level": "PDL", "high": 0.95392, "low": 0.95316, "close": 0.95325, "close_side": "PDL", "time": 1795176000}, {"kind": "late_return", "level": "PDL", "high": 0.95396, "low": 0.95312, "close": 0.95347, "close_side": null, "time": 1795176900}, {"kind": "sweep", "level": "PDL", "high": 0.95438, "low": 0.95323, "close": 0.95436, "close_side": null, "time": 1795177800}, {"kind": "sweep", "level": "PDL", "high": 0.95372, "low": 0.95314, "close": 0.95354, "close_side": null, "time": 1795186800}, {"kind": "break", "level": "PDL", "high": 0.95384, "low": 0.95324, "close": 0.95327, "close_side": "PDL", "time": 1795187700}, {"kind": "late_return", "level": "PDL", "high": 0.95371, "low": 0.95307, "close": 0.95332, "close_side": null, "time": 1795188600}, {"kind": "sweep", "level": "PDL", "high": 0.9536, "low": 0.95281, "close": 0.95353, "close_side": null, "time": 1795189500}, {"kind": "break", "level": "PDL", "high": 0.95346, "low": 0.95287, "close": 0.95313, "close_side": "PDL", "time": 1795195800}]}`
- Niveles reconstruidos: **18** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **596** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **133**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 463, "horizontal_lines": 18, "event_markers": 12} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **42** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BULLISH`, estado `WAIT_CONTEXT`, motivo `h4_against_long`.
- Niveles de referencia: PDH=0.96312, PDL=0.95329, LAST_FRIDAY_HIGH=0.95682, LAST_FRIDAY_LOW=0.94797, PDL=0.96954, PDL=0.96508, PDL=0.96508, PDL=0.96253.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BULLISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795054200, "m1_first_closed": 1795186200, "events_requested": 2}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/AUDCAD_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
