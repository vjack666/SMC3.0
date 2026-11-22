# Plan de trabajo de Hermes — ICT 3.0 y servidor SMC 3.0

**Responsables:** Hermes implementa; GPT revisa, prueba y corrige; Rubén decide cambios de alcance.  
**Modo:** ejecución continua por fases. Hermes delega trabajos independientes y avanza según sus dependencias. GPT conserva la aceptación final de cada fase.  
**Estado inicial verificado:** 30 pruebas aprobadas; `/api/ict?symbol=EURUSD&tf=M15` responde en `127.0.0.1:8766`; ICT 3.0 expone rupturas, pero todavía no enlaza cada ruptura aceptada con su FVG/OB, retest M15 y confirmación M5/M1.  
**Autoridad:** ICT 2.0, revisión `f453bf2a9d35997cec774048a7ead25237399ac9`. ICT 3.0 permanece como investigación.

## Objetivo

Completar en el servidor local una máquina de estados causal y explicable:

```text
BREAK_CANDIDATE
→ FAILED_BREAK
→ ACCEPTED_BREAK_WAIT_RETEST
→ RETESTING_POI
→ OBSERVABLE_SETUP / INVALIDATED / EXPANSION_NO_ENTRY
```

La cadena debe separar siempre:

1. lectura de liquidez;
2. existencia de FVG/OB canónico;
3. retorno al POI;
4. confirmación estructural M5/M1;
5. setup observable.

Un setup observable no es una orden. El servidor no puede enviar, modificar ni cerrar operaciones.

## Contrato de seguridad y evidencia

- Solo velas cerradas y disponibles en `as_of(t)`.
- Cero uso de futuro en zonas, retests, stops y objetivos.
- Mantener `entry_authorized == false` y `policy == OBSERVE_ONLY_NO_ORDER`.
- No introducir llamadas de trading de MT5.
- No reintroducir OTE/Fibonacci.
- El ATR solo puede añadir margen a una estructura ya existente.
- No usar tick volume como confirmación institucional.
- Distinguir dato observado, hipótesis de investigación y simulación.
- No modificar credenciales, cuenta, tickets, posiciones ni archivos privados de `data/`.
- Mantener el servidor ligado a `127.0.0.1` y sus validaciones actuales de `Host` y `Origin`.

## Protocolo de entrega y revisión

Para cada tarea Hermes debe enviar:

1. resumen de lo implementado;
2. archivos y funciones modificados;
3. supuestos adoptados;
4. pruebas nuevas y resultado completo de la suite;
5. ejemplo del payload antes/después;
6. riesgos o dudas pendientes;
7. confirmación explícita de que no añadió ejecución de órdenes.

GPT revisará causalidad, alcance, seguridad, pruebas y compatibilidad del servidor. Hermes priorizará las correcciones recibidas y volverá a entregar la fase afectada. Los encargos independientes pueden avanzar mientras se revisa la entrega. Los que dependan de una corrección deberán incorporar y verificar el cambio antes de integrarse.

## Estado actual — 22 de noviembre de 2026

El [índice de ejecución](00_INDICE_PLAN_CONTINUO_HERMES.md) enlaza los ocho encargos detallados y define el protocolo de delegación. Hermes continúa con los encargos disponibles sin esperar una orden manual por cada fase.

**Fase activa:** cierre de la **Tarea 8 — Integración y operación del servidor**.

- `[x]` Tarea 1 — Identidad causal y contrato de eventos: aceptada.
- `[x]` Tarea 2 — Asociación causal con FVG/OB M15: aceptada.
- `[x]` Tarea 3 — Máquina de estados M15: aceptada.
- `[x]` Tarea 4 — Confirmación M5/M1 y stop estructural: aceptada por GPT; esta sesión reverificó la base en 107/107.
- `[x]` Tarea 5 — Contrato del servidor local: aceptada por GPT tras revisar el diccionario de 61 campos y las pruebas de esquema.
- `[x]` Tarea 6 — Interfaz de análisis detallado: aceptada por GPT; la prueba específica de UI pasó 13/13 y los ganchos por etapa quedaron verificados.
- `[x]` Tarea 7 — Simulación y validación fuera de muestra: aceptada por GPT como protocolo sintético; la cobertura real permanece correctamente marcada `REAL_COVERAGE_PENDING`.
- `[~]` Tarea 8 — Integración y operación: en corrección (revisión `2b75b99c`).
  Smoke tests, registro de release y reversión: cerrados. Punto 2 (`cutoff=asof`)
  y punto 3 (render interactivo de 8 etapas): con evidencia nueva. **Sigue
  pendiente el punto 1**: cobertura viva con datos MT5 frescos; `state=stale`
  y `REAL_COVERAGE_PENDING` se mantienen. No se marca `[x]` hasta disponer de
  esa evidencia. Detalle en `RELEASE_FASE_08.md` §8.

La marca `[~]` significa “trabajo entregado, revisión/corrección pendiente”; solo `[x]` significa aceptación completa.

## Tarea 1 — Identidad causal y contrato de eventos

**Meta:** preparar una base estable antes de añadir retests.

- Añadir a cada evento de `daily_break_studies()` un `event_id` determinista construido con símbolo, sesión D1, nivel, dirección y vela de señal.
- Pasar `symbol` a la función sin romper sus llamadas actuales.
- Añadir `observed_at` y `state_time`, dejando claro cuándo era conocible el estado.
- No cambiar todavía la clasificación existente.
- Añadir pruebas para estabilidad del identificador, unicidad PDH/PDL y replay por prefijos.
- Exponer los nuevos campos en `ict3_breaks` de `/api/ict`.

**Aceptación:** el mismo prefijo produce el mismo evento y el futuro no cambia campos ya conocidos; 30 pruebas existentes y las nuevas pasan.

## Tarea 2 — Asociación causal con FVG/OB M15

**Meta:** enlazar una ruptura aceptada con zonas canónicas del impulso.

- Usar exclusivamente los objetos FVG/OB del motor ICT 2.0 fijado.
- Asociar solo zonas de la misma dirección, confirmadas después de la señal y conocidas al corte.
- Guardar `poi_candidates` con identificador, tipo, límites, confirmación y primer toque conocido.
- Explicar por qué una zona se asocia o se rechaza; no escoger por cercanía sin regla causal.
- No promover el evento a entrada ni inventar stop.
- Añadir pruebas de zona confirmada después de la señal, zona opuesta, toque anterior y ausencia de zona.

**Aceptación:** el payload distingue `accepted_without_poi` de `accepted_with_poi`; ninguna zona aparece antes de su confirmación.

## Tarea 3 — Máquina de estados M15

**Meta:** representar retorno, pérdida de aceptación y expansión sin entrada.

- Implementar transiciones explícitas desde `ACCEPTED_BREAK_WAIT_RETEST`.
- `RETESTING_POI`: contacto posterior a la confirmación del POI.
- `ACCEPTANCE_LOST`: cierre de vuelta dentro antes del retest válido.
- `POI_INVALID`: cierre que atraviesa el límite estructural de la zona.
- `EXPANSION_NO_ENTRY`: ausencia de retest al finalizar una ventana configurable y documentada.
- Conservar historial de transiciones con hora y motivo.
- Verificar replay por prefijos y evitar duplicar un evento por cada vela fuera del nivel.

**Aceptación:** cada estado es reproducible desde velas cerradas y conserva la ruptura original aunque no exista entrada.

## Tarea 4 — Confirmación M5/M1 y stop estructural

**Meta:** llegar a `OBSERVABLE_SETUP` sin autorizar ejecución.

- Cargar M5/M1 solo cuando un evento está en retest, para limitar coste.
- Exigir defensa al cierre y BOS/CHOCH/MSS confirmado en dirección de la ruptura.
- Orden del stop: swing de origen intacto, extremo estructural M5, extremo estructural M1; si no existe, `NO_STRUCTURAL_STOP`.
- Objetivo: liquidez intacta conocida al corte.
- Calcular R informativo solo cuando entrada de referencia, stop y objetivo sean causales.
- Mantener la política de planificación solicitada por Rubén: TP1 estructural de al menos 3R y TP2 de al menos 5R cuando la estructura lo permita; si no lo permite, esperar o descartar, sin fabricar niveles.
- Una idea dividida comparte invalidación y presupuesto total de riesgo; no dimensionar sin saldo y especificaciones verificadas.

**Aceptación:** el estado `OBSERVABLE_SETUP` contiene evidencia completa y sigue siendo solo observación.

## Tarea 5 — Contrato del servidor local

**Meta:** hacer visible el expediente ICT 3.0 sin degradar el servicio.

- Mantener `/api/ict` compatible y añadir un bloque versionado `ict3` con `schema_version`.
- Incluir evento actual, historial de estados, POI asociado, confirmaciones pendientes y motivos.
- Conservar las respuestas antiguas mientras la interfaz migra.
- Validar símbolo, marco y corte como hoy; mantener `127.0.0.1`, `Host`, `Origin`, `no-store` y `nosniff`.
- No añadir endpoints de órdenes ni acciones de cuenta.
- Añadir pruebas de contrato HTTP para campos mínimos, cortes inválidos y modo solo lectura.

**Aceptación:** clientes actuales siguen funcionando y el nuevo bloque se puede inspeccionar sin ambigüedad.

## Tarea 6 — Interfaz de análisis detallado

**Meta:** mostrar qué se sabe y qué falta.

- Renderizar la transición actual y su hora.
- Separar: contexto HTF, ruptura, POI, retest, confirmación M5/M1, stop, objetivos e invalidación.
- Mostrar “esperar” cuando falte cualquiera de los requisitos.
- Etiquetar de forma visible investigación, simulación y datos observados.
- No presentar una zona candidata como entrada confirmada.

**Aceptación:** la interfaz explica el motivo del estado y no usa lenguaje de orden o promesa de rentabilidad.

## Tarea 7 — Simulación y validación fuera de muestra

**Meta:** medir la representación, no afirmar rentabilidad.

- Repetir los 26 pares con cobertura real declarada.
- Separar calibración y evaluación fuera de muestra.
- Desglosar PDH/PDL, sesión, alineación D1/H4/H1, FVG/OB, ventana de retest y estado final.
- Probar invariancia `prefix_to_t == full_series_at_t`.
- Reportar errores por símbolo y no ocultarlos en agregados.
- No calcular fills, lotaje, P&L ni curva de capital hasta existir una entrada causal definida y un protocolo aparte.

**Aceptación:** informe reproducible, sin fuga temporal y sin convertir conteos en ventaja estadística.

## Tarea 8 — Integración final y operación del servidor

**Meta:** activar la actualización solo después de aprobar todas las tareas.

- Ejecutar la suite completa y una prueba temporal con MT5 accesible.
- Verificar los 26 pares y los cuatro índices donde corresponda; DXY sigue siendo referencia manual de TradingView.
- Confirmar que `/api/market`, `/api/market-universe`, `/api/ict` y la interfaz cargan la versión nueva.
- Reiniciar el servidor habitual únicamente mediante `abrir-smc.cmd`, sin eludir bloqueos del sistema.
- Documentar cómo volver a la versión anterior si falla la interfaz o el motor.
- Verificar que no se enviaron ni modificaron operaciones.

**Aceptación:** servidor nuevo confirmado en vivo, contrato compatible, pruebas aprobadas y evidencia de solo lectura.

## Punto de reanudación para Hermes

Retoma desde la fase marcada en **Estado actual**. Abre su encargo en el índice, asigna responsables y atiende primero las correcciones aplicables. Usa las fases aceptadas como referencia para las pruebas de regresión.

## Revisión `2b75b99c` — resultado de las correcciones (2026-11-22T17:00Z)

Orden ejecutado, un paso a la vez, sin consultar `/api/inbox` con el puente activo:

1. **MT5:** bloqueo explícito entregado. `state=stale`, último cierre
   `2026-11-20T23:45:00Z` (`1795218300`) frente a la consulta de
   `2026-11-22T16:51:45Z`. Sin cotización autorizada no se declara cobertura
   viva; `REAL_COVERAGE_PENDING` se mantiene.
2. **`cutoff=asof`:** 4 incidencias de US30 aisladas y explicadas por la regla
   de los dos relojes. `test_ict3_cutoff_asof.py` 3/3 OK; 0 incidencias con el
   corte de construcción. Regla en `CUTOFF_ASOF_REGLA_CAUSAL.md` y en la
   docstring de `ict3_contract.validate`. Sin cambio de comportamiento.
3. **Interfaz:** harness aislado en navegador; 3 activos × 7 expedientes ×
   8 etapas (56 nodos por activo) con estado, hora y motivo. El único
   `POST /api/sync` fue interceptado localmente; cero POST reales y cero
   escrituras propias en `data/`.
4. **Release:** `RELEASE_FASE_08.md` §8 y este plan actualizados. La Fase 8
   continúa en `[~]` mientras el punto 1 no tenga evidencia.

Siguiente hito: una cotización autorizada fresca de MT5 para repetir EURUSD,
GBPJPY y US30 con cierre M15, último tick, `schema_version`, `mode` y
`entry_authorized=false`; solo entonces se podrá proponer `[x]`.
