# ICT 3.0 · Snapshot de Londres +15m

Este paquete publica, para cada día hábil, el estado observable del motor ICT 3.0 al corte de
las **08:15 Europe/London**. Su destinatario es una IA que debe reconstruir el gráfico y
contrastarlo con macroeconomía con timestamps explícitos.

## Punto de entrada

- `latest.json`: **único** puntero válido al último snapshot verificado. Si falta, está antiguo o
  su manifiesto no valida, la lectura actual debe marcarse **PENDIENTE DE SNAPSHOT NUEVO**.
- `snapshots/YYYY-MM-DD/london_0815/manifest.json`: índice inmutable con SHA-256 de cada archivo.
- `snapshots/YYYY-MM-DD/london_0815/instruments/<SÍMBOLO>/`: detalle por instrumento.

## Lectura por instrumento

- Abre primero `snapshot_global.md`: incluye enlaces directos a `analysis.md` por instrumento.
- El JSON detallado se conserva sin eliminar campos. El corte no se publica si la carga compacta alcanza o supera 32.000.000 bytes.

## Reglas de lectura

1. Verificar `latest.json` → seguir `manifest` → comprobar `cutoff`, `london_date` y que el commit
   publicado existe. No usar un snapshot fechado distinto al del día esperado.
2. `snapshot_cutoff_utc` es el corte real. Los campos `*_engine_utc` están en el reloj codificado
   de MT5; `broker_clock_offset_seconds` permite convertirlos (real UTC = engine − offset).
3. Toda noticia macro con `macro_observed_at` posterior al corte es **actualización posterior**,
   nunca información disponible para justificar el estado técnico al corte.
4. El motor permanece en `OBSERVE_ONLY_NO_ORDER` y `entry_authorized=false`. Un toque en POI no
   habilita ejecución. No hay lifecycle inventado por zona.
5. `freshness_report.json` y `data_quality.json` documentan cobertura real; D1/H4/H1 tienen
   calendario de cierre propio y no se marcan obsoletos por cerrar antes de 08:15.

## Reproducción

```bash
.venv/Scripts/python.exe tools/london/run_daily.py --repo . --date YYYY-MM-DD --no-publish
.venv/Scripts/python.exe tools/london/run_daily.py --repo . --date YYYY-MM-DD
```

La segunda forma valida, hace commit y push del snapshot, verifica la lectura remota y solo
entonces actualiza `latest.json`. Requiere terminal MT5 abierta y credenciales de GitHub
disponibles en el administrador de credenciales del sistema.

## Instrucciones de recuperación

- Si falla MT5: el snapshot no se publica; `latest.json` conserva la fecha antigua y debe leerse
  como pendiente, nunca como lectura fresca.
- Si falla el push: se documenta `BLOCKED` con la causa; no se actualiza `latest.json`.
- Si un corte ya publicado se regenera con contenido distinto, se crea una revisión nueva;
  los snapshots fechados no se sobrescriben en silencio.

La tarea independiente `Seguimiento matutino de trading` de las 07:45 America/Guayaquil no se
modifica ni se sustituye por este mecanismo.
