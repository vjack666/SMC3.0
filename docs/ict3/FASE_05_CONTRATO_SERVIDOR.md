# Fase 5 — Contrato del servidor local

## Orden de trabajo para los agentes

**Mandato.** Cierra el contrato del bloque existente antes de usarlo como base de interfaz.

1. **Agente de contrato.** Redacta un diccionario de campos de `ict3`, eventos, transiciones y `load`. Para cada campo registra tipo, unidad, nulabilidad, procedencia y significado. Indica qué se conserva en `ict3_breaks` y qué casos representan espera legítima.
2. **Agente de HTTP.** Valida respuestas de lectura en servidor local y casos de corte o parámetros inválidos conforme al contrato existente. Comprueba cabeceras, validaciones vigentes y ausencia de rutas de órdenes mediante pruebas de contrato ordinarias. Separa resultados simulados de verificaciones con MT5.
3. **Entregable de Hermes.** Diccionario, ejemplos JSON y pruebas de compatibilidad. Aceptación: los consumidores existentes siguen leyendo el formato previo, y un consumidor nuevo puede distinguir sin adivinar entre sin retest, datos ausentes y evidencia insuficiente.

## Objetivo
Exponer el expediente ICT 3.0 con versionado y compatibilidad.

## Trabajo
- Mantener `/api/ict` y añadir `ict3` versionado.
- Documentar estados, POI, carga M5/M1, cobertura y pendientes.
- Conservar validaciones de símbolo, marco, corte, `127.0.0.1`, Host, Origin, `no-store` y `nosniff`.
- No crear rutas de órdenes, cuenta o posiciones.
- Probar respuestas válidas, cortes inválidos, host prohibido y rutas de trading inexistentes.

## Delegación y aceptación
Delegar esquema/compatibilidad, HTTP y superficie de ataque. Clientes antiguos deben seguir funcionando y el servidor debe permanecer de solo lectura.
