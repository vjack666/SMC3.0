# SMC 3.0

Proyecto público de observación y estudio ICT/SMC para MetaTrader 5. El sistema es de solo lectura: no solicita contraseñas ni envía órdenes.

## Dataset público de velas

El repositorio incluye un dataset reproducible de **162.768 velas EURUSD** descargadas de Dukascopy para el periodo 2006-01-01 a 2025-12-31:

| Temporalidad | Velas |
| --- | ---: |
| H1 | 124.377 |
| H4 | 32.133 |
| D1 | 6.258 |

Los archivos están en `datasets/eurusd_dukascopy_20y/`, en CSV con columnas `time,open,high,low,close`. No existe un volcado SQL local verificable en esta copia del proyecto; por eso se publica el dataset original disponible sin inventar una base distinta. El archivo `metadata.json` conserva los conteos exactos y el intervalo temporal.

Abre MetaTrader 5 en la cuenta FundedNext configurada y ejecuta **abrir-smc.cmd**. El tablero abre en http://127.0.0.1:8766.

## Diario

- Los datos se leen de la cuenta activa de MT5. La sincronización valida el servidor y el número de cuenta.
- El tablero sincroniza los cierres al abrirse y cada 30 segundos mientras permanece abierto. También puedes usar **Sincronizar MT5**.
- El diario local conserva tickets y agrupa las ejecuciones por posición. Los cierres parciales de una misma posición se agrupan al completarse. El resultado neto incluye beneficio, comisión, swap y tarifa tal como llegan de MT5.
- Los cierres y las velas conservan el reloj de MT5. La última sincronización se muestra en hora de Ecuador. La caída calculada con el saldo histórico solo mide movimientos contabilizados.
- La carpeta **data** contiene los datos privados. Guárdala al cambiar de PC. El repositorio local excluye esa carpeta y el entorno de Python.

## Gráfico y notas

1. Carga un símbolo usando el nombre que aparece en MT5. La vista abre en D1 para comenzar por el contexto. El perfil diario usa D1 para sesgo, H4 para zona, H1 para contexto y M15 para observar la confirmación. M5 y M1 están disponibles para inspección de detalle.
2. Usa **Usar ficha ICT** para registrar la lectura top-down. Para marcar un **POI candidato**, abre la temporalidad de la zona y haz clic en su inicio y en el otro límite de precio. La caja guarda una observación manual. Para un nivel o una idea basta un clic. Para una línea de tendencia usa dos.
3. Activa **Ver operaciones** para ver entradas y salidas del símbolo que estás revisando. El diario registra cada posición y el gráfico muestra cada ejecución.
4. Los marcajes quedan guardados en **data/marcajes.json**, por símbolo y temporalidad.

## Instalación en otra PC

Crea un entorno local de Python 3.12 para Windows y ejecuta:

    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt

Copia tus datos privados desde la PC anterior o crea **data/cuenta.json** a partir de **account.example.json**. Indica el login, servidor y ruta del terminal. El programa lee la sesión existente de MT5, sin solicitar contraseñas ni enviar órdenes.

## Autoridad ICT y trazabilidad

- **Fuente principal.** `vjack666/ict2.0`, revisión de `main` en `f453bf2`. El índice define la jerarquía. La tesis firmada gobierna el modelo y la enmienda v1.1 retira OTE. EQ 50% y premium/discount se conservan como contexto. [Índice de autoridad](https://github.com/vjack666/ict2.0/blob/f453bf2a9d35997cec774048a7ead25237399ac9/docs/INDICE_AUTORIDAD.md) · [Tesis firmada](https://github.com/vjack666/ict2.0/blob/f453bf2a9d35997cec774048a7ead25237399ac9/docs/ict/SPEC_TESIS_FORMAL.md) · [Enmienda v1.1](https://github.com/vjack666/ict2.0/blob/f453bf2a9d35997cec774048a7ead25237399ac9/docs/ict/SPEC_TESIS_FORMAL_V1.1_AMENDMENT_OTE_REMOVAL.md)
- **Lectura diaria.** Sesgo HTF con velas cerradas → liquidez y barrido → desplazamiento y BOS/CHOCH → FVG/OB en contexto → retorno. La zona candidata, la confirmación y la ejecución son hitos distintos. El gráfico puede mostrar la vela en formación. El tablero registra observaciones y las ejecuciones que realmente devuelve MT5. [POI](https://github.com/vjack666/ict2.0/blob/main/docs/ict/21_POI.md) · [Capa diaria LTF/EXEC](https://github.com/vjack666/ict2.0/blob/main/docs/tesis/SDD_LTF_ENTRY_LAYER.md)
- **Alcance de la evidencia.** El piloto independiente `c810374` verifica replay causal H4/M15 en los controles publicados. `5146055` certifica un control de anclas de seis temporalidades en otra rama. La rentabilidad y el uso en vivo requieren evidencia propia. Los commits `75de15f` y `080e52c` corresponden al parche de compatibilidad con pandas 3 y su bitácora. [Piloto H4/M15](https://github.com/vjack666/ict2.0/commit/c8103747956db13403fe8b42ce858288ba35c442) · [Control de anclas](https://github.com/vjack666/ict2.0/commit/5146055a5c9c94b7933e2b3252372ebd183cdc96) · [Bitácora pandas 3](https://github.com/vjack666/ict2.0/commit/080e52c6703c68386659c7736d66dc94fc69f0c8)
- **Engram compartido.** El protocolo de agosto registra las decisiones y el trabajo traspasado entre entornos. Los resultados técnicos se contrastan con el commit publicado y la bitácora. Las entradas guardadas el 12 de noviembre distinguen la práctica de TradingView del historial de MT5 y reservan volumen y P&L monetario para cifras confirmadas.
- **Antecedente.** SMC-SYSTEMS documenta el observador anterior y sirve para comparar su evolución. [SMC-SYSTEMS](https://github.com/vjack666/SMC-SYSTEMS)
- **Borradores ICT 3.0.** Las ampliaciones nacen como estudios no activos. El plan, la tesis, el mapa y el primer caso separan una ruptura fuerte aceptada de una entrada ejecutable: [plan de trabajo](docs/ict3/00_PLAN_TRABAJO_ICT3.md) · [tesis ICT 3.0](docs/ict3/THESIS_ICT3.md) · [mapa PDH/PDL](docs/research/ICT3_MAPA_LIQUIDEZ_DIARIA.md) · [ruptura fuerte de liquidez diaria](docs/ict3/01_RUPTURA_FUERTE_LIQUIDEZ_DIARIA.md) · [simulación causal de 26 pares](docs/research/ICT3_SIMULACION_26_PARES.md).

## Análisis automático del universo MT5

El gráfico usa el motor original de `ict2.0` para detectar FVG/OB, registrar su primer toque y evaluar el perfil diario. Los POI se muestran como **candidatos** en H4/H1 cuando el contexto del motor está alineado, la zona permanece sin toque, tiene estructura confirmada del marco padre y desplazamiento, y queda del lado favorable del EQ diario. Este criterio del observador limita el tablero a tres candidatos. Las cajas FVG/OB comienzan al cierre de confirmación y su trazo cambia al primer toque. El gráfico puede mostrar la vela en formación por referencia visual. El motor recibe únicamente velas cerradas.

**Revisar entrada** reconstruye lo que se conocía al abrir esa posición, en hora MT5. El tablero muestra el estado del contexto y los candidatos disponibles al corte, incluida la ausencia de una zona apta. Los recuadros de candidatos muestran el contexto del corte seleccionado. El gráfico conserva los marcajes manuales en una capa independiente.

En **Símbolo**, escribe `EURUSD`, `GBPJPY` o `US30` y pulsa **Cargar gráfico**. El alto y el bajo del día anterior se toman de la última D1 cerrada de ese símbolo en MT5, con su precisión de precio. La revisión desde el diario y los avisos de apertura se ofrecen para EURUSD.

La capa **Último viernes HH/LL** conserva como referencia semanal el máximo y el mínimo de la D1 del viernes más reciente que MT5 ya haya cerrado por completo. Se calcula en Python para cada instrumento, se actualiza diariamente aunque el navegador esté cerrado y cambia al viernes siguiente solo después de su cierre. Es una referencia de liquidez, no una confirmación de entrada.

La interfaz se organiza en tres pestañas: **Mercado** para el gráfico y los marcajes, **Análisis detallado** para los eventos ICT 3.0 y el escáner de POI, y **Diario de MT5** para las operaciones sincronizadas y su lectura histórica.

En **M15 → Modelos del Libro 22** puedes elegir la señal de la lista o hacer clic en su marca en modo **Explorar** para abrir **Análisis detallado**. La ficha muestra lo que el modelo conocía a la hora de la evaluación. Incluye el estado, su motivo, la D1 de origen, el contexto H4, la zona M15 y el retesteo cuando existen. Muestra entrada de referencia, invalidación, objetivo y R cuando se han podido calcular. En revisión histórica, los datos se limitan al corte. Un diamante marca un barrido y un triángulo una continuación observada con dos cierres consecutivos fuera del mismo extremo. El barrido se etiqueta como **Turtle Soup** si el giro planteado va contra el H4 cerrado y como **Giro por barrido** en los demás casos.

El modelo da hasta ocho M15 para la confirmación con desplazamiento y FVG/OB, y hasta ocho más para un cierre que defienda el punto medio de la zona. El stop usa la mecha del barrido o un swing M15 intacto de la continuación, con un margen de 0.3 ATR y ajuste al tick. El primer objetivo elegible es la liquidez intacta más cercana entre swings M15 y el nivel diario disponible en la dirección del escenario. La apertura de la vela siguiente al retesteo sirve de referencia una vez que esa vela cierra. La etiqueta de 3R a 5R es una observación del modelo, con spread aproximado y sin órdenes.

### Criterio para el próximo análisis diario

1. Informar el último cierre usado y el sesgo por D1, H4 y H1 antes de describir ideas.
2. Si hay marcos enfrentados o la ubicación es desfavorable, indicar **esperar** y precisar qué tendría que cambiar.
3. Distinguir un FVG/OB visible de un POI en contexto. En M15 pedir barrido, desplazamiento, estructura y retorno confirmado antes de describir una posible entrada.
4. Si una idea se divide en varios tickets, escribir primero la invalidación común y el presupuesto total de riesgo. La revisión histórica usa los cierres de MT5 y no presupone que el SL final fuera el SL inicial.

### Restaurar el motor en otra PC

Con Git instalado, desde la carpeta de SMC 3.0:

    git clone --filter=blob:none --sparse https://github.com/vjack666/ict2.0.git motor_smc/fuentes/ict2
    git -C motor_smc/fuentes/ict2 sparse-checkout set --no-cone /engine/ /detectors/ /tools/
    git -C motor_smc/fuentes/ict2 switch --detach f453bf2a9d35997cec774048a7ead25237399ac9
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m unittest -q test_ict

La integración trabaja en modo observación. El diario, los marcajes y los datos de cuenta permanecen locales.

## Rangos de apertura M15

- **Londres.** Se observa la primera M15 desde las 08:00 de Londres. Al cierre se compara con PDH/PDL y con el rango desde las 09:00 de Tokio hasta la apertura londinense.
- **Nueva York.** Se observa la primera M15 desde las 08:00 de Nueva York, inicio del solapamiento Forex. Se compara con PDH/PDL y con el rango de Londres acumulado antes de esa apertura.
- La capa **Rangos de apertura M15** admite los 26 pares y cuatro índices de MT5. Al confirmar el cierre de la primera vela de cada apertura, traza el máximo y el mínimo desde sus mechas hasta el final de la jornada del servidor MT5. Londres se dibuja en dorado y Nueva York en violeta. La capa **PDH/PDL** puede verse a la vez. Si al índice le falta la vela exacta de apertura, el rango aparece como no disponible.
- Las velas M15 posteriores se comparan con cada rango ya cerrado hasta el fin de la jornada MT5. El Libro 22 marca con un diamante el barrido que cierra dentro y con un triángulo la ruptura que cierra fuera. Los toques, los huecos, los cruces de ambos extremos y los retornos tardíos quedan fuera de estos avisos. SMC 3.0 muestra el último evento en el panel y avisa en Windows por cada activo al confirmarse el cierre con la siguiente vela. Si una vela afecta ambos rangos, agrupa los dos eventos en un aviso.
- El aviso de Windows de **EURUSD** combina los barridos o rupturas confirmados y se emite una sola vez por apertura. Requiere que MT5 y el servidor local estén abiertos. Los ajustes de notificaciones de Windows pueden ocultar el aviso de escritorio.
- Los horarios se ajustan con las zonas de Londres y Nueva York. El reloj de la cuenta se compara con una cotización reciente del terminal. Un rango de sesión con velas faltantes se omite. Esta función conserva el modo de solo lectura.

## Historial D1 de POI

El escáner de solo lectura [poi_history.py](poi_history.py) revisa los dos años
calendario anteriores al corte. Usa más historial para inicializar la estructura
y devuelve la cobertura efectiva de MT5. Por defecto usa la lista confirmada
de 26 pares. En el panel se puede escanear un grupo completo o abrir el
detalle de un solo símbolo. Los cuatro índices se escanean por separado.
Sus nombres en FundedNext son GER30 (GER40), NDX100 (NAS100), SPX500 (SPX)
y US30.

    .venv\Scripts\python.exe poi_history.py --summary
    .venv\Scripts\python.exe poi_history.py --group indices --summary
    .venv\Scripts\python.exe poi_history.py EURGBP EURUSD GBPJPY US30
    .venv\Scripts\python.exe poi_history.py --symbols-file lista.txt --date 2026-11-18

La fecha incluye las D1 cerradas del día en el calendario de MT5. La última
vela disponible sirve para verificar el cierre de la anterior. El tablero
local expone los mismos resultados en
`/api/poi-history?symbol=EURGBP&symbol=EURUSD`. El parámetro opcional `at`
usa la misma escala de tiempo de MT5 de `/api/ict`.

`scan_poi_history()` usa los detectores canónicos `detect_fvg()` y
`detect_order_blocks()` de ICT 2.0. Cada zona incluye la vela de origen,
los límites y la vela que confirma el patrón. `analyze_poi_history()` distingue
la geometría de un POI candidato con desplazamiento y BOS real o CHOCH
concordante entre el inicio y la confirmación del patrón. Es un filtro D1
para revisar contexto, sin validación de una entrada.

El selector también ofrece **TVC:DXY** como estudio visual en TradingView.
La vista integrada oficial carga al desplegarla y conserva la atribución.
El widget reportó que el símbolo está disponible en el sitio de TradingView,
por lo que el panel ofrece un [enlace al gráfico D1](https://www.tradingview.com/chart/?symbol=TVC%3ADXY&interval=D).
La licencia de visualización de TradingView mantiene a DXY fuera del escaneo
automático de MT5.

`zone_lifecycle()` cuenta las velas en contacto y agrupa contactos
consecutivos. El estado distingue la primera mecha que cruza el borde y
cierra del lado aceptado del primer cierre que invalida la zona. Un toque
exacto al borde cuenta como contacto. El seguimiento comienza después de
la confirmación y termina al primer cierre de invalidación o en el corte.

## Motor de actualización

[motor_smc](motor_smc) contiene los adaptadores locales y el servicio de
panel. La fuente oficial se instala en `motor_smc/fuentes/ict2` con
`engine`, `detectors` y `tools` de la revisión indicada arriba.

**Gráficos abiertos.** El motor comprueba las dos últimas velas de los
marcos relevantes aproximadamente cada 8 segundos por vista. La vela
en curso se puede mostrar. Las señales se recalculan cuando cambia un
cierre confirmado por su sucesora. El panel distingue la última lectura
correcta, el último análisis y los errores. Si se corta MT5, conserva
la última lectura disponible y vuelve a intentar. La actividad de una
vista caduca después de 90 segundos sin solicitudes, con un máximo de
seis vistas atendidas simultáneamente, además del monitor M15.

**Universo completo.** El servicio comprueba un activo cada 25 segundos
y espera su turno si hay gráficos abiertos en cola. Esta comprobación
registra el último cierre D1 disponible por activo aunque el navegador
esté cerrado. Una vuelta nominal toma unos 13 minutos. El panel muestra
solo comprobaciones efectuadas y señala las antiguas.

**Monitor de Windows.** El servidor mantiene M15 para los 26 pares Forex
y US30 aunque el navegador esté cerrado. Comprueba las dos últimas M15
por activo en lotes de hasta cinco, aproximadamente cada 35 segundos por
activo cuando no hay retrasos de MT5. Carga el historial para el análisis
inicial y vuelve a calcularlo cuando cambia una M15 cerrada. La tabla
**Monitor M15** distingue el cierre visto del que realmente se analizó.
Los avisos de apertura siguen en EURUSD, GBPJPY y US30. El nuevo monitor
añade un aviso cuando un escenario del Libro 22 pasa a cumplir
3R–5R en un cierre reciente con reloj y cotización verificados. El primer
análisis establece una referencia silenciosa. Los avisos de escenarios se
deduplican en `data/avisos-motor.json`. La conexión se observa con EURUSD.
Tras una lectura exitosa, la pérdida requiere al menos tres fallos
explícitos durante 90 segundos o más. La recuperación requiere al menos
tres lecturas correctas durante 30 segundos o más. Un mercado sin
cotizaciones recientes se muestra como tal. Todos los avisos son de
observación y usan el sistema de notificaciones local de Windows.

**Historial de dos años.** Se ejecuta por solicitud. En el mismo proceso,
el escáner reutiliza el cálculo por cuenta, símbolo, fecha de corte y
sesión D1 hasta detectar una nueva D1, con historial suficiente para
cubrir el periodo. La caché se vacía cuando se cierra el proceso.
TVC:DXY permanece en TradingView para uso visual.

**Servidor habitual.** El punto de entrada es `abrir-smc.cmd`. Una
instancia que ya está ejecutándose carga los archivos de la página al
recargar el navegador, pero necesita un inicio nuevo para cargar Python
y exponer `/api/market` y `/api/market-universe`. El panel identifica
esa versión anterior y conserva el gráfico existente.

## Referencias de TradingView y medición en MT5

En **Marcaje → Referencias de TradingView**, escribe el símbolo completo,
el marco y el precio que anotaste en TradingView. Para un POI registra cada
borde como una referencia. **Abrir gráfico MT5** busca el mismo ticker o el
alias verificado del bróker. En el gráfico correspondiente, elige apertura,
máximo, mínimo o cierre y pulsa **Medir en vela cerrada**. Luego selecciona
la vela histórica. El panel presenta la hora de la vela en MT5, los dos
precios y la diferencia con signo. También puedes comparar un nivel
existente o elegir un límite de un POI del mismo símbolo y marco.

Las referencias y la última comparación de cada una se guardan en el
navegador de esta PC. Los marcajes de MT5 conservan su archivo habitual.
TVC:DXY admite referencias manuales y un enlace a TradingView. Esta cuenta
no tiene un equivalente de DXY en MT5.

## Grafo local de SMC 3.0

Las consultas de Graphify devuelven relaciones entre funciones y notas
del proyecto. Desde esta carpeta se puede actualizar el grafo y hacer una
consulta acotada con estos comandos.

    .venv\Scripts\graphify.exe update .
    .venv\Scripts\graphify.exe query "scan_poi_history zone_lifecycle" --budget 500
