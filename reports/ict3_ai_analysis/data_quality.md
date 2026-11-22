# Calidad y cobertura de datos

Este documento solo consigna cifras verificadas por el inventario real (`database/data_inventory.json`) y por el código del motor.

## Datos usados por el motor en vivo

- Terminal MetaTrader5 conectada; `ict.read_bars` solicita `BAR_COUNT + 1 = 551` velas por temporalidad y `closed_frame` descarta la vela posición 0.
- Perfil: `D1, H4, H1, M15`. M5/M1 se solicitan solo si aparece un retest M15; si fallan, el motor registra `load.load_reason` en lugar de inventar confirmaciones.
- Los cortes causales usan `at` y `asof`; `closed_frame` exige cierre <= cutoff.

## Dataset histórico publicado

- `D1`: 6258 filas, 2006-01-01 → 2025-12-31, 271857 bytes, columnas ['time', 'open', 'high', 'low', 'close'], huecos detectados=1043, SHA256 coincide con manifiesto=False.
- `H4`: 32133 filas, 2006-01-01 20:00:00 → 2025-12-31 20:00:00, 1685328 bytes, columnas ['time', 'open', 'high', 'low', 'close'], huecos detectados=1057, SHA256 coincide con manifiesto=False.
- `H1`: 124377 filas, 2006-01-01 21:00:00 → 2025-12-31 21:00:00, 6523705 bytes, columnas ['time', 'open', 'high', 'low', 'close'], huecos detectados=1069, SHA256 coincide con manifiesto=False.

**Discrepancia verificada:** el SHA256 declarado en `SHA256SUMS` no coincide con el calculado en D1, H4, H1. Se reporta, no se corrige ni se oculta.
Este dato es real y debe tenerse en cuenta al verificar la procedencia del dataset.

## Inventario real

- Instrumentos en catálogo: 33 (forex, índices y materias primas).
- MT5 conectado: True; versión de terminal: 6325.
- Bases de datos `.db`/`.sqlite`/`.sql` encontradas: 0.
- Los datos financieros y de identificación de la cuenta y las rutas locales del terminal se han eliminado del inventario publicado; solo se conserva el estado de conexión.

## Símbolos con datos reales

- `AUDCAD`
- `AUDCHF`
- `AUDJPY`
- `AUDUSD`
- `CADCHF`
- `CADJPY`
- `EURAUD`
- `EURCAD`
- `EURCHF`
- `EURGBP`
- `EURJPY`
- `EURNZD`
- `EURUSD`
- `GBPAUD`
- `GBPCAD`
- `GBPCHF`
- `GBPJPY`
- `GBPNZD`
- `GBPUSD`
- `GER30`
- `NDX100`
- `NZDCAD`
- `NZDCHF`
- `NZDJPY`
- `NZDUSD`
- `SPX500`
- `UKOUSD`
- `US30`
- `USDCAD`
- `USDCHF`
- `USDJPY`
- `USOUSD`
- `XAUUSD`

## Límites que no se han superado artificialmente

- No se amplió `BAR_COUNT`; un análisis con corte muy antiguo puede carecer de M15 suficiente.
- No se rellenan huecos de velas ni se interpolan precios.
- No hay base SQL verificable en esta copia (ver `database/README.md`).
- No se publican credenciales, números de cuenta ni datos privados de la terminal.
