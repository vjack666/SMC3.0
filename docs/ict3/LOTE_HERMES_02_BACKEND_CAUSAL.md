# Lote Hermes 02 — correcciones y backend causal ICT 3.0

**Estado de la revisión de GPT:** Tarea 1 no aceptada todavía.  
**Alcance del lote:** corregir el contrato temporal, asociar POI M15, completar los estados M15 y publicar un bloque API versionado.  
**Prohibido:** interfaz, confirmación M5/M1, órdenes, lotaje, fills, P&L, credenciales o cambios en `data/`.

## Hallazgos obligatorios de la revisión

### C1 — Candidato final marcado como fallo sin evidencia

En `daily_break_studies()`, el bloque final usa:

```python
candidate["state"] = "BREAK_CANDIDATE" if session_end > cutoff else "FAILED_BREAK"
candidate["state_time"] = int(session[-1].closed)
```

Pero `session_end` se calcula con `min(next_open, cutoff)` o con `cutoff`, por lo que no puede ser mayor que `cutoff`. Una primera ruptura situada en la última M15 disponible queda etiquetada inmediatamente como `FAILED_BREAK`, aunque ninguna vela haya cerrado de vuelta dentro.

Corrección requerida:

- `FAILED_BREAK` solo existe cuando una M15 posterior cierra dentro antes de la aceptación.
- Un candidato sin segunda vela suficiente permanece `BREAK_CANDIDATE`.
- Para el candidato abierto, `state_time` permanece en `signal_close`; no se mueve en cada replay si el estado no cambió.
- No crear todavía un estado de expiración por fin de sesión. Si después se necesita, se definirá explícitamente y no se llamará `FAILED_BREAK`.

Pruebas mínimas:

1. primer cierre fuera en la última vela → `BREAK_CANDIDATE`;
2. mismo prefijo más otra vela fuera → `ACCEPTED_BREAK_WAIT_RETEST`;
3. mismo prefijo más una vela dentro → `FAILED_BREAK` con `failure_time == state_time`;
4. añadir futuro que no cambia el estado conserva `event_id`, `observed_at` y `state_time`;
5. ningún `FAILED_BREAK` puede carecer de `failure_time`.

### C2 — La simulación pierde la identidad del símbolo

`ict3_simulation.py` llama:

```python
daily_break_studies(d1, m15, cutoff, digits=info.digits)
```

Como no pasa `symbol`, todos los `event_id` de la simulación se construyen con el valor por defecto `EURUSD`.

Corrección requerida:

- pasar `symbol=symbol` desde `simulate_symbol()`;
- revisar todas las llamadas con `rg` y documentar que no queda ninguna ruta multiactivo usando el valor por defecto por accidente;
- añadir una prueba del camino de simulación o extraer una función pequeña que permita verificar que dos símbolos producen ids distintos con los mismos precios y tiempos.

### C3 — La prueba de replay no cubre las transiciones

La prueba actual compara únicamente un evento que ya está aceptado en ambos prefijos. No detecta el error candidato → fallo prematuro.

Corrección requerida:

- construir una matriz de prefijos para `BREAK_CANDIDATE`, `ACCEPTED_BREAK_WAIT_RETEST` y `FAILED_BREAK`;
- comprobar campos inmutables por `event_id` y campos que cambian solo al producirse una transición real;
- mantener las 33 pruebas actuales y añadir las nuevas.

## Tarea 2 — Asociación causal con FVG/OB M15

Después de corregir C1–C3, implementar la asociación de cada ruptura aceptada con zonas canónicas del motor ICT 2.0.

### Reglas

- Usar únicamente los objetos M15 ya producidos por `build_ltf_canonical_feed` de la revisión fijada `f453bf2`.
- Misma dirección que la ruptura.
- La zona no puede aparecer antes de su `confirmation_time`.
- Su impulso debe pertenecer causalmente a la secuencia de ruptura; definir y documentar la ventana temporal exacta. No elegir simplemente la zona más cercana por precio.
- Una zona tocada antes de estar confirmada no cuenta como retest.
- Conservar todas las candidatas válidas en `poi_candidates`; la selección de una zona primaria debe tener `selection_reason` explícita.
- Estados intermedios del enlace: `accepted_without_poi` y `accepted_with_poi` como campos descriptivos, sin reemplazar todavía el estado principal.
- No inventar stop, entrada u objetivo.

### Payload mínimo de cada POI

```text
zone_id, kind, direction, low, high, confirmed_at,
first_touch_at, association_reason, rejected_reason
```

### Pruebas mínimas

- FVG válido de la misma dirección;
- OB válido de la misma dirección;
- zona opuesta rechazada;
- zona confirmada antes de la señal rechazada si no pertenece al impulso;
- zona confirmada después del corte invisible;
- primer toque anterior a confirmación no tratado como retest;
- replay por prefijos conserva el enlace cuando no cambia la evidencia.

## Tarea 3 — Máquina de estados M15

Sobre el enlace de la Tarea 2, implementar transiciones causales:

```text
ACCEPTED_BREAK_WAIT_RETEST
→ RETESTING_POI
→ ACCEPTANCE_LOST
→ POI_INVALID
→ EXPANSION_NO_ENTRY
```

### Reglas

- `RETESTING_POI`: primer contacto posterior a la confirmación de la zona.
- `ACCEPTANCE_LOST`: cierre M15 de vuelta dentro de PDH/PDL después de aceptación y antes de un retest válido.
- `POI_INVALID`: cierre que atraviesa el límite estructural de la zona en contra de la dirección.
- `EXPANSION_NO_ENTRY`: no hubo retest dentro de una ventana de observación configurable. Implementar primero ventanas de 4, 8, 16 y 32 M15 como resultados comparables; no escoger una regla normativa sin validación.
- Un evento conserva la ruptura original y un `transition_history` ordenado con `from`, `to`, `at` y `reason`.
- Una transición solo puede usar velas cerradas en el corte.
- No implementar `OBSERVABLE_SETUP` en este lote; eso requiere M5/M1 y será otro lote.

### Pruebas mínimas

- aceptación sin zona;
- aceptación con zona sin toque;
- toque exacto al borde;
- gap que atraviesa una zona;
- pérdida de aceptación antes del retest;
- invalidación de POI después del toque;
- expansión sin retorno para las cuatro ventanas;
- ausencia de duplicados por permanencia fuera del nivel;
- invariancia `prefix_to_t == full_series_at_t` para cada transición.

## Tarea 4 — Contrato versionado del servidor

Publicar el resultado de las tareas anteriores en un bloque nuevo y compatible:

```json
{
  "ict3": {
    "schema_version": "0.2-research",
    "mode": "OBSERVE_ONLY_NO_ORDER",
    "events": []
  }
}
```

### Reglas

- Mantener temporalmente `ict3_breaks` sin eliminar ni renombrar sus campos.
- Cada evento nuevo incluye identidad, tiempos, vector de fuerza, POI asociados, estado actual, historial de transiciones, evidencias pendientes y motivo de espera.
- `entry_authorized` debe ser siempre `false` dentro del bloque ICT 3.0.
- Mantener `127.0.0.1`, validación de `Host`/`Origin`, `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`.
- No añadir rutas POST, endpoints de trading ni acciones de cuenta.
- Añadir pruebas de contrato para payload mínimo, `schema_version`, compatibilidad de `ict3_breaks`, corte inválido y ausencia de campos de orden.

## Orden de trabajo del lote

1. C1–C3 y suite completa.
2. Tarea 2 y sus pruebas.
3. Tarea 3 y sus pruebas.
4. Tarea 4 y pruebas de contrato.
5. Ejecutar suite completa y probar `/api/ict` con al menos EURUSD, GBPJPY y US30 si MT5 está disponible.
6. No reiniciar el servidor habitual hasta que todo el lote pase; usar únicamente `abrir-smc.cmd` para un reinicio autorizado y nunca eludir bloqueos del sistema.

## Entrega única del lote

Hermes debe entregar:

- resumen por corrección y tarea;
- lista de archivos y funciones modificados;
- decisiones causales y ventanas usadas;
- suite completa con conteo;
- ejemplos de candidato, aceptación, retest, pérdida e invalidez;
- payload anterior y nuevo de `/api/ict`;
- resultado por EURUSD, GBPJPY y US30 o error explícito de MT5;
- riesgos pendientes;
- confirmación de que no añadió ni ejecutó órdenes y no tocó credenciales ni datos privados.

No implementar M5/M1, interfaz ni simulación de rentabilidad en este lote.
