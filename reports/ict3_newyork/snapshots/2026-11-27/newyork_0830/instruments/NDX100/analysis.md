# NDX100 — ICT 3.0 · apertura Nueva York 2026-11-27

> Salida real de `ict.ict_chart`, revisión `f453bf2a9d35997cec774048a7ead25237399ac9`. Modo: **OBSERVE_ONLY_NO_ORDER**. Sin autorización de operación.

## Sesión y corte

- Apertura configurada: 08:00 America/New_York = 2026-11-27T13:00:00+00:00 UTC = 2026-11-27T08:00:00-05:00 Ecuador = 2026-11-27T15:00:00Z reloj MT5.
- Corte: 08:30 America/New_York = 2026-11-27T13:30:00+00:00 UTC = 2026-11-27T08:30:00-05:00 Ecuador = 2026-11-27T15:30:00Z reloj MT5.
- Offset del broker: `7200` s. Los epochs nativos del motor están en reloj MT5.

## Doble vela M15 verificada

- M15 #1: abre 2026-11-27T13:00:00Z (real UTC), cierra 2026-11-27T13:15:00Z; O 26681.49 H 26695.12 L 26660.49 C 26679.62; finalizada=True.
- M15 #2: abre 2026-11-27T13:15:00Z (real UTC), cierra 2026-11-27T13:30:00Z; O 26679.74 H 26680.87 L 26629.87 C 26640.24; finalizada=True.
- Segundo cierre respecto a la caja: cierre 26640.24 por debajo del mínimo 26660.49 de la caja (-20.25).
- Estado de la prueba: `VERIFIED`; motor: `CUTOFF_CONFIRMED`.

## Estructura y eventos del motor

- Régimen D1/H4/H1/M15: D1=BULLISH, H4=BULLISH, H1=BEARISH, M15=BULLISH
- Sesgo `BULLISH`, estado `WAIT_CONTEXT`, motivo `h1_opposes_long`.
- Eventos ICT3: 7; POI/zonas: poi=692, marks=131.
- `asof` real UTC: `2026-11-27T13:30:00Z`; última M15 cerrada real UTC: `2026-11-27T13:30:00Z`.
- No se inventa lifecycle por zona; no se usan velas posteriores al corte.

