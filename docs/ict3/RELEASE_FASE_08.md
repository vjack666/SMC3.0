# Registro de release — Fase 8: Integración y operación del servidor

**Entrega final de Fase 8 (reverificación en modo estricto).**
**Hora (UTC):** 2026-11-22T16:30Z – 16:35Z.
**Addendum de correcciones (revisión `2b75b99c`): sección 8, 16:51Z – 17:00Z.**
La Fase 8 sigue en `[~]`: los puntos 2 y 3 tienen evidencia nueva, el punto 1
(MT5 con cotización autorizada fresca) continúa bloqueado.
**Modo:** `OBSERVE_ONLY_NO_ORDER` — sin órdenes, lotaje, fills, P&L, credenciales, posiciones ni cambios en `data/`.
**Autoridad ICT 2.0:** `f453bf2` (hash completo servido en `source`: `f453bf2a9d35997cec774048a7ead25237399ac9`).
**Revisión del repositorio:** rama `main` sin commits (`git log -1` → "your current branch 'main' does not have any commits yet"); no hay SHA de commit. La revisión probada se identifica con las huellas SHA-256 de la sección 1.1.
**Este registro sustituye al borrador de las 16:19–16:22Z**, que declaró una escritura automática en `data/diario-*.json` por el auto-sync de la interfaz. Esa desviación **no se repitió** en esta corrida: no se abrió navegador, no se hizo POST y los hashes de `data/` son idénticos antes y después.

## 0. Responsables, delegación y solapamientos

El plan `00_INDICE_PLAN_CONTINUO_HERMES.md` permite ejecutar los encargos en orden y registrar quién los asume cuando no hay agentes separados. En esta corrida `delegate_task` devolvió "presupuesto agotado (0/2)", de modo que **Hermes asumió los cuatro papeles en secuencia**. La petición del mensaje se cumplió en el orden indicado y con una sola propiedad de escritura: este registro. Producción y `data/` quedaron intactos.

| Rol (según el mensaje) | Asumido por | Escritura | Resultado |
|---|---|---|---|
| 1. Preparación | Hermes | Ninguna | Revisión, arranque, respuestas previas y reversión registrados |
| 2. Verificación | Hermes | Ninguna en producción; script solo en `$TMPDIR` | Suite, endpoints de lectura e interfaz estática comprobados |
| 3. Auditoría | Hermes | Ninguna | Rutas de orden, credenciales/`data/` y DXY comprobados |
| 4. Integración | Hermes | `docs/ict3/RELEASE_FASE_08.md` | Solapamientos resueltos; registro final entregado |

Solapamientos resueltos:

- Los dos ganchos de Fase 6 que el borrador dejaba sin ejecutar están cubiertos: la prueba específica `test_ict3_ui_contract` pasó 13/13 de nuevo. Ya no son pendientes.
- Las 4 incidencias de marca temporal de US30 con `cutoff=asof` se confirman, pero con `cutoff=now` son 0. No se cambió código: es decisión de alcance sobre semántica de `asof`, no uso de velas futuras.
- `book22[].entry` existe en el legado ICT 2.0 fuera del bloque `ict3`; dentro de `ict3` la única clave de la familia de ejecución es el propio indicador `entry_authorized`, siempre `false`. Se declara, no se toca.

## 1. Preparación

### 1.1 Huellas de la revisión probada (SHA-256)

```
a86e91c529c261302bd8fa0256669f326fd75c2e3f55fe4cb943bcfd29adbe20  abrir-smc.cmd
28a25c71c83c4908080c169241a562c808e7189a82432f34fe5e1dea03610eb4  smc.py
34695eae6ef2b8ff136978301e6ce4faa8b6ea276d8096e8e1cf004ad8634879  app.js
330ee37ee52ad5edf157e7040551270eff0520e8d6dec7f76784412cd0a0e8d4  index.html
5d49e93cedfbf6d5f55d3a6bd1beb6693b1573087c19952b033220756cf30fa8  style.css
dcaa6c8fbdba496a163da08696589eb0569aba7dc0903019217b06f5b8795285  ict3_contract.py
778ff1be6fc18d34f8873c7b9686e30ba0fc07e53ca0bb58bcb95091e64de84d  ict3_oos.py
```

### 1.2 Arranque

`abrir-smc.cmd` comprueba el puerto 8766 con un `TcpClient` de PowerShell y solo lanza `.venv\Scripts\python.exe smc.py serve` si está libre; después abre `http://127.0.0.1:8766`. **No mata ni sustituye** un proceso en marcha. En esta corrida `GET /` devolvió 200 antes de cualquier acción, así que el servicio ya estaba levantado: no se lanzó ni se reinició nada. Se ejercitó directamente el servidor en marcha, que es el estado que `abrir-smc.cmd` habría confirmado.

### 1.3 Respuestas previas (baseline del borrador de Fase 8)

| Endpoint | Código | Evidencia previa |
|---|---|---|
| `/api/market?symbol=EURUSD&tf=M15` | 200 | `checked_at=2026-11-22T15:41:14Z`, velas M15 |
| `/api/market-universe` | 200 | inventario sin error |
| `/api/poi-universe` | 200 | `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` |
| `/api/ict?symbol=EURUSD&tf=M15` | 200 | `schema_version=0.2-research`, `mode=OBSERVE_ONLY_NO_ORDER`, 5 eventos, 10 breaks |
| `/api/ict?symbol=GBPJPY&tf=M15` | 200 | 7 eventos, 12 breaks |
| `/api/ict?symbol=US30&tf=M15` | 200 | 6 eventos, 13 breaks, `load_reason=M5_M1_LOADED` |

### 1.4 Reversión segura

No se activaron cambios nuevos: los módulos y documentos ya existían y el servidor sigue sirviendo el contrato actual. No hay nada que deshacer. Si hiciera falta volver a una versión anterior preservando cambios ajenos:

1. Detener únicamente el proceso propio que ejecuta `smc.py serve`; nunca otros procesos de MT5 ni del puente.
2. Restaurar, uno por uno, solo los archivos de código implicados en esa activación, comparando antes con las huellas de 1.1.
3. **No reemplazar** `data/`, credenciales (`data/cuenta.json`) ni notas/marcajes: contienen cambios del usuario.
4. Reiniciar con `abrir-smc.cmd` y repetir los smoke tests de la sección 2.
5. Si falla solo la interfaz y el motor responde, basta con restaurar `index.html`, `app.js` y `style.css`, sin tocar el motor.

## 2. Verificación

### 2.1 Suite completa

```
cd C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0
.venv/Scripts/python.exe -m unittest discover -v
Ran 161 tests in 1.281s
OK
.venv/Scripts/python.exe -m unittest -v test_ict3_ui_contract
Ran 13 tests in 0.027s
OK
```

Sin fallos ni errores; cero saltos.

### 2.2 Endpoints de lectura (GET, servidor ya en marcha, `Host: 127.0.0.1:8766`)

Todas las respuestas incluyen `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`.

| Endpoint | HTTP | `schema_version` | `mode` | `entry_authorized` | Cobertura / detalle | Errores por activo |
|---|---|---|---|---|---|---|
| `/api/market-universe` | 200 | n/a | n/a | n/a | `assets=33`, `intraday=27`, `total=33` | — |
| `/api/poi-universe` | 200 | n/a | n/a | n/a | `forex=26`, `indices=4`, `commodities=3` | — |
| `/api/market?symbol=EURUSD&tf=M15` | 200 | n/a | n/a | n/a | `state=stale`, `m15_closed=1795218300`, `last_tick_mt5=1795219185` | `errors.openings`: "Esperando una cotización reciente de EURUSD para comprobar la hora de MT5." |
| `/api/market?symbol=GBPJPY&tf=M15` | 200 | n/a | n/a | n/a | `state=stale`, mismas marcas | el mismo mensaje de `openings` |
| `/api/market?symbol=US30&tf=M15` | 200 | n/a | n/a | n/a | `state=stale`, `last_tick_mt5=1795219079` | el mismo mensaje de `openings` |
| `/api/ict?symbol=EURUSD&tf=M15` | 200 | `0.2-research` | `OBSERVE_ONLY_NO_ORDER` | `false` en 5/5 eventos | 5 eventos, 10 breaks, 34 `book22`; `load_reason=NOT_REQUESTED_NO_M15_RETEST`, 0 velas M5/M1 | sin error de payload |
| `/api/ict?symbol=GBPJPY&tf=M15` | 200 | `0.2-research` | `OBSERVE_ONLY_NO_ORDER` | `false` en 7/7 eventos | 7 eventos, 12 breaks, 30 `book22`; mismo `load_reason`, 0 velas M5/M1 | sin error de payload |
| `/api/ict?symbol=US30&tf=M15` | 200 | `0.2-research` | `OBSERVE_ONLY_NO_ORDER` | `false` en 6/6 eventos | 6 eventos, 13 breaks, 16 `book22`; `load_reason=M5_M1_LOADED`, 551 velas M5 y 551 M1 | sin error de payload |
| `/api/ict?symbol=TVC:DXY&tf=M15` | 400 | n/a | n/a | n/a | `{"error": "Símbolo o temporalidad inválidos."}` | referencia manual, no feed operable |

`source=f453bf2a9d35997cec774048a7ead25237399ac9` en los tres payloads ICT. No aparece un campo `policy` separado; la política se declara en `ict3.mode`.

Validación del contrato con `ict3_contract.validate` (contrato `1.0`):

- EURUSD: `cutoff=asof` → 0 incidencias; `cutoff=now` → 0.
- GBPJPY: `cutoff=asof` → 0 incidencias; `cutoff=now` → 0.
- US30: `cutoff=asof` → 4 incidencias (2 `liquidez.observed_at`, `load.last_closed_m5`, `load.last_closed_m1`); `cutoff=now` → 0.
- Claves de ejecución exactas dentro de `ict3`: solo `entry_authorized` (indicador, siempre `false`). No hay `order`, `lots`, `volume`, `fill`, `fills`, `pnl`, `profit`, `entry_price`, `stop_loss` ni `take_profit`.

### 2.3 Interfaz (verificación estática, sin navegador)

`GET /` → 200 (14.636 bytes), `/app.js` → 200 (99.764), `/style.css` → 200 (11.528). Marcadores presentes: `#scanTarget`, `#dxyWidget`, título "SMC 3.0" en el HTML; `loadDxyWidget` y `/api/sync` en `app.js`; estilos `dxy` y `.panel`. La prueba de cableado de interfaz pasó 13/13.

**Decisión de solo lectura:** no se abrió la página en un navegador. `app.js` ejecuta `refreshJournal()` dentro de `start()` y lo repite cada 30 s; esa función hace `POST /api/sync`, que reconstruye `data/diario-*.json`. Abrir la interfaz habría vuelto a escribir en `data/`, prohibido por el modo de esta entrega. Por eso se verificó el servicio de archivos estáticos y el contrato de UI, y se deja el render interactivo explícitamente no ejecutado en esta corrida. `EventSource('/api/events')` pertenece al puente de mensajería, no a esta interfaz; `app.js` no lo usa.

### 2.4 MT5 y frescura — pendiente explícito

`state=stale` y `errors.openings` indican que el terminal no aporta una cotización reciente. El último cierre servido sigue siendo `2026-11-20T23:45:00Z` (epoch `1795218300`) frente a consultas del `2026-11-22T16:32Z`. Las verificaciones locales quedan completas; **la prueba temporal con velas recientes de MT5 queda PENDIENTE** y no se usaron credenciales para forzarla. No se afirma cobertura de mercado actual.

## 3. Auditoría de solo lectura

- **Rutas de orden:** `smc.py` solo expone GET de lectura y dos POST (`/api/sync` y `/api/notes`, ambos con validación de `Origin`). `/api/trade`, `/api/order`, `/api/position` y `/api/orders` devolvieron **404** en vivo. En `app.js` los únicos POST son `/api/sync` (línea 584) y `/api/notes` (línea 1816).
- **Sin efectos de órdenes:** no aparecen `order_send`, `order_modify`, `order_close` ni `positions_modify` en `smc.py`, `ict.py`, `ict22.py` ni los módulos `ict3_*`. Tampoco aparecen `history_deals_get`, `positions_get` ni `orders_get` en la capa HTTP; esas lecturas, cuando existen, viven dentro de `diario.sync()` en modo lectura.
- **Credenciales y `data/`:** no se abrieron, imprimieron ni introdujeron credenciales; `account.example.json` es solo plantilla y `data/cuenta.json` no se leyó. Los hashes directos de `data/` antes y después de todo el trabajo son idénticos: `avisos-apertura.json` `937c0197…`, `corte-inicial.md` `55b7f553…`, `cuenta.json` `d95d6f93…`, `diario-FundedNext-Server_3-35458088.json` `4c73368b…`, `ict-revision-eurusd.json` `6dc0b3b6…`, `marcajes.json` `524e4ecd…`. `git status --short` muestra solo archivos sin seguimiento (el repo no tiene commits), sin modificaciones rastreadas.
- **DXY:** `app.js` trata `TVC:DXY` como widget externo de TradingView (`loadDxyWidget`), `referenceInstrument()` devuelve `null` para DXY y `/api/ict?symbol=TVC:DXY&tf=M15` responde 400. DXY sigue siendo **referencia manual**, nunca símbolo operable ni parte del universo MT5.

## 4. Cobertura declarada (no interpretar como dato real)

El inventario contiene 26 pares, 4 índices y 3 materias primas; solo se sondearon EURUSD, GBPJPY y US30. La cobertura real sigue marcada como `REAL_COVERAGE_PENDING` y la fuente OOS como `SYNTHETIC_DECLARED` (`ict3_oos.SYNTHETIC_SOURCE` y `REAL_PENDING`). Los resultados de Fase 7 son sintéticos declarados: **no se presentan como datos reales ni como rentabilidad**. Ninguna cifra de cuenta del tablero forma parte de esta entrega.

## 5. Criterios de aceptación

| Criterio | Resultado |
|---|---|
| Suite completa OK | SÍ — 161/161, más UI 13/13, sin saltos |
| Endpoints compatibles | SÍ — 200, contrato `1.0` / esquema `0.2-research` sin cambios |
| Interfaz funcionando | SÍ en modo estático — activos 200, cableado verificado; render interactivo omitido a propósito por `data/` |
| Cobertura declarada | SÍ — 26/4/3 en inventario; 3 sondeados; `REAL_COVERAGE_PENDING` |
| Reversión documentada | SÍ — sección 1.4, sin cambios que revertir |
| Evidencia de solo lectura | SÍ — hashes de `data/` idénticos, sin POST, sin credenciales, sin órdenes |
| Prueba en vivo con MT5 | PENDIENTE — cotización no fresca; verificaciones locales completas |

## 6. Riesgos y pendientes

1. Frescura de MT5: `state=stale`; impedimento externo, no de código.
2. Semántica de `asof` frente a M5/M1 cerrados posteriores (US30): requiere decisión de alcance de Rubén/GPT; no se modificó nada.
3. Cobertura real de los 26 pares y 4 índices: `REAL_COVERAGE_PENDING`; no inferir de los 3 casos probados.
4. `book22[].entry` del legado ICT 2.0: fuera de `ict3`, no es orden; se declara y no se toca.
5. Auto-sync de la interfaz: abrir la página dispara `POST /api/sync` y reescribe `data/diario-*.json`; en modo estricto verificar solo archivos estáticos o bloquear esa petición.

## 7. Confirmación de solo lectura

No se enviaron ni modificaron órdenes, posiciones, tickets, lotes, volumen, fills, P&L ni saldos. No se abrieron, imprimieron ni introdujeron credenciales. No se reinició el servidor. **No hubo ninguna escritura en `data/`:** los seis hashes directos son idénticos a los registrados antes de empezar. No se abrió navegador ni se hizo POST a ningún endpoint. `entry_authorized` permaneció en `false` y `mode` en `OBSERVE_ONLY_NO_ORDER` en todos los payloads consultados. Durante el trabajo no se consultó `/api/inbox` ni se buscaron mensajes nuevos; el puente sigue con la tarea activa y se cierra al entregar este informe.

## 8. Addendum — correcciones de la revisión `2b75b99c`

**Ventana:** 2026-11-22T16:51Z – 17:00Z. **Autoridad:** ICT 2.0 `f453bf2`.
Este addendum actualiza los tres pendientes señalados por GPT. Las secciones
1–7 quedan como registro histórico de la entrega de las 16:30Z.

### 8.1 Frescura MT5 — bloqueo explícito, sin cambio de estado

Sondeo de lectura contra el servidor en marcha (`GET`, sin `at`):

| Activ | `checked_at` | `state` | `m15_closed` | `last_tick_mt5` | `errors.openings` |
|---|---|---|---|---|---|
| EURUSD | `2026-11-22T16:51:45.693793Z` | `stale` | `1795218300` | `1795219185` | "Esperando una cotización reciente de EURUSD para comprobar la hora de MT5." |
| US30 | igual | `stale` | `1795218300` | `1795219079` | el mismo mensaje |

Último cierre observado: **`2026-11-20T23:45:00Z` (`1795218300`)**, con
consulta a **`2026-11-22T16:51:45Z`**. No existe cotización autorizada fresca:
se mantienen `state=stale` y `REAL_COVERAGE_PENDING` y **no se declara cobertura
viva**. No se usaron credenciales ni se forzó la carga de MT5. **Bloqueo
entregado**, no resuelto: depende de una cotización autorizada, no de código.

### 8.2 `cutoff=asof` en US30 — aislado y documentado sin cambiar el validador

Se capturó `GET /api/ict?symbol=US30&tf=M15` y se validó con
`ict3_contract.validate`:

- `cutoff=asof` (`1795218300` = cierre M15 stale) → **4 incidencias**:
  2 × `liquidez.observed_at` en `evt_36b6f6e056899a9c` y
  `evt_ba099ef9917346ec` (`M1_SWING`, `1795218540`),
  `load.last_closed_m5` (`1795219200`) y `load.last_closed_m1` (`1795219080`).
- `cutoff=now` (`1795219200`, reloj de pared usado por `attach_confirmations`)
  → **0 incidencias**.

Regla causal documentada: el productor usa dos relojes — el ancla M15
(`result['asof']`) y el reloj de pared que filtra M5/M1. Esos tres campos son
`<=` el corte de construcción, por lo que **no son velas futuras**; pasar el
`asof` stale como `cutoff` mezcla ambos relojes. Se añadieron el documento
`docs/ict3/CUTOFF_ASOF_REGLA_CAUSAL.md`, la docstring de
`ict3_contract.validate` y el módulo de pruebas `test_ict3_cutoff_asof.py`
(3/3 OK): 0 incidencias para un payload histórico válido, 4 incidencias
aisladas en la forma exacta, y todas las marcas marcadas `<=` su corte de
construcción. No se modificó la lógica de `validate`: el único código cambiado
es su docstring, por lo que `ict3_contract.py` pasa de la huella `dcaa6c8f…`
(§1.1) a `e031413d5a888e26420a8f802521887bb211a7e235b963836e89ce2dfc586b1c`.

### 8.3 Interfaz interactiva — harness aislado, sin POST real ni `data/`

Se ejecutó el render real en un navegador contra un servidor efímero en
`127.0.0.1:8799` cuyo documento es una copia de `index.html`/`app.js`/`style.css`
en `$TMPDIR/ui_harness`, con un `fetch` inyectado antes de `app.js` que:

- intercepta **todo** método no GET y responde localmente con
  `{harness_blocked:true}`; el único POST observado fue el `/api/sync` del
  arranque, **respondido en el harness sin llegar al servidor 8766**;
- sirve para `/api/ict` un payload US30 capturado por GET (6 expedientes reales)
  más un séptimo evento sintético explícitamente etiquetado
  `HARNESS_SYNTHETIC_OBSERVABLE` para cubrir `OBSERVABLE_SETUP`.

Evidencia del render interactivo (no estático):

- Activadores evaluados: `loadDetailedAnalysis()` y cambio de
  `#analysisSymbol` para `EURUSD`, `GBPJPY` y `US30`.
- Por activo: **7 expedientes × 8 etapas = 56 nodos**
  `[data-ict3-stage]`, sin etapas ausentes.
- Etapas presentes en cada tarjeta: `ruptura`, `zona`, `retest`, `m5`, `m1`,
  `stop`, `objetivos`, `invalidacion`, cada una con
  `data-ict3-state`, `data-ict3-time` y `data-ict3-reason` no vacíos.
- Estados renderizados del payload vivo: `POI_INVALID` (2),
  `EXPANSION_NO_ENTRY`, `RETESTING_POI` (2),
  `ACCEPTED_BREAK_WAIT_RETEST`, más el sintético `OBSERVABLE_SETUP`.
- `ict3DetailStatus`: "US30 · 7 expedientes ICT 3.0 · esperando evidencia en 3
  · actualizado al 20-nov, 11:45 p. m. · hora MT5".
- GETs emitidos: `/api/poi-universe`, `/api/notes`, `/api/journal`,
  `/api/market?...`, `/api/market-universe` y
  `/api/ict?symbol={EURUSD,GBPJPY,US30}&tf=M15`. POSTs reales al servidor: 0.
- Captura: `C:\Users\v_jac\.config\browser-harness\tmp\p-46fbce37aab8\shot.png`.

La prueba estática 13/13 sigue vigente; esta verificación es adicional y
complementaria, no la sustituye.

### 8.4 Estado de criterios tras el addendum

| Criterio | Estado |
|---|---|
| Punto 1 · MT5 con cotización autorizada fresca | **BLOQUEADO** — `state=stale`, `REAL_COVERAGE_PENDING` |
| Punto 2 · 4 incidencias `cutoff=asof` | **RESUELTO** — documentadas + 3/3 pruebas (0 incidencias con corte propio) |
| Punto 3 · render interactivo de 8 etapas | **RESUELTO** — 3 activos × 7 × 8 etapas en navegador aislado |
| Fase 8 | **`[~]`** — no se marca `[x]` mientras el punto 1 carezca de evidencia |

### 8.5 Nota de solo lectura del addendum

No se enviaron órdenes, no se usaron credenciales, no se pulsó `/api/sync` real
y no se consultó `/api/inbox`. Cinco de los seis hashes de `data/` permanecen
idénticos a los de la sección 3. Se detectó **una escritura externa concurrente**
en `data/diario-FundedNext-Server_3-35458088.json` a las `2026-11-22T16:58:10Z`
(`4c73368b…` → `7d0611aa…`): `smc.py` solo escribe ese archivo desde
`POST /api/sync`, que en el harness fue interceptado y nunca alcanzó el puerto
8766; las demás rutas usadas fueron GET de lectura. No se observaron cambios
adicionales durante 35 s de observación posterior. Esta modificación externa
se reporta y **no se atribuye a esta corrida**; ninguna acción del addendum
escribió en `data/`.
