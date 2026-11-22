# NZDUSD — radiografía técnica ICT 3.0

> Generado desde la salida real de `ict.ict_chart` (revisión `f453bf2a9d35997cec774048a7ead25237399ac9`). Modo del motor: **OBSERVE_ONLY_NO_ORDER**. `entry_authorized` se conserva sin modificar.

## 1. Identificación y snapshot

- Instrumento: `NZDUSD`
- Marco solicitado: `M15`; base temporal: `Reloj MT5`
- `asof`: 1795218300 (2026-11-20T23:45:00Z)
- Última vela cerrada: 1795218300 (2026-11-20T23:45:00Z)
- Cierre por temporalidad: D1=1795132800 (2026-11-20T00:00:00Z), H4=1795204800 (2026-11-20T20:00:00Z), H1=1795215600 (2026-11-20T23:00:00Z), M15=1795218300 (2026-11-20T23:45:00Z)
- Sesgo: **BEARISH** · estado: **WAIT_CONTEXT** · motivo: `short_in_discount`

## 2. Procedencia y cobertura de datos

- Fuente: terminal MetaTrader5 conectada; el motor lee velas con `BAR_COUNT=550` por temporalidad y excluye la vela posición 0.
- Perfil calculado: `D1, H4, H1, M15`. M5/M1 solo se cargan si hay retest M15: `load.load_reason=NOT_REQUESTED_NO_M15_RETEST`.
- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte en `data_quality.md`. No existe base SQL en esta copia.

## 3. Estructura por temporalidad

| TF | Régimen (salida real) | Zonas (marks) |
|---|---|---|
| D1 | BEARISH | ver chart_objects.json por TF |
| H4 | BEARISH | ver chart_objects.json por TF |
| H1 | BEARISH | ver chart_objects.json por TF |
| M15 | BEARISH | 130 |

- Estructura LTF: `{"bars": 120, "bos_dir": 0, "momentum": -1, "trend": "BEARISH"}`
- Retest: `"OBSERVED"`

## 4. Mapa de liquidez

- PDH/PDL y eventos diarios: `{"pdh": 0.55335, "pdl": 0.54801, "source_open": 1795046400, "session_open": 1795132800, "pdh_m15_open": 1795095900, "pdl_m15_open": 1795130100, "m15_count": 95, "events": [{"kind": "sweep", "level": "PDL", "high": 0.54869, "low": 0.54799, "close": 0.54849, "close_side": null, "time": 1795133700}, {"kind": "break", "level": "PDL", "high": 0.54842, "low": 0.54748, "close": 0.54775, "close_side": "PDL", "time": 1795136400}, {"kind": "late_return", "level": "PDL", "high": 0.54814, "low": 0.54793, "close": 0.54805, "close_side": null, "time": 1795140000}, {"kind": "sweep", "level": "PDL", "high": 0.54858, "low": 0.54789, "close": 0.54854, "close_side": null, "time": 1795140900}, {"kind": "sweep", "level": "PDL", "high": 0.54832, "low": 0.54789, "close": 0.5483, "close_side": null, "time": 1795148100}, {"kind": "break", "level": "PDL", "high": 0.54846, "low": 0.54798, "close": 0.54799, "close_side": "PDL", "time": 1795202100}, {"kind": "late_return", "level": "PDL", "high": 0.54819, "low": 0.54791, "close": 0.54805, "close_side": null, "time": 1795203000}, {"kind": "break", "level": "PDL", "high": 0.54822, "low": 0.54792, "close": 0.54797, "close_side": "PDL", "time": 1795203900}]}`
- Niveles reconstruidos: **19** (ver `liquidity.json`).
- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión como campos dedicados; no se inventan.

## 5. Catálogo de POI

- Zonas/POI reconstruidas: **632** (ver `poi.json` con IDs, TF de origen, precios y timestamps).
- `pois` del motor (candidatos cross-TF): **0**.
- `marks` del marco M15: **130**. Tipos presentes: FVG, OB.

## 6. Secuencia de eventos ICT

- Eventos: **6** · estado(s): ACCEPTANCE_LOST, ACCEPTED_BREAK_WAIT_RETEST, POI_INVALID
- Esquema: `0.2-research` · modo: `OBSERVE_ONLY_NO_ORDER`
- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, `transition_history`, POI candidatos y `wait_reason` (ver `events.json`).

## 7. Mitigación / validez

- El motor no publica un campo `lifecycle` independiente por POI; la validez se observa en `link_state`, `current_state` y `transition_history` de cada evento.
- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` y `at` para cortes causales.

## 8-9. Confluencias y representación del gráfico

- Objetos: {"zones": 502, "horizontal_lines": 19, "event_markers": 13} (ver `chart_objects.json` con coordenadas e IDs).
- Book 22 (modelos del libro): **37** registros reales en `analysis.json`.

## 10. Escenarios observados y niveles

- Escenario observado por el motor: sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `short_in_discount`.
- Niveles de referencia: PDH=0.55335, PDL=0.54801, LAST_FRIDAY_HIGH=0.55118, LAST_FRIDAY_LOW=0.54631, PDL=0.55395, PDL=0.55395, PDL=0.55204, PDL=0.55204.
- No se emite recomendación BUY/SELL: el modo del motor es `OBSERVE_ONLY_NO_ORDER` y `entry_authorized` es false en los eventos.

## 11. Contradicciones y datos faltantes

- `h1_opposes_short` aparece como motivo: H1=BEARISH frente a D1=BEARISH/H4=BEARISH; es una contradicción **real del motor**.
- M5/M1: NOT_REQUESTED_NO_M15_RETEST; cobertura {"m5_bars_closed": 0, "m1_bars_closed": 0, "m5_first_closed": null, "m1_first_closed": null, "events_requested": 0}.
- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.

## 12. Evidencia verificable

- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, `chart_objects.json`; copia sin procesar en `../evidence/raw/NZDUSD_*.json`.
- `engine_source`=f453bf2a9d35997cec774048a7ead25237399ac9, `schema_version`=0.2-research.
