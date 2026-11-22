# USDCHF — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `USDCHF`
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
| M15 | BULLISH | 141 |

- Estructura LTF: `{"bars": 120, "bos_dir": 1, "momentum": 1, "trend": "BULLISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.84437, "pdl": 0.84172, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795124700, "pdl_m15_open": 1795092300, "m15_count": 94, "events": [{"kind": "sweep", "level": "PDL", "high": 0.84362, "low": 0.84147, "close": 0.84356, "close_side": null, "time": 1795134600}, {"kind": "sweep", "level": "PDL", "high": 0.8421, "low": 0.84169, "close": 0.84191, "close_side": null, "time": 1795158900}, {"kind": "break", "level": "PDL", "high": 0.84214, "low": 0.84147, "close": 0.84158, "close_side": "PDL", "time": 1795164300}, {"kind": "late_return", "level": "PDL", "high": 0.84199, "low": 0.84143, "close": 0.84194, "close_side": null, "time": 1795165200}, {"kind": "sweep", "level": "PDL", "high": 0.8427, "low": 0.8417, "close": 0.84198, "close_side": null, "time": 1795167000}, {"kind": "break", "level": "PDL", "high": 0.84242, "low": 0.84136, "close": 0.84141, "close_side": "PDL", "time": 1795175100}, {"kind": "late_return", "level": "PDL", "high": 0.84221, "low": 0.84075, "close": 0.84216, "close_side": null, "time": 1795177800}, {"kind": "sweep", "level": "PDL", "high": 0.84219, "low": 0.84158, "close": 0.84197, "close_side": null, "time": 1795179600}, {"kind": "break", "level": "PDL", "high": 0.84213, "low": 0.84159, "close": 0.84163, "close_side": "PDL", "time": 1795180500}, {"kind": "late_return", "level": "PDL", "high": 0.842, "low": 0.84159, "close": 0.84186, "close_side": null, "time": 1795182300}, {"kind": "sweep", "level": "PDL", "high": 0.84236, "low": 0.84167, "close": 0.84176, "close_side": null, "time": 1795184100}, {"kind": "break", "level": "PDL", "high": 0.84176, "low": 0.8413, "close": 0.84144, "close_side": "PDL", "time": 1795185000}]}`
- Niveles reconstruidos: **18** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **664** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **141**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **5** · estado(s): ACCEPTANCE_LOST, POI_INVALID, RETESTING_POI
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 523, "horizontal_lines": 18, "event_markers": 13} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **34** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h1_opposes_short`.
- Niveles de referencia: PDH=0.84437, PDL=0.84172, LAST_FRIDAY_HIGH=0.84432, LAST_FRIDAY_LOW=0.83758, PDH=0.83614, PDH=0.83614, PDH=0.83967, PDH=0.83967.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BULLISH frente a D1=BEARISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: M5_M1_LOADED; cobertura {"m5_bars_closed": 551, "m1_bars_closed": 551, "m5_first_closed": 1795052400, "m1_first_closed": 1795186200, "events_requested": 2}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/USDCHF_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
