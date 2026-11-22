# ICT 3.0 — Simulación causal de observación en 26 pares

Generado: 2026-11-21 20:36 UTC

> Esta ejecución no es un backtest. No calcula rentabilidad, fills, órdenes,
> lotaje ni curva de capital. Solo reinterpreta velas cerradas de MT5 para
> entrenar/inspeccionar la máquina de estados propuesta para rupturas de
> PDH/PDL.

## Alcance de datos

- Símbolos: 26 pares Forex confirmados.
- Solicitud máxima del script: 5,000 velas M15 y 2,000 velas D1 por símbolo.
- El terminal puede devolver menos barras según su historial local; el informe conserva la cobertura real.
- Solo se usan prefijos hasta la última M15 cerrada de cada símbolo.
- Fuente: cuenta MT5 configurada en `data/cuenta.json`; no se envían solicitudes de trading.

## Estados agregados

| Estado | Conteo |
|---|---:|
| `ACCEPTED_BREAK_WAIT_RETEST` | 1101 |
| `FAILED_BREAK` | 1247 |

## Cobertura por símbolo

| Símbolo | D1 | M15 solicitadas | M15 cerradas | Rango D1 | Rango M15 | Estudios | Fuertes | Aceptadas |
|---|---:|---:|---:|---|---|---:|---:|---:|
| EURUSD | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 91 | 16 | 12 |
| EURAUD | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 83 | 8 | 4 |
| EURCAD | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 85 | 8 | 6 |
| EURCHF | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 21:45 UTC → 2026-11-20 23:45 UTC | 92 | 15 | 9 |
| EURGBP | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 99 | 12 | 6 |
| EURJPY | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 95 | 13 | 11 |
| EURNZD | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 89 | 9 | 6 |
| AUDCAD | 2,000 | 5,000 | 4,999 | 2019-03-13 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 96 | 14 | 5 |
| AUDCHF | 2,000 | 5,000 | 4,999 | 2019-03-13 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 80 | 8 | 5 |
| AUDJPY | 2,000 | 5,000 | 4,999 | 2019-03-13 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 91 | 16 | 11 |
| AUDUSD | 2,000 | 5,000 | 4,999 | 2019-03-13 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 86 | 9 | 4 |
| GBPUSD | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 90 | 8 | 7 |
| GBPAUD | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 104 | 8 | 6 |
| GBPCAD | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 87 | 7 | 4 |
| GBPCHF | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 86 | 13 | 8 |
| GBPJPY | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 87 | 13 | 9 |
| GBPNZD | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 100 | 10 | 6 |
| NZDCAD | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 84 | 11 | 6 |
| NZDCHF | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 92 | 11 | 7 |
| NZDJPY | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 94 | 14 | 11 |
| NZDUSD | 777 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 90 | 12 | 5 |
| USDCAD | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 98 | 13 | 9 |
| USDCHF | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 21:45 UTC → 2026-11-20 23:45 UTC | 95 | 13 | 8 |
| USDJPY | 751 | 5,000 | 4,999 | 2024-01-01 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 83 | 17 | 15 |
| CADCHF | 2,000 | 5,000 | 4,999 | 2019-03-13 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 86 | 11 | 8 |
| CADJPY | 2,000 | 5,000 | 4,999 | 2020-01-31 00:00 UTC → 2026-11-19 00:00 UTC | 2026-09-09 22:00 UTC → 2026-11-20 23:45 UTC | 85 | 9 | 8 |

## Lectura de resultados

- `BREAK_CANDIDATE` es un primer cierre fuera del PDH/PDL aún sin aceptación.
- `FAILED_BREAK` vuelve a separar ruptura fallida de sweep/ruptura sostenida.
- `ACCEPTED_BREAK_WAIT_RETEST` confirma dos cierres consecutivos fuera; no es una entrada.
- La simulación no promueve una ruptura a setup si faltan POI, retest o stop estructural.
- Una muestra grande de aceptadas fuertes sin retest debe etiquetarse como `EXPANSION_NO_ENTRY`, no como oportunidad perdida imputable al motor.

## EURAUD y el caso de estudio

El caso EURAUD del 20 de noviembre de 2026 queda documentado en `docs/ict3/01_RUPTURA_FUERTE_LIQUIDEZ_DIARIA.md`. La simulación general no sustituye ese expediente: sirve para comprobar si la misma separación entre ruptura aceptada, retest y setup aparece en otros símbolos.

## Mediocridades y fallas que esta simulación puede revelar

1. **Etiquetado binario prematuro:** descartar por `no_stop_structure` borra una ruptura observada antes de que exista un retest.
2. **Duplicación de eventos:** una misma permanencia fuera del nivel no debe generar una nueva ruptura cada vela; solo el cruce inicial y la aceptación.
3. **Confusión de mecha y cierre:** una mecha fuera con cierre dentro es sweep, no breakout aceptado.
4. **Fuga temporal:** ningún target o estado posterior debe usar velas que aún no existían en el corte.
5. **Falsa precisión del volumen:** el tick volume de FX es relativo al feed MT5 y no puede convertirse en confirmación institucional centralizada.
6. **Ruptura sin entrada:** continuar sin volver al FVG/OB es un resultado válido, no un fallo de ejecución del modelo.

## Mejoras siguientes

- Correlacionar cada `ACCEPTED_BREAK_WAIT_RETEST` con FVG/OB canónico y retest M15, después bajar a M5/M1.
- Añadir estados persistentes `RETESTING_POI`, `OBSERVABLE_SETUP`, `EXPANSION_NO_ENTRY` e `INVALIDATED` al payload del motor.
- Calibrar los umbrales de fuerza por símbolo y sesión, sin convertirlos en reglas firmadas hasta tener validación fuera de muestra.
- Crear un expediente causal por evento con nivel roto, fuerza, contexto D1/H4/H1, POI, retest, stop disponible y motivo de espera.
- Repetir la simulación en una ventana de validación separada; no usar estas mismas observaciones para afirmar ventaja estadística.

## Limitación importante

Esta simulación entrena la representación y la trazabilidad de la lectura; no demuestra que una estrategia sea rentable ni autoriza automatización de órdenes.
