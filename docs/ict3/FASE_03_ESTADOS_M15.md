# Fase 3 — Máquina de estados M15

## Orden de trabajo para los agentes

**Mandato.** Mantén el historial de cada ruptura como una secuencia cronológica auditable.

1. **Agente de estados · `ict3_link.py`.** Documenta qué cierre dispara cada transición y la precedencia cuando una vela pierde el nivel diario y atraviesa el POI. Registra por separado toque de borde, cruce estructural y gap sin contacto.
2. **Agente de pruebas · `test_ict3_link.py`.** Ejecuta la matriz alcista y bajista en ventanas de 4, 8, 16 y 32 velas. Incluye retest dentro de una ventana seguido de invalidación fuera de ella, ventana incompleta y toque después de la expansión terminal.
3. **Entregable de Hermes.** Tabla de entradas, estados, horas y motivos. Aceptación: ninguna ventana usa transiciones posteriores a su cierre, cada transición aparece una vez y la expansión conserva su estado ante un toque tardío.

## Objetivo
Representar retorno al POI, pérdida de aceptación e invalidez sin convertir hipótesis en entrada.

## Trabajo
- Definir `RETESTING_POI`, `ACCEPTANCE_LOST`, `POI_INVALID` y `EXPANSION_NO_ENTRY`.
- Guardar historial con hora, estado anterior, nuevo estado y motivo.
- Usar ventanas comparables y cerrar expansión en el horizonte exacto.
- Evitar duplicados y probar replay por prefijos, dirección y gaps.

## Delegación y aceptación
Delegar autómata/precedencia, ventanas y regresiones alcistas-bajistas. Cada estado debe ser reproducible con velas cerradas; un estado terminal no se reabre por datos tardíos.
