# Diccionario del contrato `ict3` — Fase 5

Generado desde `ict3_contract.describe()`. Contrato 1.0 · esquema `0.2-research` · modo `OBSERVE_ONLY_NO_ORDER`.

Todos los instantes son epoch Unix en segundos. Los precios están en el
nivel de precisión del símbolo. Ningún campo autoriza una operación.

## Reglas de lectura

1. El subobjeto de confirmación M5/M1 es todo-o-nada: está ausente en
   eventos que nunca entraron en `RETESTING_POI`, y completo en los que sí.
2. `pending_evidence` explica qué falta; `wait_reason` es su unión legible.
3. `load_reason` explica la carga de marcos inferiores, no el estado de la idea.
4. `entry_authorized` es siempre `false` y `mode` siempre `OBSERVE_ONLY_NO_ORDER`.

## Bloque `ict3` (nivel superior)

| Campo | Tipo | Nulo | Unidad | Procedencia | Significado |
|---|---|---|---|---|---|
| `schema_version` | str | no | - | interno | Version del bloque ict3; hoy 0.2-research. |
| `mode` | str | no | - | interno | Siempre OBSERVE_ONLY_NO_ORDER. |
| `events` | list | no | - | daily_break_studies + link_breaks | Expedientes causales, uno por ruptura aceptada. |
| `load` | dict | no | - | attach_confirmations | Estado de la carga M5/M1 bajo demanda. |

## Evento (`ict3.events[]`)

| Campo | Tipo | Nulo | Unidad | Procedencia | Significado |
|---|---|---|---|---|---|
| `event_id` | str | no | - | daily_break_studies | Identificador determinista de la ruptura. |
| `symbol` | str | no | - | consulta /api/ict | Activo consultado. |
| `session_open` | int | no | epoch s | D1 | Apertura de la sesion diaria. |
| `observed_at` | int | no | epoch s | M15 cerrada | Instante en que se conocio el evento. |
| `state_time` | int | no | epoch s | maquina de estados | Instante del ultimo estado. |
| `accept_time` | int | sí | epoch s | M15 cerrada | Cierre que acepto la ruptura. |
| `level_name` | str | no | - | D1 | PDH o PDL. |
| `level` | int|float | no | precio | D1 | Nivel de liquidez leido. |
| `direction` | int | no | +1/-1 | D1 + M15 | Sentido de la ruptura. |
| `force` | dict | no | - | cuerpo/rango M15 | Medidas de la vela de senal. |
| `link_state` | str | no | - | link_breaks | Resultado de la asociacion causal. |
| `current_state` | str | no | - | maquina de estados | Estado causal actual. |
| `retest_at` | int | sí | epoch s | M15 cerrada | Cierre del retest observado. |
| `poi_candidates` | list | no | - | FVG/OB ICT 2.0 | Zonas canonicas candidatas. |
| `primary_poi` | dict|str | sí | - | link_breaks | Zona principal asociada (objeto) o id heredado de zona. |
| `transition_history` | list | no | - | maquina de estados | Transiciones con hora y motivo. |
| `window_results` | dict | no | - | link_breaks | Resultado por ventana de observacion. |
| `observation_windows` | list | no | - | link_breaks | Ventanas comparables usadas. |
| `pending_evidence` | list | no | - | motor | Evidencia que todavia falta; nunca se inventa. |
| `wait_reason` | str | no | - | motor | Union de pending_evidence o OBSERVATION_ONLY. |
| `entry_authorized` | bool | no | - | politica | Siempre false. |
| `mode` | str | no | - | politica | Siempre OBSERVE_ONLY_NO_ORDER. |
| `confirmation_state` | str | no | - | M5/M1 | WAIT_M5_M1_CONFIRMATION o M5_STRUCTURE_CONFIRMED. |
| `defense_at` | int | sí | epoch s | M5 cerrada | Cierre M5 de la primera defensa. |
| `m5_structure_kind` | str | sí | BOS/CHOCH/MSS | M5 cerrada | Estructura M5 confirmada por cierre. |
| `m5_structure_at` | int | sí | epoch s | M5 cerrada | Cierre de la vela de ruptura M5. |
| `m1_structure_kind` | str | sí | BOS/CHOCH/MSS | M1 cerrada | Corroboracion M1, nunca sustituto de M5. |
| `m1_structure_at` | int | sí | epoch s | M1 cerrada | Cierre de la vela de ruptura M1. |
| `stop_basis` | str | no | - | swing causal | Autoridad del stop estructural informativo. |
| `stop_price` | int|float | sí | precio | swing causal | Precio informativo del stop; no es una entrada. |
| `stop_observed_at` | int | sí | epoch s | swing causal | Instante en que el pivote era conocible. |
| `target_policy_status` | str | no | - | liquidez conocida | Estado de la politica TP1>=3R / TP2>=5R. |
| `target_price` | int|float | sí | precio | liquidez conocida | Liquidez conocida mas cercana. |
| `target_liquidity` | list | no | - | M5/M1 cerradas | Niveles {kind, price, observed_at}. |

## Carga bajo demanda (`ict3.load`)

| Campo | Tipo | Nulo | Unidad | Procedencia | Significado |
|---|---|---|---|---|---|
| `m5_loaded` | bool | no | - | M5 cerradas | Existe al menos una vela M5 cerrada <= cutoff. |
| `m1_loaded` | bool | no | - | M1 cerradas | Existe al menos una vela M1 cerrada <= cutoff. |
| `last_closed_m5` | int | sí | epoch s | M5 cerradas | Ultimo cierre M5 observable. |
| `last_closed_m1` | int | sí | epoch s | M1 cerradas | Ultimo cierre M1 observable. |
| `coverage` | dict | no | - | M5/M1 cerradas | Conteo y primeros cierres observados. |
| `load_reason` | str | no | - | carga bajo demanda | Motivo de carga o espera. |

## Cobertura (`ict3.load.coverage`)

| Campo | Tipo | Nulo | Unidad | Procedencia | Significado |
|---|---|---|---|---|---|
| `m5_bars_closed` | int | no | velas | M5 cerradas | Velas M5 usadas. |
| `m1_bars_closed` | int | no | velas | M1 cerradas | Velas M1 usadas. |
| `m5_first_closed` | int | sí | epoch s | M5 cerradas | Cierre M5 mas antiguo usado. |
| `m1_first_closed` | int | sí | epoch s | M1 cerradas | Cierre M1 mas antiguo usado. |
| `events_requested` | int | no | eventos | maquina de estados | Eventos en RETESTING_POI que pidieron carga. |

## Transición (`transition_history[]`)

| Campo | Tipo | Nulo | Unidad | Procedencia | Significado |
|---|---|---|---|---|---|
| `from` | str | no | - | maquina de estados | Estado anterior. |
| `to` | str | no | - | maquina de estados | Estado nuevo. |
| `at` | int | no | epoch s | vela cerrada | Instante de la transicion. |
| `reason` | str | no | - | motor | Motivo legible de la transicion. |

## Liquidez conocida (`target_liquidity[]`)

| Campo | Tipo | Nulo | Unidad | Procedencia | Significado |
|---|---|---|---|---|---|
| `kind` | str | no | BROKEN_LEVEL/M5_SWING/M1_SWING | estructura | Tipo de liquidez. |
| `price` | int|float | no | precio | estructura | Precio de la liquidez. |
| `observed_at` | int | no | epoch s | estructura | Instante en que era conocible. |

## Campos heredados conservados en `ict3_breaks`

Se mantienen sin cambio para los consumidores actuales:

`event_id`, `session_open`, `source_open`, `level_name`, `level`, `direction`, `signal_open`, `signal_close`, `body_ratio`, `body_multiple`, `close_extension`, `close_location`, `strong_body`, `strong_range`, `strong_extension`, `strong`, `state`, `observed_at`, `state_time`, `accept_time`, `accept_open`, `failure_time`.

## Claves prohibidas

Nunca aparecen en el bloque: `balance`, `cash_value`, `deal`, `entry`, `equity`, `fill`, `lots`, `margin`, `order`, `pnl`, `position`, `ticket`, `volume`.

## Casos de espera distinguibles

| Clase | Significado | `wait_reason` representativo | `load_reason` |
|---|---|---|---|
| `SIN_RETEST` | Ruptura aceptada todavia sin retest observable. | `RETEST_NOT_OBSERVED` | `NOT_REQUESTED_NO_M15_RETEST` |
| `DATOS_AUSENTES` | No hay velas M5/M1 cerradas utilizables al corte. | `M5_M1_CONFIRMATION_NOT_LOADED` | `LOWER_SOURCE_UNAVAILABLE / LOWER_SOURCE_MALFORMED / NO_CLOSED_M5_BARS_AT_CUTOFF / M1_BARS_UNAVAILABLE_M5_USED` |
| `EVIDENCIA_INSUFICIENTE` | Datos cargados, pero falta defensa, estructura, stop o liquidez. | `M5_M1_CONFIRMATION_NOT_COMPLETE` | `M5_M1_LOADED` |

El clasificador `ict3_contract.classify_wait(block)` devuelve una de esas
clases, o `SIN_ESPERA` cuando no falta evidencia. Está probado en
`test_ict3_contract_dictionary.py`.
