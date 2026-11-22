# EURCHF — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `EURCHF`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BEARISH** · estado: **WAIT_CONTEXT** · motivo: `h1_opposes_short`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=M5_M1_LOADED`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BEARISH | ver chart_objects.json por TF |
| H4 | BEARISH | ver chart_objects.json por TF |
| H1 | BULLISH | ver chart_objects.json por TF |
| M15 | BEARISH | 127 |

- Estructura LTF: `{"bars": 120, "bos_dir": 1, "momentum": 1, "trend": "BULLISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.92747, "pdl": 0.92408, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795107600, "pdl_m15_open": 1795046400, "m15_count": 95, "events": [{"kind": "sweep", "level": "PDL", "high": 0.92526, "low": 0.9233, "close": 0.9252, "close_side": null, "time": 1795134600}, {"kind": "sweep", "level": "PDL", "high": 0.92473, "low": 0.924, "close": 0.92427, "close_side": null, "time": 1795171500}, {"kind": "sweep", "level": "PDL", "high": 0.92467, "low": 0.92382, "close": 0.92439, "close_side": null, "time": 1795172400}, {"kind": "sweep", "level": "PDL", "high": 0.92464, "low": 0.9239, "close": 0.92415, "close_side": null, "time": 1795173300}, {"kind": "break", "level": "PDL", "high": 0.92459, "low": 0.92394, "close": 0.92399, "close_side": "PDL", "time": 1795174200}]}`
- Niveles reconstruidos: **15** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **562** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **127**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 435, "horizontal_lines": 15, "event_markers": 12} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **12** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h1_opposes_short`.
- Niveles de referencia: PDH=0.92747, PDL=0.92408, LAST_FRIDAY_HIGH=0.9262, LAST_FRIDAY_LOW=0.91949, PDH=0.92418, PDH=0.92418, PDL=0.9224, PDH=0.92489.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795053900, "m1_first_closed": 1795186200, "events_requested": 1}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/EURCHF_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
