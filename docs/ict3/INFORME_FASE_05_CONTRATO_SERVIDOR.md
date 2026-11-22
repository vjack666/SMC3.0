# Informe Fase 5 — Contrato del servidor local

**Estado:** entregada para revisión de GPT. Cierre de la Fase 4 confirmado:
GPT aceptó el Lote 03 corregido y el Lote 04, y esta sesión verificó la línea
base con `.venv/Scripts/python.exe -m unittest discover` → 107 pruebas / OK.
No quedó pendiente de ejecución en Fase 4; la corrección causal del stop ya
está documentada en `REVISION_LOTE_03_CORRECCIONES_CAUSALIDAD.md`.

## 1. Responsables y propiedad de escritura

No había agentes externos disponibles para este encargo dentro de esta sesión,
así que Hermes asumió los tres papeles en el orden del plan e indicó quién ejerce
cada uno. La regla de un único propietario de escritura por archivo se respetó.

| Papel (agente asumido por Hermes) | Archivos autorizados (propietario de escritura) | Insumos | Resultado | Prueba de aceptación |
|---|---|---|---|---|
| Contrato | `ict3_contract.py`, `docs/ict3/CONTRATO_ICT3_DICCIONARIO.md` | `ict.py:ict3_payload`, `ict3_confirm.attach_confirmations`, `smc.Handler` | Catálogo de 56 campos, validador y clasificador de espera | `describe()` serializable; `validate()` sin incidencias en payloads reales |
| HTTP / superficie | `test_ict3_contract_dictionary.py` (único propietario) | servidor efímero `LocalServer` puerto 0 | Contrato en el cable, cabeceras, corte inválido, host prohibido, rutas de trading cerradas | 13 pruebas del módulo OK |
| Regresión | sin escritura | suite completa del proyecto | verificación de no regresión | `unittest discover` OK |

Trabajo paralelo de otras sesiones, sin solape de archivos con esta fase:
Fase 6 → `app.js`, `index.html`, `style.css`, `test_ict3_ui_contract.py`;
Fase 7 → `ict3_oos.py`, `test_ict3_oos.py`, `FASE_07_PROTOCOLO_OOS.md`.
`ict.py`, `smc.py` e `ict3_confirm.py` quedaron en solo lectura: no se modificaron.

## 2. Resumen

Se cerró el contrato del bloque `ict3` sin cambiar el payload del servidor.
`ict3_contract.py` es la fuente única de verdad: declara tipo, nulabilidad,
unidad, procedencia y significado de cada campo; valida bloques completos; y
clasifica la espera en `SIN_RETEST`, `DATOS_AUSENTES`, `EVIDENCIA_INSUFICIENTE`
o `SIN_ESPERA`. El diccionario markdown se genera desde `describe()`, de modo
que no puede divergir del código.

Contrato `1.0`, esquema `0.2-research`, modo `OBSERVE_ONLY_NO_ORDER`.
Campos documentados: `ict3` 4, evento 34, `load` 6, cobertura 5, transición 4,
liquidez 3. Claves prohibidas: `entry`, `order`, `fill`, `lots`, `volume`, `pnl`,
`position`, `cash_value`, `balance`, `equity`, `margin`, `ticket`, `deal`.

Decisiones de contrato que eliminan ambigüedad para un consumidor nuevo:

- El subobjeto de confirmación M5/M1 es todo-o-nada: ausente si el evento nunca
  alcanzó `RETESTING_POI`; completo en caso contrario.
- `primary_poi` admite el objeto actual o el identificador de zona heredado,
  porque ambos aparecen en payloads legítimos del servidor y de pruebas.
- `load_reason` describe la carga de marcos inferiores; `wait_reason` describe
  la evidencia pendiente de la idea. No se mezclan.
- `ict3_breaks` se conserva íntegro para los clientes actuales.

## 3. Archivos y funciones

| Archivo | Funciones / símbolos |
|---|---|
| `ict3_contract.py` (nuevo) | `Field`, `describe`, `validate`, `assert_valid`, `classify_wait`, `CONTRACT_VERSION`, `SCHEMA_VERSION`, `MODE`, `FORBIDDEN_KEYS`, `TOP_LEVEL`, `EVENT`, `LOAD`, `COVERAGE`, `TRANSITION`, `LIQUIDITY`, `CATALOG`, `CONFIRMATION_FIELDS`, `LEGACY_BREAK_FIELDS`, `WAIT_CASES` |
| `test_ict3_contract_dictionary.py` (nuevo) | `ContractDictionaryTests` (6 pruebas), `WireContractTests` (3 pruebas), `complete_event` |
| `docs/ict3/CONTRATO_ICT3_DICCIONARIO.md` (nuevo) | diccionario generado, reglas de lectura, campos heredados, casos de espera |
| `docs/ict3/INFORME_FASE_05_CONTRATO_SERVIDOR.md` (este archivo) | informe único de la fase |

No se modificaron archivos de producción.

## 4. Comandos, pruebas y resultado

```bash
cd C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0
.venv/Scripts/python.exe -m unittest -v test_ict3_contract_dictionary
# Ran 13 tests — OK  (9 propios del módulo + 4 importados de test_ict3_contract)

.venv/Scripts/python.exe -m unittest -v test_ict3_ui_contract
# Ran 13 tests — OK (skipped=2)  [trabajo paralelo de Fase 6]

.venv/Scripts/python.exe -m unittest -v test_ict3_oos
# Ran 18 tests — OK  [trabajo paralelo de Fase 7]

.venv/Scripts/python.exe -m unittest -v test_ict3_schema
# Ran 10 tests — OK  [verificación de esquema de otro agente en paralelo]

.venv/Scripts/python.exe -m unittest discover -v
# Ran 161 tests — OK (skipped=1)
```

Casos cubiertos por las 9 pruebas propias: integridad y serialización del
catálogo; payload observable válido; ausencia de subobjeto de confirmación sin
retest; tres clases de espera distinguibles; rechazo del validador ante
`entry_authorized=true`, tipo inválido, clave prohibida e instante posterior al
corte; conservación de `ict3_breaks`; cable HTTP con cabeceras `no-store` y
`nosniff`; corte inválido (400); host prohibido (403); rutas `/api/trade`,
`/api/order`, `/api/position`, `/api/fill` inexistentes (404).

El único salto pertenece a Fase 6: el gancho por etapa
`data-ict3-state`/`data-ict3-time`/`data-ict3-reason` todavía no está
publicado. No es un fallo de esta fase y queda como pendiente explícito.
La verificación de esquema añadida por otro agente en paralelo
(`test_ict3_schema.py`, `docs/ict3/FASE_05_DICCIONARIO_CAMPOS.md`) corrobora
los mismos invariantes desde payloads reales del pipeline, sin importar
`ict3_contract.py`.

## 5. Payload y evidencia

Ejecución real con velas sintéticas declaradas, corte `1003800` salvo el caso
de evidencia insuficiente (`1000800`). Resumen de los cinco estados probados:

| Caso | Clase | `current_state` | `load_reason` | `pending_evidence` | `entry_authorized` |
|---|---|---|---|---|---|
| sin retest | SIN_RETEST | `ACCEPTED_BREAK_WAIT_RETEST` | `NOT_REQUESTED_NO_M15_RETEST` | `M5_M1_CONFIRMATION_NOT_LOADED; STRUCTURAL_STOP_NOT_DEFINED` | false |
| sin velas M5 | DATOS_AUSENTES | `RETESTING_POI` | `NO_CLOSED_M5_BARS_AT_CUTOFF` | `M5_M1_CONFIRMATION_NOT_LOADED` | false |
| retest incompleto | DATOS_AUSENTES | `RETESTING_POI` | `M5_M1_LOADED` | `M5_M1_CONFIRMATION_NOT_LOADED` | false |
| M5/M1 cargados sin estructura | EVIDENCIA_INSUFICIENTE | `RETESTING_POI` | `M5_M1_LOADED` | `M5_STRUCTURE_NOT_CONFIRMED; M5_M1_CONFIRMATION_NOT_COMPLETE` | false |
| evidencia completa | SIN_ESPERA | `OBSERVABLE_SETUP` | `M5_M1_LOADED` | `[]` / `OBSERVATION_ONLY` | false |

Evidencia adicional en vivo (Fase 8, solo lectura): `GET
/api/ict?symbol=EURUSD&tf=M15` en `127.0.0.1:8766` devolvió
`schema_version=0.2-research`, `mode=OBSERVE_ONLY_NO_ORDER`, 5 eventos `ict3`,
10 eventos `ict3_breaks`, `load_reason=NOT_REQUESTED_NO_M15_RETEST`. Al validar
ese bloque con `ict3_contract.validate(block, cutoff=asof)` el resultado fue
`issues: []` y `classify_wait` = `SIN_RETEST`.

## 6. Supuestos

- El contrato describe el bloque después de `attach_confirmations`, que es lo
  que entregó siempre `GET /api/ict`; `ict3_payload` solo produce la base.
- Las velas de prueba son sintéticas y sirven para verificar tipo, causalidad y
  contrato, no para afirmar un estado de mercado real.
- Se conserva la compatibilidad: no se renombró ni eliminó ningún campo y no
  se añadió una ruta HTTP nueva.

## 7. Riesgos, pendientes y bloqueos

- Fase 6: dos pruebas de ganchos por etapa siguen omitidas; la vista explicable
  queda verificada solo a nivel de vocabulario. Depende del agente de
  presentación, no de este contrato.
- Fase 7: la cobertura real sigue marcada `REAL_COVERAGE_PENDING` hasta que se
  entregue un dataset verificable; los conteos actuales son sintéticos
  declarados y no son ventaja estadística.
- El validador comprueba forma y instantes, no la verdad económica de un pivote;
  la causalidad sustantiva la cubren las pruebas de las fases 1 a 4.
- No se conectó a MT5 con credenciales ni se ejecutó ninguna orden.

## 8. Confirmación de solo lectura

No se crearon órdenes, posiciones, tickets, fills, lotaje, volumen, P&L ni
movimientos de cuenta. No se leyó ni modificó ningún archivo de `data/`, ni
credenciales. No se añadió ningún endpoint de trading. `entry_authorized` sigue
siendo `false` y `mode` `OBSERVE_ONLY_NO_ORDER` en todos los payloads
verificados. El puente permaneció en modo trabajo (`active=true`) durante todo
el encargo y no se consultó `/api/inbox`.
