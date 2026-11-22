# Fase 8 — Integración y operación del servidor

## Orden de trabajo para los agentes

**Mandato.** Demuestra que la versión integrada funciona en la ruta habitual de SMC 3.0 y deja una reversión practicable.

1. **Agente de preparación.** Registra revisión actual, cómo se inicia y qué cambios se activarán. Guarda resultados previos de los endpoints de lectura. Documenta la forma de restaurar la versión anterior preservando cambios ajenos.
2. **Agente de verificación.** Ejecuta la suite completa. Tras el arranque autorizado mediante `abrir-smc.cmd`, compara código HTTP, versión, modo y respuesta de `/api/market`, `/api/market-universe` y `/api/ict`. Revisa la interfaz y registra cobertura real por activo. Si MT5 está inaccesible, conserva las pruebas locales y deja la comprobación en vivo pendiente.
3. **Entregable de Hermes.** Registro de release con revisión, hora, comandos, pruebas, cobertura y pasos de reversión. Aceptación: servicio e interfaz responden en la versión prevista, el contrato permanece compatible y las comprobaciones confirman el modo de solo lectura.

## Objetivo
Confirmar funcionamiento vivo en modo estrictamente observacional.

## Trabajo
- Ejecutar suite y prueba temporal con MT5 accesible.
- Verificar 26 pares, cuatro índices y DXY solo como referencia manual.
- Comprobar `/api/market`, `/api/market-universe`, `/api/ict` e interfaz.
- Reiniciar únicamente mediante `abrir-smc.cmd`.
- Documentar reversión segura y confirmar cero operaciones enviadas o modificadas.

## Delegación y aceptación
Delegar smoke tests, cobertura de instrumentos, despliegue/reversión y auditoría final. Contrato compatible, suite aprobada, servidor confirmado e interfaz cargando sin operar cuentas.
