# Índice del plan continuo de Hermes — ICT 3.0

Hermes debe avanzar por estas fases, delegando los subpuntos independientes en agentes especializados cuando estén disponibles. Cada agente entrega archivos, pruebas, supuestos, riesgos y evidencia de solo lectura; Hermes integra y entrega un informe único.

Antes de cada fase: `POST http://127.0.0.1:8765/api/bridge/work` con `{"active":true,"task":"FASE N"}`. Mientras esté activo no debe consultar `/api/inbox` ni buscar mensajes. El puente usa `fs.watch` + debounce, `/api/events` (SSE) y `EventSource('/api/events')`. Al terminar debe responder `terminé el trabajo` y cerrar con `{"active":false,"task":""}`.

## Mandato para Hermes

Empieza en la fase activa que figura en el [plan principal](PLAN_HERMES_REVISION_IA.md). Trata las fases aceptadas como base de regresión. Avanza con los encargos independientes mientras GPT revisa la entrega anterior. Si una corrección cambia el contrato o la evidencia de la que depende otro encargo, resuélvela primero y continúa con lo que se pueda verificar por separado.

1. **Asigna responsables.** Para cada encargo indica agente, archivos que puede editar, insumos, resultado esperado y prueba de aceptación. Cuando dos encargos comparten un archivo, designa un propietario de escritura y deja al otro agente la revisión o las pruebas en archivos separados. Si faltan agentes, ejecuta los encargos en el mismo orden y registra quién los asumió.
2. **Integra con evidencia.** Cada agente devuelve archivos y funciones, casos probados, comando y resultado, supuestos y bloqueos. Hermes revisa las diferencias, resuelve solapamientos y corre la suite completa del proyecto con `.venv\Scripts\python.exe -m unittest discover -v`. Consulta `AGENTS.md` y actualiza Graphify si corresponde.
3. **Entrega por fase.** Incluye estado, revisión probada, responsables, resultado de la suite, ejemplos con corte temporal y pendientes con su dependencia concreta. Usa «terminé el trabajo» al entregar una fase para revisión de GPT. Mantén el registro de aceptación en el plan principal.
4. **Escala decisiones de alcance.** Rubén decide cambios de objetivos o reglas de mercado. Hermes decide la implementación dentro del alcance y GPT valida la entrega. Los agentes trabajan con datos autorizados y mantienen el sistema en modo de observación.

## Secuencia

1. [ ] [Fase 1 — Causalidad y eventos](FASE_01_CAUSALIDAD_EVENTOS.md)
2. [ ] [Fase 2 — Asociación FVG/OB](FASE_02_ASOCIACION_POI.md)
3. [ ] [Fase 3 — Máquina de estados M15](FASE_03_ESTADOS_M15.md)
4. [ ] [Fase 4 — Confirmación M5/M1](FASE_04_CONFIRMACION_M5_M1.md)
5. [ ] [Fase 5 — Contrato HTTP](FASE_05_CONTRATO_SERVIDOR.md)
6. [ ] [Fase 6 — Interfaz explicable](FASE_06_INTERFAZ_ANALISIS.md)
7. [ ] [Fase 7 — Simulación fuera de muestra](FASE_07_VALIDACION_OOS.md)
8. [ ] [Fase 8 — Integración y operación](FASE_08_INTEGRACION_OPERACION.md)

El estado aceptado o pendiente se mantiene en `PLAN_HERMES_REVISION_IA.md`.
