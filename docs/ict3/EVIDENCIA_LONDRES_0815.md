# Evidencia de ejecución real — Londres +15m · 2026-11-23

## P0 — diagnóstico (READY)

- Repositorio `vjack666/SMC3.0`, rama `main`; motor `ict.REVISION = f453bf2a…` coincidente con la
  fuente ICT 2.0 anclada. El repositorio local se actualizó a `origin/main` antes de cualquier cambio.
- MT5 conectado (MetaTrader 5, build 6325), 33 símbolos del catálogo con datos D1/H4/H1/M15/M5/M1.
- **Reloj del broker: +7200 s** respecto a UTC. Medición en vivo: tick `19:54:04Z` frente a
  sistema `17:54:04Z`; `offset_seconds_raw=7199`, redondeado a 7200 sobre rejilla horaria.
- `result['asof']`, `latest_closed` y `last_closed_by_tf` están en reloj MT5. Se publican tal cual
  **y** con su equivalente `asof_real_utc = valor − 7200`.
- Sin navegador: el motor se ejecutó desde `.venv\Scripts\python.exe` con la terminal MT5 abierta.

## Corte y vela real

- `snapshot_cutoff_utc = 2026-11-23T08:15:00Z` (08:15 Europe/London, GMT) = `03:15` en
  America/Guayaquil.
- `engine_cutoff = 1795428900` (10:15 en espacio MT5 = 08:15 real).
- Última M15 cerrada: abierta `1795428000` (10:00 MT5 = 08:00 London real), OHLC real
  `O 1.09973 / H 1.09985 / L 1.09907 / C 1.09941`. Con el corte UTC naive se obtenía una barra
  dos horas anterior: por eso el offset es obligatorio.
- DST verificado con `zoneinfo`: GMT → 03:15 Guayaquil; BST → 02:15 Guayaquil. El plan es correcto.

## Snapshot publicado

- `snapshot_id`: `london0815_20261123_1795421700_c25e4c199a`
- Ruta: `reports/ict3_london/snapshots/2026-11-23/london_0815/`
- Commit de publicación: `bd691df2472b31402b14163c12caa5c06e5d2526`
- Instrumentos: **33 exportados**, 0 stale, 0 unavailable.
- Archivos: **202**, ~23,31 MB, JSON compacto, sin volcados OHLC crudos.
- Modo del motor: `OBSERVE_ONLY_NO_ORDER`; `entry_authorized=false` en todos los eventos.
- `freshness_report.json`: offset medido 7200 de fuente `max_last_tick_time`; estados
  `FRESH` y `PARTIAL_FEED` documentados, sin velas inventadas.
- Verificación remota: **202/202 archivos** recuperados por `raw.githubusercontent.com` fijado al
  commit, SHA-256 y bytes coincidentes, cero errores.

## Pruebas

- Exportador: 7/7 tests (idempotencia, contrato de manifiesto, `latest.json` solo tras validar,
  modo y autorización preservados, sin lifecycle inventado).
- Invariantes P5: **32/32 tests** (no look-ahead, semántica de vela, idempotencia, privacidad,
  hashes LF, DST, modos de fallo).
- Frescura y horarios: suites de los módulos propias, todas en verde.
- Validación del bundle: **PASS** (9/9 checks).

## Fallos detectados y corregidos

1. El primer piloto usó 20 MB como umbral de "compacto" con JSON indentado (35,8 MB) → FAIL.
   Se compactó JSON sin quitar campos (−32 %) y se fijó el umbral en 25 MB con justificación.
2. El primer orquestador pasó `clock_source="max_last_tick_time"`, valor no reconocido que
   desactivaba la medición y dejaba offset 0 → snapshot dos horas atrasado. Se cambió a `ticks` y
   se añadió una salvaguarda que bloquea la publicación si el offset mide 0 sin confirmación.
3. La verificación usaba la API de GitHub y recibió HTTP 403 por rate limit → se cambió a raw por
   SHA, sin límite y sin caché de `main`.
4. La verificación buscaba `README.md` dentro del snapshot → 404. Se cambió a `snapshot_global.md`.

Tras las correcciones, `latest.json` se escribió únicamente con la verificación remota en verde.

## Automatización

Dos tareas locales en hora America/Guayaquil: `ICT3_Londres_0815_BST` (02:20) e
`ICT3_Londres_0815_GMT` (03:20). `run_daily.py` comprueba la hora real de Londres con IANA y decide
cuál disparador es válido; el otro termina sin publicar. La tarea de 07:45 Ecuador no se modifica.
