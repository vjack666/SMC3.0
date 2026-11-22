# Plan de trabajo ICT 3.0

## Objetivo

Extender ICT 2.0 sin romper su autoridad: mejorar la lectura de rupturas de
PDH/PDL, conservar evidencia causal, separar contexto de setup y permitir que
la IA explique por qué una ruptura fue aceptada, falló o continuó sin entrada.

## Reglas heredadas de ICT 2.0

Se mantienen como contrato:

- D1/H4/H1 aportan contexto; M15/M5/M1 confirman.
- Sweep: rompe el nivel y cierra de vuelta dentro en la misma vela.
- Displacement: cuerpo dominante y desplazamiento observable.
- BOS/CHOCH/MSS requieren estructura cerrada y confirmada.
- El POI es FVG/OB canónico creado por el desplazamiento.
- La entrada solo ocurre en retorno al POI, nunca persiguiendo el BOS.
- El stop es estructural; ATR solo aporta margen a una estructura existente.
- Sin retorno, no hay entrada.
- Todo análisis usa `as_of(t)` y no mira velas futuras.

## Fases

### Fase 0 — Baseline y trazabilidad

- Congelar la revisión ICT 2.0 `f453bf2`.
- Registrar limitaciones del motor actual y del feed MT5.
- Conservar el expediente EURAUD como caso de referencia.

### Fase 1 — Detector ICT 3.0 de ruptura diaria

- Detectar el primer cruce de PDH/PDL por cierre.
- Separar `BREAK_CANDIDATE`, `SWEEP`, `FAILED_BREAK` y aceptación por dos cierres.
- Calcular fuerza como vector explicable, no como score opaco:
  `body_ratio`, `body_multiple`, `close_extension`, `close_location`.
- No descartar la ruptura porque aún no exista stop.

### Fase 2 — Máquina de estados de continuación

Estados objetivo:

```text
INSIDE_RANGE
→ BREAK_CANDIDATE
→ ACCEPTED_BREAK_WAIT_RETEST
→ RETESTING_POI
→ OBSERVABLE_SETUP
→ EXPANSION_NO_ENTRY / INVALIDATED
```

- Correlacionar con FVG/OB canónico.
- Bajar la confirmación de entrada a M5/M1.
- Registrar el motivo exacto de cada espera o descarte.

### Fase 3 — Simulación causal de observación

- Pedir al terminal el máximo de historial que devuelva MT5.
- Ejecutar la lectura en los 26 pares confirmados.
- No calcular P&L, fills, lotaje ni órdenes.
- Comparar el etiquetado actual con ICT 3.0 propuesto.
- Separar resultados por símbolo, sesión, PDH/PDL y alineación D1/H4/H1.

### Fase 4 — Auditoría de mediocridades

Buscar:

- duplicación de BOS o rupturas;
- confusión entre mecha y cierre;
- entradas sin retest;
- stops inventados o no estructurales;
- targets que usan futuro;
- uso indebido de tick volume;
- umbrales únicos para símbolos con microestructura distinta;
- estados que ocultan información causal bajo `discarded`.

### Fase 5 — Validación fuera de muestra

- Separar calibración y evaluación.
- Verificar invariancia PIT: el resultado al corte no cambia al añadir futuro.
- Solo después proponer cambios normativos a la tesis.

## Criterios de aceptación

- Cero órdenes enviadas.
- Cero datos futuros en la simulación.
- 26/26 pares procesados o error explícito por símbolo.
- Cada evento conserva nivel, hora, fuerza, estado y motivo.
- El motor distingue “ruptura correcta sin entrada” de “ruptura inválida”.
- Tests unitarios y de contrato pasan.

## Entregables

1. Detector y payload ICT 3.0 en `ict.py`.
2. Simulación en `ict3_simulation.py`.
3. Informe generado en `docs/research/ICT3_SIMULACION_26_PARES.md`.
4. Expediente EURAUD en `docs/ict3/01_RUPTURA_FUERTE_LIQUIDEZ_DIARIA.md`.
5. Este plan como control de alcance.

