# XAUUSD — ICT 3.0 · apertura Nueva York 2026-11-27

> Salida real de `ict.ict_chart`, revisión `f453bf2a9d35997cec774048a7ead25237399ac9`. Modo: **OBSERVE_ONLY_NO_ORDER**. Sin autorización de operación.

## Sesión y corte

- Apertura configurada: 08:00 America/New_York = 2026-11-27T13:00:00+00:00 UTC = 2026-11-27T08:00:00-05:00 Ecuador = 2026-11-27T15:00:00Z reloj MT5.
- Corte: 08:30 America/New_York = 2026-11-27T13:30:00+00:00 UTC = 2026-11-27T08:30:00-05:00 Ecuador = 2026-11-27T15:30:00Z reloj MT5.
- Offset del broker: `7200` s. Los epochs nativos del motor están en reloj MT5.

## Doble vela M15 verificada

- M15 #1: abre 2026-11-27T13:00:00Z (real UTC), cierra 2026-11-27T13:15:00Z; O 3669.42 H 3671.14 L 3655.67 C 3657.25; finalizada=True.
- M15 #2: abre 2026-11-27T13:15:00Z (real UTC), cierra 2026-11-27T13:30:00Z; O 3657.26 H 3659.15 L 3644.04 C 3648.03; finalizada=True.
- Segundo cierre respecto a la caja: cierre 3648.03 por debajo del mínimo 3655.67 de la caja (-7.64).
- Estado de la prueba: `VERIFIED`; motor: `CUTOFF_CONFIRMED`.

## Estructura y eventos del motor

- Régimen D1/H4/H1/M15: D1=BEARISH, H4=BULLISH, H1=BULLISH, M15=BULLISH
- Sesgo `BEARISH`, estado `WAIT_CONTEXT`, motivo `h4_against_short`.
- Eventos ICT3: 6; POI/zonas: poi=678, marks=130.
- `asof` real UTC: `2026-11-27T13:30:00Z`; última M15 cerrada real UTC: `2026-11-27T13:30:00Z`.
- No se inventa lifecycle por zona; no se usan velas posteriores al corte.

