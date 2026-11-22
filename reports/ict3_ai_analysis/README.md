# ICT 3.0 — exportación forense para interpretación por IA

Generado: 2026-11-22T20:56:41Z · revisión del motor: `f453bf2a9d35997cec774048a7ead25237399ac9`

Este paquete expone **la salida real del motor ICT 3.0**, sin un segundo motor de análisis y sin
conclusiones subjetivas. Está pensado para que otra IA reconstruya lo que el sistema observa.

## Índice

- `snapshot_global.md` — estado de todos los instrumentos auditados.
- `motor_capabilities.md` — qué módulos están operativos, parciales o experimentales.
- `data_quality.md` — procedencia, cobertura, huecos y límites de los datos.
- `schema.json` — árbol real de claves de los JSON publicados.
- `instruments/<SÍMBOLO>/` — `analysis.md`, `analysis.json`, `poi.json`, `liquidity.json`,
  `events.json`, `chart_objects.json`.
- `evidence/raw/` — copia sin procesar de `ict_chart` por instrumento y temporalidad.
- `evidence/export_script.py` — generador exacto, para reproducibilidad.
- `database/` — inventario y aclaración sobre la ausencia de SQL en esta copia.
- `manifest.json` — checksums SHA-256 de todos los archivos.

## Cómo leer un instrumento

1. `analysis.md`: narrativa técnica con los campos reales del motor.
2. `events.json`: secuencia causal Liquidity → Sweep → Displacement → retest → POI, con
   `transition_history` y `wait_reason`.
3. `poi.json`: identidad de cada zona (ID, tipo, temporalidad de origen, precios, timestamps).
4. `liquidity.json`: PDH/PDL, referencia del viernes y niveles de ruptura del motor.
5. `chart_objects.json`: objetos reconstruibles con coordenadas e identificadores cruzados.

## Reglas respetadas

- No se inventan datos: lo que el motor no expone se declara como no expuesto.
- No se altera `mode`, `entry_authorized`, `can_trade` ni `training_eligible`.
- No se emite BUY/SELL: el modo es `OBSERVE_ONLY_NO_ORDER`.
- No se usan velas no cerradas para reconstruir eventos históricos.

## Verificación

Cada archivo tiene su SHA-256 en `manifest.json`. La fuente es
`https://github.com/vjack666/SMC3.0`, rama `main`, carpeta `reports/ict3_ai_analysis/`.
