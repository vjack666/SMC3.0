# NZDCHF — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `NZDCHF`
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
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BEARISH | 108 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": 1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.46612, "pdl": 0.46214, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795095900, "pdl_m15_open": 1795046400, "m15_count": 95, "events": [{"kind": "sweep", "level": "PDL", "high": 0.46288, "low": 0.46182, "close": 0.46278, "close_side": null, "time": 1795133700}, {"kind": "sweep", "level": "PDL", "high": 0.46287, "low": 0.4617, "close": 0.46283, "close_side": null, "time": 1795134600}, {"kind": "break", "level": "PDL", "high": 0.46257, "low": 0.46183, "close": 0.46204, "close_side": "PDL", "time": 1795136400}, {"kind": "late_return", "level": "PDL", "high": 0.4625, "low": 0.46196, "close": 0.46239, "close_side": null, "time": 1795137300}, {"kind": "sweep", "level": "PDL", "high": 0.4625, "low": 0.46212, "close": 0.46223, "close_side": null, "time": 1795138200}, {"kind": "touch", "level": "PDL", "high": 0.46255, "low": 0.46214, "close": 0.46255, "close_side": null, "time": 1795139100}, {"kind": "break", "level": "PDL", "high": 0.46268, "low": 0.46207, "close": 0.46209, "close_side": "PDL", "time": 1795151700}, {"kind": "late_return", "level": "PDL", "high": 0.46243, "low": 0.46208, "close": 0.46234, "close_side": null, "time": 1795152600}, {"kind": "sweep", "level": "PDL", "high": 0.46275, "low": 0.4621, "close": 0.4627, "close_side": null, "time": 1795177800}, {"kind": "sweep", "level": "PDL", "high": 0.46232, "low": 0.46196, "close": 0.46218, "close_side": null, "time": 1795186800}, {"kind": "break", "level": "PDL", "high": 0.46232, "low": 0.46143, "close": 0.46143, "close_side": "PDL", "time": 1795187700}]}`
- Niveles reconstruidos: **20** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **536** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **108**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 428, "horizontal_lines": 20, "event_markers": 11} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **38** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h4_against_short`.
- Niveles de referencia: PDH=0.46612, PDL=0.46214, LAST_FRIDAY_HIGH=0.46409, LAST_FRIDAY_LOW=0.45862, PDL=0.46196, PDL=0.46196, PDL=0.46116, PDL=0.46116.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BEARISH/H4=BULLISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795054200, "m1_first_closed": 1795186200, "events_requested": 1}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/NZDCHF_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
