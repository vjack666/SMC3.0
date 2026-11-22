# Informe Fase 8 — Integración y operación del servidor (avance de solo lectura)

**Estado:** integración verificada en local y en el servidor ya en marcha.
No se reinició el servicio, no se conectó con credenciales y no se verificó
frescura de datos de mercado. Queda pendiente la comprobación en vivo con
velas recientes, según se detalla en el apartado 6.

## 1. Responsables y propiedad de escritura

| Papel (Hermes asume el encargo si no hay agente separado) | Archivos autorizados | Resultado | Prueba de aceptación |
|---|---|---|---|
| Preparación | solo lectura de `abrir-smc.cmd`, `smc.py`, `requirements.txt` | ruta de arranque y reversión documentadas | `abrir-smc.cmd` no fuerza reinicio si el puerto 8766 ya responde |
| Verificación | este informe; sin cambios en producción | suite completa + smoke HTTP de lectura | `unittest discover` OK, cabeceras y modos correctos |
| Auditoría final | sin escritura en `data/` | contrato aplicado a payloads reales | `validate()` sin incidencias con el corte correcto |

No se modificó ningún archivo de producción en esta fase. La reversión no
requirió deshacer cambios porque no se activó nada nuevo.

## 2. Comandos y resultado

```bash
cd C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0
.venv/Scripts/python.exe -m unittest discover -v
# Ran 161 tests in ~1.5 s — OK (skipped=1)
```

Suite = 107 pruebas base (Fase 4 aceptada) + 9 de contrato Fase 5 + 10 de
esquema Fase 5 + 13 de interfaz Fase 6 + 18 de OOS Fase 7, más 4 clases
importadas por las pruebas de contrato. El único salto es de Fase 6 y
corresponde a ganchos por etapa aún no publicados; no oculta fallos de las
fases 5 o 7.

## 3. Smoke tests HTTP en el servidor habitual

Servidor: `http://127.0.0.1:8766`, `Host: 127.0.0.1:8766`. No se lanzó una
instancia nueva; se consultó la ya existente. Todas las peticiones son GET.

| Endpoint | Resultado | Evidencia |
|---|---|---|
| `/api/market?symbol=EURUSD&tf=M15` | 200 | `checked_at=2026-11-22T15:41:14Z`, `digits=5`, velas M15 presentes |
| `/api/market-universe` | 200 | inventario devuelto sin error |
| `/api/poi-universe` | 200 | cabeceras `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` |
| `/api/ict?symbol=EURUSD&tf=M15` | 200 | `schema_version=0.2-research`, `mode=OBSERVE_ONLY_NO_ORDER`, 5 eventos `ict3`, 10 `ict3_breaks`, `load_reason=NOT_REQUESTED_NO_M15_RETEST` |
| `/api/ict?symbol=GBPJPY&tf=M15` | 200 | 7 eventos `ict3`, 12 `ict3_breaks`, mismo esquema y modo |
| `/api/ict?symbol=US30&tf=M15` | 200 | 6 eventos `ict3`, 13 `ict3_breaks`, `load_reason=M5_M1_LOADED` |
| `/api/trade`, `/api/order`, `/api/position` | 404 | no existen rutas de ejecución |

Validación del contrato sobre esas respuestas reales:

- EURUSD y GBPJPY: `validate(block, cutoff=asof)` → `[]`.
- US30 con `cutoff=asof` → 4 incidencias de marca temporal (detalle abajo); con
  `cutoff=hora actual` → `[]`. No hay claves prohibidas dentro de `ict3`.
- En los tres payloads, todo evento tiene `entry_authorized=false`.

## 4. Hallazgos de la verificación en vivo

1. **Marca temporal mixta.** `result["asof"]` se ancla al cierre M15 más
   reciente (`2026-11-20T23:45Z`), mientras `attach_confirmations` recibe la
   hora de reloj como `as_of`. En US30 eso produce `last_closed_m5=2026-11-21T00:00Z`,
   `last_closed_m1=2026-11-21T00:01Z` y dos `target_liquidity[].observed_at`
   posteriores a `asof`. El propio código de `ict.py` declara que M1/M5 pueden
   mostrar formaciones cerradas posteriores sin alterar la instantánea diaria;
   por eso no se cambió el comportamiento en esta entrega. La incidencia es de
   semántica de `asof`, no de uso de velas abiertas: con la hora actual como
   corte, todas las marcas son pasadas y el contrato pasa sin incidencias.
   Requiere decisión de alcance (Rubén/GPT) sobre si `asof` debe ser el cierre
   M15 o la hora de reloj para marcos inferiores.
2. **Datos de mercado no frescos.** El último cierre M15 servido es del
   `2026-11-20T23:45Z`, unas 40 horas antes de la consulta
   (`2026-11-22T15:44Z`). El servidor responde, pero el terminal MT5 parece no
   estar aportando velas nuevas en este entorno. No se puede usar esta
   verificación para afirmar cobertura de mercado actual.
3. **`entry` en el legado `book22`.** Las respuestas reales contienen claves
   `book22[].entry` con precios de referencia del modelo del Libro 22 ICT 2.0.
   Están fuera del bloque `ict3`, no son órdenes, lotes ni fills, y son
   anteriores a este trabajo. Dentro de `ict3` no aparece ninguna clave
   prohibida.

## 5. Reversión practicable

El lanzador `abrir-smc.cmd` comprueba el puerto 8766 y solo inicia
`.venv\Scripts\python.exe smc.py serve` si está libre; no mata ni sustituye un
proceso en marcha. Para volver a una versión anterior sin borrar cambios ajenos:

1. Detener únicamente el proceso propio que ejecuta `smc.py serve`.
2. Restaurar desde copia previa los archivos que se hubieran modificado en
   esa activación, uno por uno; no reemplazar `data/`, credenciales ni notas.
3. Volver a iniciar con `abrir-smc.cmd` y repetir los smoke tests del
   apartado 3.
4. Si la interfaz falla pero el motor responde, basta con restaurar
   `index.html`, `app.js` y `style.css`, sin tocar el motor.

En esta entrega no hubo activación que revertir: los cambios son nuevos
módulos y documentación, y el servidor sigue sirviendo el contrato actual.

## 6. Pendientes concretos

- Comprobación en vivo con velas recientes: depende de que MT5 vuelva a
  aportar cierres nuevos. No se usaron credenciales para forzarla.
- Cobertura completa de 26 pares y cuatro índices: solo se sondearon EURUSD,
  GBPJPY y US30. El protocolo OOS de Fase 7 marca la cobertura real como
  `REAL_COVERAGE_PENDING`; no se debe inferir cobertura de esos tres casos.
- Decisión de alcance sobre la semántica de `asof` frente a M5/M1 en vivo.
- Fase 6: dos pruebas de ganchos por etapa sin ejecutar.

## 7. Confirmación de solo lectura

No se enviaron ni modificaron órdenes, posiciones, tickets, lotes, volumen,
fills, P&L ni saldos. No se introducen credenciales ni se leyó `data/`. No se
reinició el servidor. `entry_authorized` permanece en `false` y el modo en
`OBSERVE_ONLY_NO_ORDER` en todos los payloads consultados. El puente sigue con
`active=true` y no se consultó `/api/inbox` durante el trabajo.
