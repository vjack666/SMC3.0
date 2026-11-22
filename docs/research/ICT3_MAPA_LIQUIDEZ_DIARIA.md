# ICT 3.0 — Mapa de liquidez del día anterior

## Propósito

Usar el máximo y mínimo de la D1 anterior como un mapa diario por símbolo. El
mapa responde primero **qué hizo el precio con PDH/PDL** y solo después pregunta
si existe una lectura de entrada.

## Clasificación causal

```text
PDH/PDL conocido
    ├─ mecha fuera + cierre dentro → SWEEP / toma de liquidez
    ├─ primer cierre fuera → BREAK_CANDIDATE
    │    ├─ vuelve dentro → FAILED_BREAK
    │    └─ segundo cierre fuera → ACCEPTED_BREAK_WAIT_RETEST
    │         ├─ vuelve a FVG/OB → RETESTING_POI
    │         ├─ confirma M5/M1 + stop → OBSERVABLE_SETUP
    │         └─ sigue sin volver → EXPANSION_NO_ENTRY
```

## Campos mínimos del mapa

- símbolo;
- fecha de la jornada y fecha de la D1 fuente;
- PDH y PDL con precisión MT5;
- nivel atacado y dirección;
- primer cruce, cierre de aceptación o fallo;
- `body_ratio`, `body_multiple`, `close_extension`, `close_location`;
- estado causal;
- contexto D1/H4/H1/M15;
- POI FVG/OB, si existe;
- retest y stop estructural, solo si aparecen después del corte.

## Resultado observado en la primera simulación

La simulación de observación de los 26 pares, con 5.000 velas M15 por símbolo y
entre 751 y 2.000 D1 devueltas por MT5, registró:

- 1.101 `ACCEPTED_BREAK_WAIT_RETEST`;
- 1.247 `FAILED_BREAK`;
- 0 operaciones, fills o cálculos de P&L.

Estos conteos no son una tasa de acierto. Sirven para entrenar la representación
del motor y descubrir dónde la lógica de ICT mezcla toma de liquidez,
rompimiento y entrada.

## Regla aprendida

Un sweep y un rompimiento no son dos nombres para el mismo evento:

- **Sweep:** el mercado toma liquidez y vuelve a cerrar dentro.
- **Rompimiento aceptado:** el mercado cierra fuera dos veces consecutivas.
- **Entrada:** solo después de un retorno a FVG/OB, confirmación fina y stop
  estructural.

Una ruptura aceptada que nunca retorna queda como `EXPANSION_NO_ENTRY`. No debe
marcarse como setup perdido ni perseguirse.

## Caso EURAUD

El 20 de noviembre de 2026, EURAUD rompió PDH `1.64832` con una vela M15 cuyo
cuerpo fue `88%` del rango, `2.60×` el rango medio y cerró `1.36` rangos por
encima del nivel. Dos cierres posteriores aceptaron la ruptura. Se formaron un
OB `1.64639–1.64926` y un FVG `1.64926–1.65021`, pero el precio nunca retornó a
esas zonas. La etiqueta correcta es **ruptura aceptada + expansión sin entrada**.

## Fallas que el mapa evita

1. contar cada vela que permanece fuera como una nueva ruptura;
2. llamar sweep a una vela que cierra fuera;
3. descartar una ruptura válida porque todavía no tiene stop;
4. usar el máximo final del día como target conocido retrospectivamente;
5. convertir tick volume de MT5 en volumen institucional;
6. presentar una zona candidata como entrada confirmada.

## Uso futuro

El mapa será la capa previa al análisis ICT 3.0. Cada expediente de POI debe
referenciar el evento del mapa que lo precedió: `SWEEP`, `FAILED_BREAK` o
`ACCEPTED_BREAK_WAIT_RETEST`. La promoción a `OBSERVABLE_SETUP` exige una
secuencia posterior causal y no puede inferirse solo del mapa.

