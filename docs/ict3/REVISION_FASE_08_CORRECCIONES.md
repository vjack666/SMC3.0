# Revisión Fase 8 — pendientes obligatorios de cierre

## Resultado de la revisión

La suite local pasa 161/161 y la prueba de contrato de interfaz pasa 13/13.
Los endpoints de lectura responden y el modo sigue siendo
`OBSERVE_ONLY_NO_ORDER`. La Fase 8 todavía no puede marcarse como aceptada
porque el propio release registra dos verificaciones pendientes.

## Correcciones requeridas

1. **Frescura MT5.** Mantener `state=stale` y `REAL_COVERAGE_PENDING` como
   estado pendiente. Cuando exista una cotización reciente autorizada,
   repetir EURUSD, GBPJPY y US30 y registrar cierre M15, último tick, errores,
   cantidad de eventos, `schema_version`, `mode` y `entry_authorized`. No
   inventar datos ni forzar credenciales. Si MT5 sigue inaccesible, entregar un
   bloqueo explícito con la última hora observada y no declarar cobertura viva.
2. **Semántica `cutoff=asof` de US30.** Aislar las cuatro incidencias de
   `ict3_contract.validate` y demostrar si son un problema de contrato o de
   datos posteriores al corte. Añadir una prueba que exija que todo
   `observed_at`, `last_closed_m5`, `last_closed_m1` y liquidez sea `<= cutoff`,
   o documentar con precisión por qué el contrato permite esos campos. La
   salida debe ser 0 incidencias para un payload histórico válido.
3. **Interfaz interactiva.** Verificar el render de las ocho etapas y la
   selección de activos con un harness aislado o una sesión controlada que no
   ejecute el `POST /api/sync` ni escriba `data/`. La prueba estática 13/13 no
   sustituye esta verificación. Registrar las etapas visibles, estado, hora y
   motivo, junto con errores de carga.
4. **Release.** Actualizar `RELEASE_FASE_08.md` y el plan principal para que
   `[~]` permanezca mientras exista cualquiera de estos pendientes. Solo pasar
   a `[x]` cuando haya evidencia de los tres puntos y la reversión siga
   documentada.

## Entrega

Ejecutar la suite completa, Graphify y un informe final con comandos, resultados,
cobertura real, limitaciones y confirmación de solo lectura. Cerrar el puente
con `active=false` y responder `terminé el trabajo`.

## Resultado de la corrección (2026-11-22T17:00Z)

- Punto 1: **bloqueo entregado**. `state=stale` y `REAL_COVERAGE_PENDING` se
  mantienen; último cierre M15 `2026-11-20T23:45:00Z` (`1795218300`), consulta
  `2026-11-22T16:51:45Z`. Sin cotización autorizada no se declara cobertura viva.
- Punto 2: **resuelto**. 4 incidencias aisladas (2 `liquidez.observed_at`,
  `load.last_closed_m5`, `load.last_closed_m1`); regla de los dos relojes
  documentada en `CUTOFF_ASOF_REGLA_CAUSAL.md` y en la docstring de
  `ict3_contract.validate`; `test_ict3_cutoff_asof.py` 3/3 OK con 0 incidencias
  para un payload histórico válido. El validador no cambió de comportamiento.
- Punto 3: **resuelto**. Render interactivo en harness aislado: 3 activos ×
  7 expedientes × 8 etapas, con estado/hora/motivo. Único `POST /api/sync`
  interceptado localmente; cero POST reales.
- Punto 4: Fase 8 permanece `[~]` en `RELEASE_FASE_08.md` §8 y en
  `PLAN_HERMES_REVISION_IA.md`; solo `[x]` con evidencia de los tres puntos.
