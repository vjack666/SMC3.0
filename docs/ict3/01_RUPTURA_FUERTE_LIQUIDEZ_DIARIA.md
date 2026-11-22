# ICT 3.0 — Ruptura fuerte de liquidez diaria

**Estado:** borrador de investigación; no es una regla activa ni autoriza órdenes.  
**Caso inicial:** EURAUD, 20 de noviembre de 2026, reloj MT5.  
**Fuente de datos:** velas cerradas de la cuenta MT5 configurada en SMC 3.0.  
**Autoridad heredada:** ICT 2.0, revisión `f453bf2`.

## 1. Problema

ICT 2.0 separa correctamente un barrido de una ruptura al cierre, pero el
observador del Libro 22 descarta una continuación inmediatamente cuando no
encuentra un swing M15 previo apto para anclar el stop. El caso EURAUD muestra
que eso mezcla dos decisiones distintas:

1. si la ruptura de PDH/PDL fue aceptada por el mercado;
2. si después apareció una entrada con retorno, confirmación y stop estructural.

Una ruptura puede ser válida como lectura y aun así no ofrecer entrada. ICT 3.0
debe conservar ambos hechos por separado.

## 2. Evidencia causal del caso EURAUD

Nivel conocido antes del evento:

- PDH: `1.64832` (D1 del 19 de noviembre);
- ruptura alcista inicial: vela M15 abierta a las `17:00`;
- confirmación por dos cierres consecutivos fuera: al cierre de la M15 de
  `17:15`, conocido a las `17:30`.

Geometría de la vela de ruptura de las 17:00:

| Medida | Resultado |
|---|---:|
| Apertura | 1.64651 |
| Máximo | 1.65040 |
| Mínimo | 1.64605 |
| Cierre | 1.65032 |
| Cuerpo / rango medio previo | 2.60 |
| Cuerpo / rango de la vela | 88% |
| Cierre fuera de PDH / rango medio | 1.36 |

Los dos cierres siguientes fueron `1.65027` y `1.65155`, ambos por encima de
PDH. La ruptura produjo zonas canónicas alcistas:

- OB M15: `1.64639–1.64926`, confirmado a las 17:15;
- FVG M15: `1.64926–1.65021`, confirmado a las 17:30.

El precio no volvió a esas zonas después de la confirmación. El mínimo
posterior inmediato fue `1.65029`, ocho puntos de precio por encima del borde
superior del FVG. Por tanto, el resultado causal es:

> ruptura fuerte aceptada; expansión observada; no hubo retorno a POI y no
> existió entrada conforme a la tesis.

El resultado actual del Libro 22 fue `discarded/no_stop_structure`. Esa etiqueta
describe la ausencia de stop en el instante de confirmación, pero pierde la
información de que la ruptura sí fue fuerte y aceptada.

## 3. Definiciones propuestas

Sea `L` el PDH o PDL conocido antes del evento y `d` la dirección de ruptura.
Todas las medidas usan solo velas cerradas disponibles en el instante de
decisión.

### 3.1 Ruptura candidata

Primera M15 cuyo cierre cruza `L` desde dentro hacia fuera. Una vela que solo
perfora con mecha y cierra dentro sigue siendo `SWEEP`, no ruptura.

### 3.2 Vector de fuerza

Registrar sin reducir prematuramente a un único score:

- `body_ratio = abs(close-open)/(high-low)`;
- `body_multiple = abs(close-open)/mean(high-low, 14 velas previas)`;
- `close_extension = d*(close-L)/mean(high-low, 14 velas previas)`;
- `close_location`: cierre dentro del cuarto exterior de la vela en dirección
  de la ruptura;
- `gap_or_zone`: FVG/OB canónico dejado por el impulso.

Hipótesis inicial para una ruptura fuerte:

```text
body_ratio >= 0.70
AND body_multiple >= 1.50
AND close_extension >= 0.50
```

Los umbrales son candidatos de ingeniería y requieren calibración. No deben
promoverse a contrato de tesis por este único ejemplo.

### 3.3 Aceptación

La ruptura pasa a `ACCEPTED_BREAK` cuando existen dos cierres M15 consecutivos
fuera de `L` en la misma dirección. La aceptación solo existe al cierre de la
segunda vela; no se reescribe retrospectivamente la primera.

Antes de esa confirmación:

- cierre de vuelta dentro → `FAILED_BREAK`;
- mecha fuera y cuerpo dentro → `SWEEP`;
- segundo cierre fuera → `ACCEPTED_BREAK`.

## 4. Máquina de estados propuesta

```text
INSIDE_RANGE
  → BREAK_CANDIDATE
  → ACCEPTED_BREAK_WAIT_RETEST
      → RETESTING_POI
          → OBSERVABLE_SETUP
          → INVALIDATED
      → EXPANSION_NO_ENTRY
  → FAILED_BREAK / SWEEP
```

### `ACCEPTED_BREAK_WAIT_RETEST`

Es una lectura de continuación, no una entrada. Debe conservar:

- PDH/PDL roto;
- vela de impulso y vector de fuerza;
- cierres de aceptación;
- alineación D1/H4/H1/M15;
- FVG/OB creados;
- liquidez conocida al corte.

### `RETESTING_POI`

Solo comienza después de que exista un FVG/OB canónico confirmado y el precio
regrese a la zona. Tocar el nivel roto sin tocar el POI no basta por sí solo.

### `OBSERVABLE_SETUP`

Requiere, además del retest:

1. defensa del nivel roto o del POI al cierre;
2. confirmación estructural M5 o M1 en la dirección de ruptura;
3. stop estructural disponible;
4. objetivo de liquidez conocido en ese instante;
5. relación riesgo/objetivo conforme a la política vigente.

No equivale a orden, fill ni autorización de ejecución.

### `EXPANSION_NO_ENTRY`

Si no hay retest del POI dentro de la ventana de observación, la ruptura se
registra como expansión correcta sin entrada. Perder una operación por no
perseguir precio es un resultado válido del modelo.

## 5. Stop estructural: cambio propuesto

La ausencia de swing de stop en el instante de aceptación no debe convertir la
ruptura en falsa. Debe impedir la entrada, no borrar la lectura.

Orden de autoridad para un stop posterior al retest:

1. swing de origen del impulso que siga intacto;
2. extremo estructural de la reacción/retest en M5;
3. extremo estructural confirmado en M1;
4. si ninguno existe: `NO_STRUCTURAL_STOP` y no hay setup.

No se permite usar PDH/PDL como stop por conveniencia ni crear un stop solo con
ATR. El ATR puede aportar margen a una estructura existente, nunca sustituirla.

## 6. Contexto multi-TF

En el corte final del caso, D1 era bajista y H4/H1 alcistas. La ruptura de PDH
fue alcista y el observador la marcó alineada con H4. ICT 3.0 debe registrar el
conflicto explícitamente:

- H4/H1 alineados: evidencia favorable a continuación local;
- D1 opuesto: transición o contratendencia macro;
- el conflicto eleva la evidencia exigida para el retest, pero no convierte por
  sí solo una ruptura observada en falsa.

La dirección HTF no puede reemplazar la geometría de la ruptura ni autorizar
una entrada.

## 7. Objetivos sin fuga de futuro

Los objetivos solo pueden usar liquidez intacta conocida al momento de la
decisión: swings M15/H1/H4 previos, niveles diarios o semanales ya cerrados y
su ciclo de contactos. El máximo final del mismo viernes (`1.65903`) no era
conocido a las 17:30 y no puede usarse retrospectivamente como target del caso.

## 8. Invalidez

Separar invalidez de lectura e invalidez de entrada:

- `BREAK_INVALID`: cierre M15 de vuelta dentro antes de la aceptación;
- `ACCEPTANCE_LOST`: cierre M15 dentro después de la aceptación y antes del
  retest;
- `POI_INVALID`: cierre contrario atraviesa el límite estructural del POI;
- `SETUP_INVALID`: rompe el stop estructural después de existir setup.

## 9. Validación requerida antes de activar

Ejecutar replay causal sobre dos años D1 y suficiente M15 para los 26 pares,
separando por:

- PDH frente a PDL;
- Londres, Nueva York y fuera de killzone;
- alineación D1/H4/H1;
- terciles de `body_ratio`, `body_multiple` y `close_extension`;
- con/sin FVG, con/sin OB;
- retest en 4, 8, 16 y 32 velas M15;
- ruptura aceptada, fallo, expansión sin retest y setup observable;
- MAE/MFE posterior sin convertirlo en ejecución simulada;
- costes solo cuando exista una entrada causal definida.

Comparar al menos:

1. modelo actual (`no_stop_structure` descarta al confirmar);
2. modelo propuesto (conserva ruptura y espera retest/stop);
3. control sin filtro de fuerza.

No modificar el motor activo hasta que la prueba PIT demuestre que
`prefix_to_t == full_series_at_t` y exista evidencia fuera de muestra.

## 10. Relación con ICT 2.0

La propuesta conserva las reglas firmadas:

- sweep = ruptura con cierre de vuelta dentro;
- displacement real exige cuerpo dominante;
- BOS/CHOCH/MSS se confirma al cierre;
- entrada solo en retorno a FVG/OB;
- stop siempre estructural;
- precio sin retorno = no entrada.

La ampliación de ICT 3.0 consiste en representar explícitamente una ruptura
aceptada que aún no tiene entrada, evitando que `no_stop_structure` elimine una
lectura de mercado válida.

## Fuentes de autoridad

- [SPEC_TESIS_FORMAL, revisión f453bf2](https://github.com/vjack666/ict2.0/blob/f453bf2a9d35997cec774048a7ead25237399ac9/docs/ict/SPEC_TESIS_FORMAL.md)
- [Índice de autoridad, revisión f453bf2](https://github.com/vjack666/ict2.0/blob/f453bf2a9d35997cec774048a7ead25237399ac9/docs/INDICE_AUTORIDAD.md)
- [SDD LTF/EXEC, revisión f453bf2](https://github.com/vjack666/ict2.0/blob/f453bf2a9d35997cec774048a7ead25237399ac9/docs/tesis/SDD_LTF_ENTRY_LAYER.md)

