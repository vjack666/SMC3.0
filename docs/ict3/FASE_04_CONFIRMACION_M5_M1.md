# Fase 4 — Confirmación M5/M1 y stop estructural

## Orden de trabajo para los agentes

**Mandato.** Empieza por [la corrección pendiente del lote 03](REVISION_LOTE_03_CORRECCIONES_CAUSALIDAD.md). Resuelve primero la evidencia temporal que condiciona las fases posteriores.

1. **Agente de estructura · `ict3_confirm.py`.** Verifica la defensa de la zona y el cierre M5 sobre el máximo o bajo el mínimo de referencia. Registra hora y nivel del pivote, momento de confirmación y hora de ruptura. Comprueba que la ruptura corresponda a la reacción al retest y que una mecha o M1 por sí solos dejen el evento en espera.
2. **Agente de causalidad · pruebas de confirmación.** Separa la hora del extremo y la hora en que quedó confirmado. El origen debe estar confirmado al retest. Para un extremo de reacción usa el horizonte aplicable a esa reacción. Prueba pivote tardío, vela abierta al corte, M1 ausente, stop ausente y objetivos sin estructura suficiente. Compara prefijo y serie completa al mismo corte.
3. **Agente de integración · `ict.py` y pruebas de carga.** Comprueba cuándo se solicita evidencia inferior, registra cobertura y fallos por marco, y distingue esa lectura de la que pueda pedir la vista de un gráfico M5 o M1. Muestra evidencia con EURUSD, GBPJPY y US30 cuando MT5 esté disponible.
4. **Entregable de Hermes.** Tres expedientes: espera, stop estructural ausente y setup observable. Cada uno incluye corte, fechas de disponibilidad, motivo y prueba que lo reproduce. Aceptación: cada transición ocurre cuando toda su evidencia ya es observable y `entry_authorized` permanece en `false`.

## Objetivo
Completar evidencia de un setup observable después del retest, sin autorizar ejecución.

## Trabajo
- Cargar M5/M1 solo para `RETESTING_POI` y truncar al `cutoff`.
- Exigir defensa al cierre y BOS/CHOCH/MSS M5 confirmado por cierre.
- Usar M1 solo como corroboración, nunca como sustituto de M5.
- Seleccionar stop por autoridad: origen intacto, extremo M5, extremo M1, `NO_STRUCTURAL_STOP`.
- Aplicar TP1 >= 3R y TP2 >= 5R solo con liquidez conocida.
- Para el stop de origen, exigir confirmación al retest. Para los extremos de reacción, usar el plazo causal de la reacción.

## Delegación y aceptación
Delegar pivotes M5, corroboración M1, causalidad de stops/objetivos e integración MT5 de solo lectura. Suite y replay verdes; `entry_authorized=false`; sin órdenes, lotes, volumen, fills ni P&L.
