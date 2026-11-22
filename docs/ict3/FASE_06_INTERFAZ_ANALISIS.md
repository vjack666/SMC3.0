# Fase 6 — Interfaz de análisis explicable

## Orden de trabajo para los agentes

**Mandato.** Permite al usuario entender el recorrido de un evento desde la ruptura hasta su estado actual.

1. **Agente de presentación.** Organiza la ficha de arriba abajo: ruptura, zona, retest, defensa M5, corroboración M1, invalidación y objetivos observados. Para cada etapa muestra estado, hora cuando exista y motivo en español. Conserva la navegación y la selección de activo.
2. **Agente de calidad.** Prueba evento sin zona, zona sin retest, espera de M5, M1 ausente, POI invalidado y setup observable. Verifica cambio de activo durante una carga, datos ausentes, vista estrecha y navegación por teclado. Aporta capturas de espera y de evidencia completa con datos de prueba.
3. **Entregable de Hermes.** Mapa campo → texto visible y recorrido verificado. Aceptación: la ficha deja claro qué falta y a qué activo pertenece. El SSE de mensajería corresponde al puente de Hermes. Para el panel ICT conserva su mecanismo de actualización existente y evita añadir consultas periódicas.

## Objetivo
Mostrar qué evidencia existe, qué falta y por qué el motor espera.

## Trabajo
- Renderizar estado, hora y motivo de transición.
- Separar contexto HTF, ruptura, POI, retest, M5, M1, stop, objetivos e invalidez.
- Mostrar esperas y errores sin inventar datos.
- Etiquetar observado, hipótesis y simulación.
- Conservar el mecanismo de actualización del panel. El SSE del puente de mensajería se mantiene separado.

## Delegación y aceptación
Delegar contrato UI, estados vacíos y accesibilidad/regresión visual. La interfaz debe ser explicable y nunca presentar una zona candidata como entrada confirmada.
