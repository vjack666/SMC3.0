# Fase 2 — Asociación causal de FVG/OB

## Orden de trabajo para los agentes

**Mandato.** Conserva las zonas del motor fijado y haz auditable la decisión de asociación.

1. **Agente de motor · `ict3_link.py`.** Identifica la vela del impulso y su relación con la señal y la aceptación. Contrasta dirección, intervalo del impulso y hora de confirmación de cada zona. Si hay varias candidatas, documenta el orden de precedencia existente y cómo resuelve un empate.
2. **Agente de pruebas · `test_ict3_link.py`.** Cubre FVG válido, OB válido, zona opuesta, zona fuera del impulso, confirmación posterior al corte y toque anterior a la confirmación. Verifica el instante exacto en que una zona se hace visible.
3. **Entregable de Hermes.** Ejemplos de ruptura con y sin POI, con ID, límites, evidencia temporal y motivo. Aceptación: el primer toque cuenta solo si la zona ya era conocida y repetir un corte produce la misma selección.

## Objetivo
Enlazar una ruptura aceptada con el POI canónico del impulso y explicar cada aceptación o rechazo.

## Trabajo
- Usar únicamente objetos FVG/OB de ICT 2.0.
- Exigir misma dirección, confirmación posterior a la señal y disponibilidad al corte.
- Registrar límites, tipo, identificador, confirmación, primer toque y razón.
- Rechazar zonas opuestas, anteriores o confirmadas después del corte.
- No seleccionar por cercanía ni promover a entrada.

## Delegación y aceptación
Delegar extracción, asociación temporal/direccional y pruebas negativas. El payload debe distinguir `accepted_without_poi` de `accepted_with_poi` y seguir en observación.
