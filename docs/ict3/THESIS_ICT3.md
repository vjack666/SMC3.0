# Tesis ICT 3.0 — borrador normativo de investigación

## Principio

ICT 3.0 conserva la cadena de ICT 2.0:

```text
HTF bias → liquidez → sweep o ruptura → displacement → BOS/CHOCH
→ FVG/OB → retest → confirmación M5/M1 → setup observable
```

La novedad es que una ruptura aceptada se conserva como evidencia aunque aún
no exista entrada, stop o retest.

## Mapa de máximos y mínimos del día anterior

El PDH/PDL de cada jornada es un mapa de liquidez, no una señal por sí mismo.
Para cada símbolo y cada día se registran por separado:

| Lectura | Condición causal | Interpretación |
|---|---|---|
| `SWEEP_PDH/PDL` | La mecha cruza el nivel y el cierre vuelve dentro en la misma vela | Toma de liquidez; no es ruptura aceptada |
| `BREAK_CANDIDATE` | Primer cierre fuera del nivel | Ruptura aún no confirmada |
| `FAILED_BREAK` | Vuelve dentro antes de dos cierres consecutivos fuera | Fallo de ruptura; puede ser barrido si la mecha y el cierre cumplen |
| `ACCEPTED_BREAK_WAIT_RETEST` | Dos cierres consecutivos fuera | Rompimiento aceptado; todavía no es entrada |
| `EXPANSION_NO_ENTRY` | Aceptación sin retorno a FVG/OB dentro de la ventana | Continuación observada sin perseguir precio |

El mapa conserva el día fuente, el nivel, la hora del primer cruce, la hora de
aceptación o fallo, dirección, fuerza de la vela y contexto D1/H4/H1. Nunca se
mezclan en una misma etiqueta el barrido y el rompimiento.

La primera simulación de 26 pares produjo 1.101 aceptaciones y 1.247 fallos
con 5.000 M15 por símbolo. Son conteos de observación, no resultados de
rentabilidad ni evidencia de ventaja estadística. La cobertura y el desglose
por símbolo están en el [mapa de simulación](../research/ICT3_SIMULACION_26_PARES.md).

## Ruptura fuerte de PDH/PDL

Una ruptura fuerte es una hipótesis de ingeniería, no una definición histórica
cerrada, hasta calibrarla. Sus señales son:

```text
body_ratio >= 0.70
body_multiple >= 1.50
close_extension >= 0.50
```

La ruptura solo se acepta después de dos cierres consecutivos fuera del nivel.
Una mecha fuera con cierre dentro permanece como sweep.

## Estados

- `BREAK_CANDIDATE`: primer cierre cruzando el nivel.
- `FAILED_BREAK`: vuelve al rango antes de aceptación.
- `ACCEPTED_BREAK_WAIT_RETEST`: dos cierres fuera; lectura válida, sin entrada.
- `RETESTING_POI`: el precio regresa a FVG/OB.
- `OBSERVABLE_SETUP`: retest, defensa, M5/M1, stop y objetivo causales.
- `EXPANSION_NO_ENTRY`: continúa sin volver al POI.
- `INVALIDATED`: pierde la aceptación o invalida el POI/stop.

## Seguridad epistemológica

- Una etiqueta no es una orden.
- Un score no reemplaza evidencia.
- Una ruptura fuerte no obliga a perseguir precio.
- Un target solo usa liquidez conocida en el corte.
- El tick volume MT5 es relativo al feed.
- OTE/Fibonacci no se reintroducen.

## Estado de implementación

La primera implementación añade el detector causal y el vector de fuerza al
payload del motor. La máquina completa de retest M5/M1 queda como la siguiente
fase, sujeta a la simulación de 26 pares y a validación fuera de muestra.

