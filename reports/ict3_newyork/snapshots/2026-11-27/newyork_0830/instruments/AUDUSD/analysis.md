# AUDUSD — ICT 3.0 · apertura Nueva York 2026-11-27

> Salida real de `ict.ict_chart`, revisión `f453bf2a9d35997cec774048a7ead25237399ac9`. Modo: **OBSERVE_ONLY_NO_ORDER**. Sin autorización de operación.

## Sesión y corte

- Apertura configurada: 08:00 America/New_York = 2026-11-27T13:00:00+00:00 UTC = 2026-11-27T08:00:00-05:00 Ecuador = 2026-11-27T15:00:00Z reloj MT5.
- Corte: 08:30 America/New_York = 2026-11-27T13:30:00+00:00 UTC = 2026-11-27T08:30:00-05:00 Ecuador = 2026-11-27T15:30:00Z reloj MT5.
- Offset del broker: `7200` s. Los epochs nativos del motor están en reloj MT5.

## Doble vela M15 verificada

- M15 #1: abre 2026-11-27T13:00:00Z (real UTC), cierra 2026-11-27T13:15:00Z; O 0.66716 H 0.66716 L 0.66638 C 0.66638; finalizada=True.
- M15 #2: abre 2026-11-27T13:15:00Z (real UTC), cierra 2026-11-27T13:30:00Z; O 0.66639 H 0.6664 L 0.66549 C 0.66551; finalizada=True.
- Segundo cierre respecto a la caja: cierre 0.66551 por debajo del mínimo 0.66638 de la caja (-0.00087).
- Estado de la prueba: `VERIFIED`; motor: `CUTOFF_CONFIRMED`.

## Estructura y eventos del motor

- Régimen D1/H4/H1/M15: D1=BULLISH, H4=BEARISH, H1=BULLISH, M15=BULLISH
- Sesgo `BULLISH`, estado `WAIT_CONTEXT`, motivo `h4_against_long`.
- Eventos ICT3: 4; POI/zonas: poi=633, marks=141.
- `asof` real UTC: `2026-11-27T13:30:00Z`; última M15 cerrada real UTC: `2026-11-27T13:30:00Z`.
- No se inventa lifecycle por zona; no se usan velas posteriores al corte.

