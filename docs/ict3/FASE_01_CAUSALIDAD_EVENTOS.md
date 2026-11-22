# Fase 1 — Causalidad e identidad de eventos

## Orden de trabajo para los agentes

**Mandato.** Conserva la fase aceptada como base de regresión. Reabre únicamente ante un fallo reproducible.

1. **Agente de dominio · `ict.py`.** Traza de dónde salen símbolo, sesión, nivel, dirección y vela de señal. Verifica que un candidato ya observado conserve su ID cuando se acepta o falla. Comprueba que un candidato abierto carezca de una hora de fallo inventada.
2. **Agente de pruebas · `test_ict.py`.** Construye una secuencia que termine justo antes de la señal, en el primer cierre fuera y en cada desenlace. Repite con PDH y PDL y con dos símbolos. Compara el corte de la serie completa con el prefijo disponible.
3. **Entregable de Hermes.** Matriz de identidad y tiempos por transición, con un evento que evoluciona y un par que deba distinguirse. Aceptación: mismo evento conserva ID y hora de observación, los eventos distintos se distinguen y la salida anterior sigue disponible.

## Objetivo
Eventos de ruptura reproducibles, identificables y auditables sin información posterior al corte.

## Trabajo
- Revisar `daily_break_studies()` y sus llamadas.
- Generar `event_id` determinista por símbolo, sesión, nivel, dirección y vela.
- Conservar `observed_at`, `state_time`, `signal_open` y `signal_close`.
- Probar replay por prefijos: `prefix_to_t == full_series_at_t`.
- Mantener PDH y PDL como identidades distintas.

## Delegación y aceptación
Delegar identidad/hash, replay temporal y contrato/payload en agentes separados. La suite debe estar verde, los identificadores ser estables y no deben aparecer datos futuros, órdenes ni riesgo monetario.
