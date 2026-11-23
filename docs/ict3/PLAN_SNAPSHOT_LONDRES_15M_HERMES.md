# Plan de trabajo — Snapshot ICT 3.0 de Londres +15m para lectura IA

**Estado:** PLANIFICADO / NO IMPLEMENTADO  
**Solicitante:** propietario de ICT 3.0  
**Ejecutor técnico propuesto:** Hermes (en el equipo Windows con MT5 y el repositorio local)  
**Consumidor:** ChatGPT, informe `Londres +15m · ICT 3.0 y macro` de la página [Seguimiento diario de trading y contexto macroeconómico](https://chatgpt.com/space/page_c3fe3eea801c8191ae870fddf5f2ee09)  
**Repositorio canónico:** `vjack666/SMC3.0` / rama `main`  
**Fecha del plan:** 2026-11-23

> Este documento es un plan de implementación, **no** un snapshot nuevo ni prueba de ejecución. No activa trading, no modifica tareas de ChatGPT y no acredita que haya datos actuales disponibles.

## 0. Problema comprobado y fuentes de verdad

- Exportación forense existente: [`reports/ict3_ai_analysis/`](../../reports/ict3_ai_analysis/README.md), con [manifiesto](../../reports/ict3_ai_analysis/manifest.json), [snapshot global](../../reports/ict3_ai_analysis/snapshot_global.md) y [calidad de datos](../../reports/ict3_ai_analysis/data_quality.md).
- El manifiesto existente registra generación **2026-11-22 20:59:42 UTC**, 33 instrumentos (26 pares Forex y otros 7 índices/materias primas), y motor en modo `OBSERVE_ONLY_NO_ORDER`. El `asof` de la mayoría de instrumentos es **2026-11-20 23:45 UTC**; es referencia histórica, **no** lectura de Londres del 23/11.
- Actualmente `ict.read_bars` solicita `BAR_COUNT + 1 = 551` velas y `closed_frame` descarta la vela 0. Perfil ordinario: `D1, H4, H1, M15`; M5/M1 solo bajo condiciones de confirmación. Los datos de mayor antigüedad del dataset Dukascopy publicado no están integrados al motor en vivo.
- En `data_quality.md` se advierten discrepancias SHA-256 del dataset Dukascopy y ausencia de SQL en esta copia; no utilizarlas silenciosamente como prueba de cobertura válida.
- El [mapa de capacidades](../../reports/ict3_ai_analysis/motor_capabilities.md) identifica `ict_chart` como productor real, el bloqueo de frescura MT5 de Fase 8 y la ausencia de un estado lifecycle completo por zona en los JSON públicos. No atribuir al motor lo que todavía no expone.
- `ict2.0` es fuente de autoridad conceptual fijada por revisión; **no** debe sustituir como repositorio de resultados a `SMC3.0`.

## 1. Objetivo operativo, horario y dependencia

**Objetivo:** para cada día hábil de mercado, conseguir que Hermes extraiga las velas *cerradas* disponibles al corte **08:15 Europe/London**, evalúe el motor ICT 3.0 sin operar, publique un paquete verificable en GitHub y permita a ChatGPT contrastarlo con macroeconomía y noticias con timestamps explícitos.

- Apertura de referencia: **08:00 Europe/London**; corte técnico: **08:15 Europe/London**.
- Equivalencia Ecuador: **03:15 America/Guayaquil** en invierno británico (GMT); **02:15 America/Guayaquil** en verano británico (BST). Configurar el disparador con zona `Europe/London`, **no** con UTC fijo.
- Ejecutar captura en/tras 08:15, con unos minutos de gracia para cierre/entrega de la M15 08:00–08:15. No alterar retrospectivamente el corte ni usar barras posteriores.
- **No confundir las horas:** `snapshot_cutoff_at` (08:15), `collected_at` (obtención real), `generated_at` (exportación), `published_at` (GitHub), `macro_observed_at` (lectura de noticias).
- Dependencia obligatoria: PC/sesión MT5 y permisos de GitHub realmente disponibles. GitHub por sí mismo **no** accede a `127.0.0.1:8766` ni a una terminal MT5 local.
- La tarea de ChatGPT `Seguimiento matutino de trading` de **07:45 America/Guayaquil** permanece **sin modificaciones**. No alterar tampoco la automatización adicional de Londres sin autorización. Si ChatGPT ejecuta antes del push, debe mostrar **PENDIENTE DE SNAPSHOT NUEVO**, nunca inventar una lectura fresca.

## 2. Entregables y fases de trabajo

### Fase P0 — Confirmar ejecución real y contrato (bloqueante)

- [ ] Inventariar máquina, repo local, rama, `HEAD`, versión del motor, fuente de velas MT5, símbolos disponibles y horario del broker.
- [ ] Revisar la ruta de llamada `ict_chart(settings, symbol, frame, cutoff)`, su semántica de `asof`, `latest_closed` y `last_closed_by_tf`, caché y dependencia de `BAR_COUNT`.
- [ ] Documentar si los timestamps del feed representan apertura o cierre de cada vela. Normalizar a UTC **y** almacenar reloj original; nunca asumir automáticamente que `asof` es la hora de cierre.
- [ ] Verificar que el proceso puede iniciar/salir sin interfaz web ni acción manual; si requiere MT5 abierto, declararlo expresamente.
- [ ] Comprobar credenciales de publicación sin exponer tokens, login, número de cuenta, saldos o rutas personales.
- [ ] Publicar un diagnóstico: `READY` o `BLOCKED`, con razones y pruebas. Sin `READY`, no pasar a programación.

### Fase P1 — Captura causal de velas cerradas y cobertura real

- [ ] Definir corte único `2026-... 08:15 Europe/London` por día y transformarlo con biblioteca de zonas IANA (incluye cambios BST/GMT).
- [ ] Capturar el estado de **todos los instrumentos realmente habilitados**; referencia inicial 33, sin prometer BTC si el catálogo/feed no lo contiene.
- [ ] Mantener D1/H4/H1/M15, documentar M5/M1 solo si el motor efectivamente los carga; W1/MN1 solo como contexto si hay datos y procedimiento verificado.
- [ ] Para la M15 de apertura exigir, cuando el mercado cotice y el proveedor la entregue, vela `open=08:00` / `close=08:15 Europe/London`. El cálculo puede comenzar después de 08:15, pero no incorporar a la inferencia ninguna vela cerrada *después* de ese corte.
- [ ] Aplicar validación OHLC, monotonicidad, duplicados, spreads si disponibles, lag, gaps, DST, cierres de sesión, fines de semana y festivos por instrumento.
- [ ] Registrar `last_bar_open_utc`, `last_bar_close_utc`, `bars_count`, `oldest_bar_utc`, `feed_source` y `freshness_status` por instrumento/TF. Para D1/H4/H1 aplicar el calendario real de cierres; no marcarlos obsoletos solo porque su última vela cerró antes de 08:15.
- [ ] Si la M15 requerida no está, reportar `STALE_FEED`, `MARKET_CLOSED`, `PARTIAL_FEED` o `ERROR` con evidencia; **nunca** usar el viernes como snapshot actual de lunes.

### Fase P2 — Reanálisis ICT con jerarquía HTF → LTF

- [ ] Ejecutar exclusivamente productores reales de `SMC3.0` bajo el corte causal; no montar un segundo motor narrativo ni cambiar el modo `OBSERVE_ONLY_NO_ORDER`.
- [ ] Conservar por par: régimen D1/H4/H1/M15, swings, BOS/CHoCH/MSS cuando el motor los expone, liquidez (PDH/PDL, viernes, barridos con mecha/cierre), eventos y transiciones, POI, candidatos y razones de espera/invalidación.
- [ ] De cada POI: ID estable, tipo OB/FVG/etc., `origin_tf`, fecha real de nacimiento, extremos de precio, relación HTF–LTF, primera mitigación, confirmaciones, estado realmente expuesto, y evidencia/código fuente. Si el motor no entrega ACTIVE/PARTIAL/MITIGATED/INVALIDATED por zona, **no inventar lifecycle**: dejar `NOT_EXPOSED` y abrir mejora específica.
- [ ] Agregar PWH/PWL, PMH/PML, HOD/LOD, sesiones, BSL/SSL, EQ y premium/discount **solo** si existen como salidas verificables. Si se derivan por un nuevo adaptador de OHLC, registrar `derived_from_ohlc`, fórmula, anclaje de sesión, temporalidad y límites; **no** atribuirlos a salida nativa del motor.
- [ ] No poner límite temporal arbitrario de un mes. Diagnosticar el impacto de `BAR_COUNT=550`: usar historia HTF suficiente y, en fase independiente, estudiar histórico ampliado/replay causal sin sobreescribir resultados anteriores. Primero reconciliar cobertura y hashes del dataset adicional. No declarar POI histórico vigente si falta evidencia de todas las mitigaciones intermedias.
- [ ] Separar lo **observado** del **escenario en observación**, y de **señal confirmada** (si el motor la expone). Un toque en POI no habilita ejecución.

### Fase P3 — Exportación IA y publicación ligera, inmutable e idempotente

Nueva ruta propuesta, separada de la exportación forense original:

```text
reports/ict3_london/
  README.md
  latest.json                     # solo apunta al último snapshot validado
  snapshots/YYYY-MM-DD/
    london_0815/
      manifest.json
      snapshot_global.md
      data_quality.json
      validation.json
      instruments/
        EURUSD/
          analysis.json
          analysis.md
          poi.json
          liquidity.json
          events.json
          chart_objects.json
        ... resto del catálogo evaluado
```

- [ ] Reutilizar/refactorizar el exportador [`evidence/export_script.py`](../../reports/ict3_ai_analysis/evidence/export_script.py) sin alterar el motor y eliminando dependencia rígida de rutas locales.
- [ ] Para cada ejecución escribir `snapshot_id`, `snapshot_cutoff_utc`, `snapshot_cutoff_london`, `snapshot_cutoff_guayaquil`, `generated_at_utc`, `engine_revision`, `schema_version`, `source_repository`, `provider`, `coverage_by_symbol_tf`, `freshness_by_symbol_tf`, listas de símbolos `exported/stale/unavailable`, SHA-256, bytes y estado de pruebas.
- [ ] Mantener inmutables los snapshots fechados. Reintento del mismo corte: si el contenido coincide, no duplicar commits; si difiere, nueva revisión identificada con causa, sin sobrescribir en silencio.
- [ ] Optimizar tamaño: **no publicar 80 MB de evidencia raw en cada sesión** salvo justificación. Publicar datos compactos y referencias/checksums al histórico o artefactos autorizados. Validar cuotas/límites de GitHub y política de distribución del proveedor.
- [ ] Tras validación local, hacer `commit` + `push` en rama aprobada, comprobar lectura remota del `manifest.json` y al menos varios instrumentos; actualizar `latest.json` **únicamente** tras publicación válida. Guardar SHA del commit de publicación en logs/enlace externo, evitando referencia circular al propio commit dentro del archivo que se publica.
- [ ] Incluir un `README.md` de interpretación de datos para IA y links al manifiesto/evidencia. Mantener intacto `reports/ict3_ai_analysis/` como base histórica hasta decidir formalmente su rotación.
- [ ] Si falla captura, pruebas o push, mantener `latest.json` apuntando al último éxito **con su fecha antigua claramente visible** y publicar/notificar estado `BLOCKED`; nunca etiquetar datos viejos como nuevos.

### Fase P4 — Handoff a ChatGPT y macro del mismo corte

- [ ] Consumidor busca `reports/ict3_london/latest.json` en `vjack666/SMC3.0`, sigue ruta de snapshot y verifica `manifest.json`, hashes, commit, cobertura, frescura por TF y coincidencia con fecha de Londres esperada.
- [ ] Contrastar POI, estructura y eventos de GitHub con fuentes macro públicas fechadas: calendarios alto impacto, sorpresas dato-consenso, Fed/BCE/BoE/BoJ/SNB/BoC/RBA/RBNZ según pares, DXY, bonos, oro, petróleo e índices.
- [ ] Cualquier noticia posterior a `snapshot_cutoff_at` se debe etiquetar como **actualización posterior**, no como información disponible para justificar el estado técnico al corte. Guardar `macro_observed_at` y enlaces.
- [ ] Matriz por instrumento con D1/H4, POI (tipo/TF de origen/edad/precio/estado), liquidez barrida y pendiente, calidad de feed, apoyo/contradicción macro. Hasta **3 escenarios en observación**, con invalidación, catalizadores y riesgo correlacionado; **nunca** órdenes ni resultados ficticios.
- [ ] Publicar solo en la sección `Reportes diarios` de la página con título `Londres +15m · ICT 3.0 y macro · YYYY-MM-DD`. Preservar entradas anteriores; separar MT5/FundedNext, TradingView simulado y Pocket Option, sin crear operaciones.
- [ ] No modificar la tarea independiente `Seguimiento matutino de trading` de 07:45 Ecuador. Resolver primero dependencia de publicación: si a las 08:15 Londres todavía no hay push, la tarea reportará **PENDIENTE DE SNAPSHOT NUEVO** y no rellenará con datos viejos. Cualquier ajuste de horario de la tarea requerirá aprobación aparte.

### Fase P5 — Pruebas y operación continua

- [ ] Prueba manual con terminal MT5 real y log de ejecución sin información sensible.
- [ ] Test de *no look-ahead*: ninguna vela con `close > snapshot_cutoff` alimenta el cálculo.
- [ ] Test de semántica de vela (apertura vs cierre), idempotencia, caídas de MT5, símbolo faltante, mercado festivo, GitHub sin permisos, manifiesto inválido, checksum roto y `latest.json` antiguo.
- [ ] Test BST ↔ GMT con fechas de cambio de horario: 08:15 Londres debe corresponder a 02:15/03:15 Guayaquil correctamente.
- [ ] Test de invariantes: `OBSERVE_ONLY_NO_ORDER`, `entry_authorized=false`, sin operaciones, sin actualización de P&L, sin credenciales y sin logs de identidad de cuenta.
- [ ] Reconciliar muestra representativa contra OHLC fuente, salida `ict_chart` y objetos de los JSON publicados. Verificar que `poi_id`, `event_id`, timestamps y referencias cruzadas sean estables.
- [ ] Ejecutar al menos una sesión piloto con evidencia de publicación y lectura desde GitHub; registrar fallos y plan de recuperación.

## 3. Criterios de aceptación (Definition of Done)

Se considera **HECHO** solo cuando todos estos puntos sean demostrables:

1. Captura real **posterior al cierre M15 de las 08:15 Europe/London**, con corte causal exacto y correctamente convertido a Ecuador; evidencia de disponibilidad y frescura por símbolo/TF.
2. Todos los símbolos disponibles se procesan; los ausentes o atrasados figuran explícitamente, incluido BTC si sigue fuera del catálogo.
3. Se publica un snapshot **nuevo, fechado y legible remotamente**, con URL, rama, commit SHA, manifiesto válido, checksums y separación entre datos nativos/derivados.
4. Se conservan los POI HTF históricos respaldados por cobertura real; no se afirman antigüedades, estados de mitigación ni validez fuera de la evidencia.
5. ChatGPT puede elaborar el análisis ICT+macro vinculando **el mismo corte temporal** y marcar datos/noticias fuera de corte; si no hay snapshot nuevo, **se bloquea la lectura actual**.
6. No se toca la tarea de 07:45 Ecuador ni se envía operación alguna. `OBSERVE_ONLY_NO_ORDER` permanece invariable.
7. Hermes entrega pruebas de ensayo, comandos reproducibles, fallos conocidos, enlace al PR/commit final y ruta exacta de `latest.json`.

## 4. Orden recomendado y bloqueos prioritarios

**Primero:** P0 + P1 (frescura/cierre real) → **Segundo:** P2 (análisis causal y límites históricos) → **Tercero:** P3 (exportación GitHub) → **Cuarto:** P4 (consumo por ChatGPT) → **Quinto:** P5 (prueba end-to-end y operación).

**Bloqueadores conocidos:** dependencia del terminal local MT5 y su sesión, Fase 8 previamente documentada como pendiente de frescura, `BAR_COUNT=550`, histórico Dukascopy desconectado con hashes discrepantes, lifecycle por POI no expuesto como campo independiente, y posible desfase entre hora de corte y hora real de publicación.

**No hacer:** asignar `READY` sin pruebas, inventar velas/POI, usar `ict2.0` o `SMC-SYSTEMS` como snapshot sustitutivo, mezclar datos privados con GitHub público, alterar tareas existentes, atribuir a la macro un evento técnico posterior o ejecutar órdenes.

---

**Solicitud a Hermes:** implementar en PRs pequeños, mantener una bitácora de evidencias por fase y pedir revisión antes de habilitar recurrencia. El plan aquí publicado no concede por sí mismo autorización para modificar el motor ni para operar.
