# Revisión GPT del Lote Hermes 02 — correcciones de causalidad

**Entrega revisada:** `821d3390-1df8-4d6f-abc6-708e61dfd3aa`  
**Resultado:** no aceptada todavía. La suite entregada pasa 58/58, pero pruebas diagnósticas adicionales encontraron reescritura por futuro y dos errores en la máquina de estados/ventanas.

## Evidencia verificada

- Las correcciones originales C1–C3 están implementadas.
- `ict3_simulation.py` pasa `symbol=symbol`.
- El bloque `ict3` conserva `ict3_breaks` y mantiene `entry_authorized=false`.
- La suite completa entregada ejecuta 58 pruebas sin fallos.
- No se encontraron rutas de órdenes nuevas.

## Corrección obligatoria C4 — un retest tardío borra `EXPANSION_NO_ENTRY`

La máquina recorre todas las velas disponibles antes de fijar la transición de expansión. Si en el corte de 32 velas no hubo retest, el evento se marca correctamente como `EXPANSION_NO_ENTRY`; pero al añadir una vela posterior que toca el POI, el mismo evento se reescribe como `RETESTING_POI` y desaparece la transición de expansión.

Resultado diagnóstico observado:

```text
corte de 32 M15: EXPANSION_NO_ENTRY
futuro con toque tardío: RETESTING_POI
```

Esto viola la invariancia causal. Una vez agotado el horizonte máximo, el retest tardío no puede reabrir el setup.

### Corrección requerida

- Procesar las transiciones en orden cronológico dentro de un único recorrido.
- En el cierre exacto de la ventana máxima, si no hubo retest, transicionar a `EXPANSION_NO_ENTRY` y convertirlo en estado terminal para este evento.
- Ignorar para este setup los contactos posteriores al horizonte; pueden registrarse como observación separada, pero no cambiar el estado.
- Añadir prueba con ausencia de retest hasta 32 M15 y toque en la vela 40; ambos replays deben conservar `EXPANSION_NO_ENTRY` y la misma transición.

## Corrección obligatoria C5 — `window_results` usa evidencia posterior a su horizonte

`window_results` deriva el estado de cada ventana desde el estado global final. Si el POI se invalida después de terminar la ventana de 4 velas, la ventana de 4 se presenta retroactivamente como `POI_INVALID`.

Resultado diagnóstico observado:

```text
ventana 4 termina en 1700007200
POI_INVALID ocurre en 1700009900
window_results["4"].state == POI_INVALID  # incorrecto
```

### Corrección requerida

- Evaluar cada ventana únicamente con transiciones cuyo `at <= horizon` de esa ventana.
- El estado de ventana debe ser el último estado conocido a su propio horizonte.
- `retest_within` debe respetar el mismo límite.
- Añadir prueba con retest dentro de 4 velas e invalidación posterior: ventana 4 queda `RETESTING_POI`; una ventana que incluya la invalidación queda `POI_INVALID`.
- Añadir una aserción general: ningún estado de ventana puede depender de una transición posterior a su `horizon`.

## Corrección obligatoria C6 — gap que salta el POI no invalida la zona

El código solo comprueba `POI_INVALID` después de entrar en `RETESTING_POI`. Si una vela abre y cierra por debajo del POI alcista sin solaparlo, pero aún cierra por encima del PDH roto, el evento permanece `ACCEPTED_BREAK_WAIT_RETEST` aunque el límite estructural de la zona ya fue atravesado.

Resultado diagnóstico observado con OB alcista `1.210–1.220`, PDH `1.200` y cierre por gap en `1.205`:

```text
current_state = ACCEPTED_BREAK_WAIT_RETEST
transition_history = []
```

### Corrección requerida

- Evaluar invalidez estructural del POI desde que la zona está confirmada, incluso si no hubo solapamiento/touch previo.
- Para dirección alcista, cierre `< low`; para bajista, cierre `> high`.
- Si el mismo cierre también pierde PDH/PDL, definir precedencia determinista y documentarla. Recomendación: `ACCEPTANCE_LOST` para pérdida del nivel diario antes de retest; `POI_INVALID` cuando atraviesa el POI pero conserva el nivel roto.
- Añadir pruebas simétricas de gap alcista y bajista sin contacto geométrico.

## Corrección obligatoria C7 — prueba HTTP no prueba HTTP

`test_http_contract_headers_remain_read_only` inspecciona texto fuente de `smc.py`; no abre el servidor ni valida una respuesta real. Puede pasar aunque los encabezados o el enrutamiento fallen en ejecución.

### Corrección requerida

- Añadir una prueba de integración con `LocalServer` en puerto efímero o un handler ejecutado en memoria.
- Verificar respuesta real de un GET permitido: `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`.
- Verificar `Host` inválido → 403, corte inválido → 400 y ruta de trading inexistente → 404.
- No tocar el servidor habitual ni usar MT5 en esta prueba.

## Criterios de aceptación de la corrección

1. Mantener las 58 pruebas existentes.
2. Añadir pruebas para C4, C5, C6 alcista/bajista y C7.
3. Ejecutar suite completa sin fallos.
4. Probar invariancia de prefijos antes y después del horizonte de 32 M15.
5. Confirmar que `entry_authorized=false` y `OBSERVE_ONLY_NO_ORDER` permanecen.
6. No avanzar a M5/M1, interfaz ni rentabilidad hasta que este lote quede aceptado.

## Entrega requerida

Entregar un único informe con:

- resumen por C4–C7;
- archivos y funciones modificados;
- resultados de la suite;
- payload comparado para expansión antes/después del toque tardío;
- resultados de las ventanas 4/8/16/32 sin fuga temporal;
- casos de gap alcista y bajista;
- evidencia de la prueba HTTP real;
- confirmación de solo lectura y ausencia de cambios en `data/`.
