# Lote Hermes 03 — confirmación M5/M1 y stop estructural

**Estado:** autorizado después de aceptar C4–C7.  
**Alcance:** extender la evidencia de `RETESTING_POI` hacia una observación M5/M1; no crear órdenes.  
**Autoridad:** ICT 2.0 `f453bf2`; ICT 3.0 continúa como investigación.

## Reglas de seguridad

- Solo velas cerradas y `as_of(cutoff)`.
- No leer M5/M1 para eventos que no estén en `RETESTING_POI`.
- No crear campos `entry`, `fill`, `order`, `volume`, `lots` ni llamadas de trading.
- `entry_authorized` permanece siempre `false` y `mode` sigue `OBSERVE_ONLY_NO_ORDER`.
- No introducir OTE/Fibonacci ni usar ATR como sustituto de estructura.
- No tocar credenciales, operaciones, tickets o `data/`.

## Tarea 1 — carga causal bajo demanda

- Ampliar la lectura histórica para incluir M5 y M1 solo cuando el evento tenga retest M15 observado.
- Truncar ambos marcos a velas con cierre `<= cutoff`.
- Registrar `m5_loaded`, `m1_loaded`, último cierre usado y cobertura; si no hay historial suficiente, conservar un motivo explícito.
- Probar que un evento `ACCEPTED_BREAK_WAIT_RETEST` sin POI o sin retest no carga M5/M1.
- Probar invariancia por prefijos.

## Tarea 2 — confirmación estructural

Implementar un observador descriptivo, no una entrada:

1. defensa del POI o del nivel roto al cierre;
2. BOS/CHOCH/MSS confirmado en M5 en dirección de la ruptura;
3. M1 opcional como confirmación de detalle, nunca como sustituto de M5;
4. si falta cualquier evidencia, estado `WAIT_M5_M1_CONFIRMATION`.

Registrar por separado:

```text
confirmation_state,
defense_at,
m5_structure_kind,
m5_structure_at,
m1_structure_kind,
m1_structure_at,
pending_evidence,
reason
```

No convertir un cierre aislado, una mecha o una etiqueta del futuro en estructura confirmada.

## Tarea 3 — stop estructural informativo

Aplicar este orden de autoridad únicamente después del retest:

1. swing de origen del impulso intacto;
2. extremo estructural de reacción/retest M5;
3. extremo estructural confirmado M1;
4. si ninguno existe, `NO_STRUCTURAL_STOP`.

El payload puede incluir `stop_basis`, `stop_price` y `stop_observed_at` solo como evidencia informativa; no debe incluir lotaje ni riesgo monetario. ATR, si aparece, solo puede ser margen sobre una estructura ya encontrada.

## Tarea 4 — estados y contrato

Añadir al bloque versionado `ict3`:

- `WAIT_M5_M1_CONFIRMATION`;
- `OBSERVABLE_SETUP` solo cuando retest, defensa, estructura M5, stop estructural y objetivo causal estén completos;
- `NO_STRUCTURAL_STOP` como motivo pendiente, no como ruptura inválida.

`OBSERVABLE_SETUP` no autoriza una operación. Mantener `entry_authorized=false`.

Los objetivos solo pueden usar liquidez conocida al corte. Si la política de planificación exige TP1 ≥3R y TP2 ≥5R, registrar `target_policy_status` como observación y dejar pendiente el setup cuando la estructura no lo permite. No fabricar niveles ni afirmar rentabilidad.

## Pruebas mínimas

- carga bajo demanda M5/M1;
- no carga en eventos sin retest;
- defensa válida e inválida;
- BOS/CHOCH M5 confirmado y no confirmado;
- M1 sin M5 no basta;
- stop por cada una de las tres bases y ausencia de stop;
- no usar velas futuras;
- `OBSERVABLE_SETUP` nunca cambia `entry_authorized`;
- contrato HTTP conserva `schema_version`, cabeceras y rutas sin trading;
- suite completa y prueba real en EURUSD, GBPJPY y US30 o error explícito.

## Entrega

Entregar un informe único con archivos, funciones, decisiones causales, suite completa, ejemplos de estados, cobertura por símbolo y confirmación de solo lectura. No modificar todavía la interfaz ni la simulación de rentabilidad.
