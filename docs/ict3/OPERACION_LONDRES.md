# Operación del snapshot ICT 3.0 de Londres +15m

## Estado P0 (diagnóstico real)

`READY`. El 2026-11-23 se verificó con ejecución real:

- Repositorio `vjack666/SMC3.0`, rama `main`, motor `ict.REVISION = f453bf2a…` coherente con la
  fuente ICT 2.0 anclada. El repositorio local se actualizó a `origin/main` antes de trabajar.
- MT5 conectado, terminal operativa, 33 símbolos del catálogo con velas D1/H4/H1/M15/M5/M1.
- **Reloj del broker: +7200 s respecto a UTC** (tick 19:54Z frente a 17:54Z del sistema).
- `ict_chart` solo es causal si se le pasa un `cutoff` explícito en el reloj MT5. El valor de
  `result['asof']` también está en ese reloj y debe convertirse a UTC restando el offset.
- La publicación usa el token ya almacenado en el administrador de credenciales de Windows;
  no se imprime ni se guarda en el repositorio.
- El proceso corre sin navegador ni interfaz web. Requiere la terminal MT5 abierta y sesión activa.

## Horarios verificados con IANA `zoneinfo`

| Temporada | 08:15 Europe/London | UTC | America/Guayaquil |
|---|---|---|---|
| GMT (invierno) | 08:15+00:00 | 08:15Z | 03:15-05:00 |
| BST (verano) | 08:15+01:00 | 07:15Z | 02:15-05:00 |

El plan publicado es correcto en este punto. El disparador local usa dos horas (02:20 y 03:20
Guayaquil) y `run_daily.py` decide cuál cumple 08:15 Londres; no hay UTC fijo.

## Ejecución manual

```bash
cd C:\Users\v_jac\Desktop\MT5-POI-Compartido\SMC3.0
.venv\Scripts\python.exe tools\london\run_daily.py --repo . --date 2026-11-23 --no-publish
.venv\Scripts\python.exe tools\london\run_daily.py --repo . --date 2026-11-23
```

Sin `--no-publish`: valida → commit/push del snapshot → verificación remota → `latest.json`.

## Automatización

`tools\london\registrar_londres.cmd` crea las tareas `ICT3_Londres_0815_BST` (02:20) e
`ICT3_Londres_0815_GMT` (03:20), hora America/Guayaquil. No modifica la tarea de 07:45 Ecuador.
Cada tarea llama a `ejecutar_londres.cmd`, que escribe `data/londres_run.log` sin credenciales.

## Fallos conocidos y recuperación

- MT5 cerrado o sin sesión: no se publica; `latest.json` conserva la fecha anterior y debe leerse
  como **PENDIENTE DE SNAPSHOT NUEVO**.
- `STALE_FEED`, símbolo ausente o festivo: se registran en `freshness_report.json` y en
  `symbols_stale` / `symbols_unavailable`; no se inventan velas.
- Push o verificación remota fallidos: `BLOCKED`, sin actualizar `latest.json`.
- `BAR_COUNT=550` limita la ventana HTF del motor en vivo; el histórico Dukascopy de 20 años sigue
  desconectado y con discrepancias SHA-256 documentadas. No se afirma vigencia de POI antiguo sin
  evidencia de mitigaciones intermedias.
- El motor no expone lifecycle por zona ni liquidez semanal/mensual como campos nativos; esos
  conceptos se marcan `NOT_EXPOSED`, nunca se inventan.

## Invariantes

`OBSERVE_ONLY_NO_ORDER`, `entry_authorized=false`, sin órdenes, sin P&L, sin credenciales ni datos
de cuenta en los artefactos publicados. Los 32 tests de `tools/london/tests/` cubren no look-ahead,
semántica de vela, idempotencia, privacidad, hashes, DST y modos de fallo.
