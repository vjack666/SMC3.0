
const $ = id => document.getElementById(id);
const canvas = $('chart');
const ctx = canvas.getContext('2d');
const chartPanel = $('chartPanel');
const fullscreenButton = $('chartFullscreen');
const chartTooltip = $('chartTooltip');
const windowSize = $('windowSize');
const customWindowSize = $('customWindowSize');
const rightMarginBars = 14;
const defaultBarSpacing = 8;
const dateFormat = new Intl.DateTimeFormat('es-EC', {
  timeZone: 'UTC', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
});
const dailyAxisFormat = new Intl.DateTimeFormat('es-EC', {
  timeZone: 'UTC', day: '2-digit', month: 'short',
});
const timeFormat = new Intl.DateTimeFormat('es-EC', {
  timeZone: 'America/Guayaquil', dateStyle: 'short', timeStyle: 'medium',
});
const ictFields = [
  'D1 · Sesgo y liquidez objetivo',
  'H4 · FVG/OB y ubicación vs. EQ',
  'H1 · Barrido, desplazamiento y estructura',
  'M15 · Retorno a la zona y confirmación',
  'Plan · SL estructural, TP en liquidez y riesgo total de la idea',
];
const frameSeconds = {M1: 60, M5: 300, M15: 900, H1: 3600, H4: 14400, D1: 86400};
const ictReasons = {
  no_htf_direction: 'sin dirección en temporalidades altas',
  h1_opposes_short: 'H1 alcista frente al sesgo bajista',
  h1_opposes_long: 'H1 bajista frente al sesgo alcista',
  h4_opposes_short: 'H4 alcista frente al sesgo bajista',
  h4_opposes_long: 'H4 bajista frente al sesgo alcista',
  short_in_discount: 'precio en descuento para una idea de venta',
  long_in_premium: 'precio en prima para una idea de compra',
};
const ictStates = {
  WAIT_CONTEXT: 'Esperar contexto', WAIT_LTF_CONFIRMATION: 'Esperar confirmación M15',
  WAIT_LTF_ZONE: 'Esperar zona M15', WAIT_RETEST: 'Esperar retorno a la zona',
  OBSERVABLE_SETUP: 'Configuración observable', NO_LTF_DATA: 'Faltan datos M15',
};
const ictColors = {POI: '#f4bd69', FVG: '#54d9c9', OB: '#bd9bf7'};
const book22Models = {turtle_soup: 'Turtle Soup', reversal: 'Giro por barrido', continuation: 'Continuación'};
const book22Alignments = {counter: 'contra H4', aligned: 'a favor de H4', range: 'H4 lateral'};
const book22States = {waiting: 'Candidato · en espera', discarded: 'Descartada', qualified: 'Confirmada por el modelo · cumple 3R–5R'};
const ict3States = {
  BREAK_CANDIDATE: 'Candidato de ruptura',
  FAILED_BREAK: 'Ruptura fallida',
  ACCEPTED_BREAK_WAIT_RETEST: 'Ruptura aceptada · esperar retest',
  RETESTING_POI: 'Retest de POI',
  OBSERVABLE_SETUP: 'Setup observable',
  EXPANSION_NO_ENTRY: 'Expansión sin entrada',
};
// Fase 6: vocabulario del bloque ict3.events (contrato 0.2-research) en español.
// Solo traduce códigos del motor; nunca rellena un dato que el motor no entregó.
const ict3EventStates = {
  ACCEPTED_BREAK_WAIT_RETEST: 'ruptura aceptada · a la espera de retest',
  RETESTING_POI: 'retest de la zona en curso',
  OBSERVABLE_SETUP: 'configuración observable · solo lectura',
  EXPANSION_NO_ENTRY: 'expansión sin entrada · caso cerrado',
  ACCEPTANCE_LOST: 'ruptura sin aceptación · caso cerrado',
  POI_INVALID: 'zona invalidada · caso cerrado',
};
const ict3ConfirmationStates = {
  WAIT_M5_M1_CONFIRMATION: 'esperando defensa y estructura M5/M1',
  M5_STRUCTURE_CONFIRMED: 'estructura M5 confirmada',
};
const ict3Structures = {
  BOS: 'BOS · continuación', CHOCH: 'CHOCH · cambio de carácter', MSS: 'MSS · cambio de estructura',
};
const ict3StopBases = {
  ORIGIN_SWING_INTACT: 'swing de origen intacto',
  M5_REACTION_EXTREME: 'extremo de reacción M5',
  M1_CONFIRMED_EXTREME: 'extremo confirmado M1',
  NO_STRUCTURAL_STOP: 'sin stop estructural',
};
const ict3TargetStates = {
  SATISFIED_TP1_3R_TP2_5R: 'objetivo simulado 3R/5R alcanzado con liquidez conocida',
  TP1_BELOW_3R: 'liquidez conocida por debajo de 3R',
  TP2_BELOW_5R: 'liquidez conocida por debajo de 5R',
  NO_KNOWN_LIQUIDITY_AT_CUTOFF: 'sin liquidez conocida al corte',
  NO_STOP_NO_RISK_UNIT: 'sin stop: no hay unidad R',
  NO_STRUCTURAL_REFERENCE: 'sin referencia estructural',
};
const ict3EvidenceText = {
  CAUSAL_POI_NOT_CONFIRMED: 'falta una zona POI causal confirmada',
  RETEST_NOT_OBSERVED: 'falta un retest observable',
  M5_M1_CONFIRMATION_NOT_LOADED: 'faltan velas M5/M1 cargadas hasta el corte',
  STRUCTURAL_STOP_NOT_DEFINED: 'falta un stop estructural',
  NO_RETEST_WITHIN_COMPARABLE_WINDOWS: 'sin retest en las ventanas comparables',
  BREAK_INVALIDATED: 'la ruptura quedó invalidada',
  DEFENSE_NOT_CONFIRMED_M5: 'falta la defensa confirmada en M5',
  M5_STRUCTURE_NOT_CONFIRMED: 'falta la estructura confirmada en M5',
  NO_STRUCTURAL_STOP: 'falta un stop estructural',
  M5_M1_CONFIRMATION_NOT_COMPLETE: 'la confirmación M5/M1 está incompleta',
  RETEST_EVIDENCE_INCOMPLETE: 'la evidencia del retest está incompleta',
  OBSERVATION_ONLY: 'sin espera: lectura únicamente observacional',
};
const ict3TransitionReasons = {
  first_touch_after_confirmation: 'primer contacto con la zona después de confirmarse',
  m15_close_back_inside_level_before_retest: 'una M15 cerró de nuevo dentro del nivel roto antes del retest',
  close_through_structural_boundary_against_direction: 'cierre más allá del límite estructural, en contra de la dirección',
  no_retest_within_max_observation_window_comparable_results: 'no hubo retest dentro de la ventana máxima de observación comparable',
  retest_defense_m5_structure_stop_and_known_liquidity: 'retest, defensa, estructura M5, stop y liquidez conocida disponibles',
};
const ict3ClosedStates = new Set(['ACCEPTANCE_LOST', 'POI_INVALID', 'EXPANSION_NO_ENTRY']);
function ict3Evidence(code) {
  if (!code) return '';
  const key = String(code);
  if (ict3EvidenceText[key]) return ict3EvidenceText[key];
  if (key.startsWith('TARGET_POLICY_')) {
    const status = key.slice('TARGET_POLICY_'.length);
    return 'objetivo pendiente: ' + (ict3TargetStates[status] || status.replace(/_/g, ' ').toLowerCase());
  }
  if (key.startsWith('LOWER_SOURCE_')) {
    return 'fuente M5/M1 no disponible (' + key.slice('LOWER_SOURCE_'.length).replace(/_/g, ' ').toLowerCase() + ')';
  }
  return 'motivo del motor: ' + key.replace(/_/g, ' ').toLowerCase();
}
function ict3Reason(code) {
  if (!code) return '';
  return ict3TransitionReasons[code] || ict3Evidence(code);
}
const book22Reasons = {
  no_stop_structure: 'Sin swing M15 confirmado para el stop',
  broken_stop_structure: 'El swing que protegía la ruptura ya fue superado',
  no_mss_pivot: 'Sin swing previo confirmado para verificar el cambio de estructura',
  insufficient_history: 'Historial insuficiente para calcular el margen del stop',
  no_mss_zone: 'Falta cambio de estructura con desplazamiento y FVG/OB',
  no_displacement_zone: 'Falta FVG/OB del desplazamiento de ruptura',
  no_retest: 'Falta retorno confirmado al FVG/OB',
  stop_hit: 'El precio alcanzó el stop estructural durante la espera',
  range_lost: 'El cierre salió del rango tras el barrido',
  break_lost: 'La ruptura perdió el nivel al cierre',
  gap: 'Hueco entre velas M15',
  await_reference: 'Retesteo confirmado. Falta cerrar la M15 siguiente para evaluar su apertura',
  session_ended: 'Terminó la jornada antes de disponer de un precio de referencia',
  reference_invalid: 'La apertura de referencia dejó de defender el nivel o hubo un hueco',
  invalid_risk: 'El precio de referencia quedó del lado inválido del stop',
  no_target: 'Sin liquidez opuesta intacta para un TP estructural',
  below_rr: 'El primer TP estructural queda por debajo de 3R',
  above_rr: 'El primer TP estructural supera 5R',
  in_range: 'El primer TP estructural está dentro de 3R–5R',
};
let journal, chartData, chartScope, pending, geometry;
let ictData, reviewAt;
let book22Selection = '';
let openings, lastOpeningNotice;
const openingSymbols = new Set(['EURUSD', 'GBPJPY', 'US30']);
const readingOpenings = new Set();
let notes = {};
let offset = 0;
let manualPriceRange = null;
let drag = null;
let chartHover = null;
let chartRequest = 0;
let editing = false;
let marketAvailable, requestedMarketScope, shownAnalysis;

async function api(path, options) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw Object.assign(new Error(result.error || 'No se pudo conectar.'), {status: response.status});
  return result;
}
function message(id, text, error = false) {
  const target = $(id);
  target.textContent = text;
  target.classList.toggle('error', error);
}

const scanGroups = new Map();
const scanNames = new Map();
const mt5Catalog = JSON.parse($('mt5Catalog').textContent);
let scanHistoryAvailable = false;

function symbolGroups(catalog) {
  return [
    ['26 pares Forex', Object.fromEntries(catalog.forex.map(symbol => [symbol, symbol]))],
    ['Índices', catalog.indices],
    ['Materias primas', catalog.commodities || {}],
  ];
}

function populateSymbolMenu(catalog) {
  const selected = $('symbol').value || 'EURUSD';
  for (const id of ['symbol', 'analysisSymbol']) {
    const menu = $(id);
    menu.replaceChildren(...symbolGroups(catalog).map(([label, symbols]) => {
      const group = document.createElement('optgroup');
      group.label = label;
      for (const [name, symbol] of Object.entries(symbols)) {
        group.append(new Option(name === symbol ? name : name + ' · ' + symbol, symbol));
      }
      return group;
    }));
    menu.value = id === 'analysisSymbol' ? 'EURUSD' : selected;
    if (!menu.value) menu.value = 'EURUSD';
  }
}

populateSymbolMenu(mt5Catalog);

async function loadScanUniverse() {
  try {
    let catalog;
    try {
      catalog = await api('/api/poi-universe');
      scanHistoryAvailable = true;
    } catch (error) {
      if (error.status !== 404) throw error;
      catalog = mt5Catalog;
    }
    const {forex, indices, commodities = {}} = catalog;
    populateSymbolMenu(catalog);
    scanGroups.set('forex', forex);
    scanGroups.set('indices', Object.values(indices));
    scanGroups.set('commodities', Object.values(commodities));
    for (const symbol of forex) {
      scanNames.set(symbol, symbol);
      $('scanForex').append(new Option(symbol, symbol));
    }
    for (const [name, symbol] of Object.entries(indices)) {
      const label = name === symbol ? name : name + ' (' + symbol + ')';
      scanNames.set(symbol, label);
      $('scanIndices').append(new Option(label, symbol));
    }
    for (const [name, symbol] of Object.entries(commodities)) {
      const label = name + ' (' + symbol + ')';
      scanNames.set(symbol, label);
      $('scanCommodities').append(new Option(label, symbol));
    }
    message('scanSource', scanHistoryAvailable ? 'Lista de instrumentos del servidor SMC 3.0.'
      : 'Lista local confirmada. El servidor anterior permite abrir gráficos de MT5.');
    if (!scanHistoryAvailable) showScanUnavailable();
    updateScanActions();
  } catch (error) {
    scanHistoryAvailable = false;
    message('scanSource', 'No se pudo cargar la lista de MT5. ' + error.message, true);
    updateScanActions();
  }
}

function showScanUnavailable() {
  scanHistoryAvailable = false;
  message('scanStatus', 'Para activar el escáner histórico, inicia SMC 3.0 con el lanzador después de cerrar el servidor anterior.');
}

function updateScanActions() {
  const value = $('scanTarget').value;
  const external = value === 'TVC:DXY';
  const busy = $('scanTarget').disabled;
  $('scanDate').disabled = $('scanSubmit').disabled = busy || !scanHistoryAvailable;
  $('scanOpenChart').disabled = busy || !scanNames.has(value);
  for (const id of ['scanDateLabel', 'scanSubmit', 'scanOpenChart', 'scanSource', 'scanStatus']) {
    $(id).hidden = external;
  }
}

async function refreshUniverseMonitor() {
  if (marketAvailable === false) {
    $('universeStatus').textContent = 'Comprobación D1 pendiente de reiniciar el servidor';
    $('intradayStatus').textContent = 'Monitor M15 pendiente de reiniciar el servidor';
    return;
  }
  try {
    const {total, assets, intraday} = await api('/api/market-universe');
    const rows = Object.entries(assets);
    const valid = rows.filter(([, data]) => !data.error && Date.now() - Date.parse(data.checked_at) < 30 * 60000);
    $('universeStatus').textContent = 'Último cierre D1 comprobado en ' + valid.length + '/' + total + ' activos MT5';
    const body = $('universeRows');
    body.replaceChildren();
    for (const [symbol, row] of rows) {
      const expired = Date.now() - Date.parse(row.checked_at) >= 30 * 60000;
      resultRow(body, [scanNames.get(symbol) ?? symbol,
        row.last_closed ? new Date(row.last_closed * 1000).toISOString().slice(0, 16).replace('T', ' ') : '—',
        timeFormat.format(new Date(row.checked_at)),
        row.error || (expired ? 'Comprobación anterior' : 'Cierre identificado')]);
    }
    const entries = Object.entries(intraday ?? {});
    const forex = entries.filter(([symbol, row]) => symbol !== 'US30' && row.state === 'current' && row.closed === row.analyzed);
    const us30 = intraday?.US30?.state === 'current' ? 'al día' : 'pendiente o en revisión';
    $('intradayStatus').textContent = entries.length ? 'M15 · ' + forex.length + '/' + (entries.length - 1) +
      ' pares al día · US30 ' + us30 : 'Monitor M15 aún no disponible';
    $('intradayRows').replaceChildren();
    const date = value => value ? new Date(value * 1000).toISOString().slice(0, 16).replace('T', ' ') : '—';
    for (const [symbol, row] of entries) {
      const state = {current: 'Al día', loading: 'Preparando', stale: 'Datos en revisión', unavailable: 'MT5 no disponible'};
      resultRow($('intradayRows'), [symbol, date(row.closed), date(row.analyzed),
        row.checked_at ? timeFormat.format(new Date(row.checked_at)) : '—',
        [state[row.state], ...Object.values(row.errors ?? {})].join(' · ')]);
    }
  } catch (error) {
    $('universeStatus').textContent = error.status === 404 ? 'Comprobación D1 pendiente de reiniciar el servidor'
      : 'Comprobación D1 sin respuesta';
    $('intradayStatus').textContent = error.status === 404 ? 'Monitor M15 pendiente de reiniciar el servidor'
      : 'Monitor M15 sin respuesta';
  }
}

function changeScanTarget() {
  const external = $('scanTarget').value === 'TVC:DXY';
  $('scanResults').hidden = true;
  $('scanDetails').hidden = true;
  $('dxyPanel').hidden = !external;
  if (scanHistoryAvailable) message('scanStatus', '');
  updateScanActions();
}

function openSelectedScanChart() {
  const symbol = $('scanTarget').value;
  if (!scanNames.has(symbol)) return;
  reviewAt = null;
  $('liveView').hidden = true;
  $('symbol').value = symbol;
  loadChart(true);
  $('chartPanel').scrollIntoView({block: 'start'});
}

function loadDxyWidget() {
  const frame = $('dxyFrame');
  if ($('dxyWidget').open && !frame.hasAttribute('src')) {
    // Direct third-party iframe generated by TradingView's Advanced Chart embed.
    const settings = {
      symbol: 'TVC:DXY', interval: 'D', timezone: 'America/Guayaquil', theme: 'dark',
      style: '1', allow_symbol_change: false, withdateranges: true,
      autosize: true, width: '100%', height: '100%', support_host: 'https://www.tradingview.com',
    };
    frame.src = 'https://www.tradingview-widget.com/embed-widget/advanced-chart/?locale=es#'
      + encodeURIComponent(JSON.stringify(settings));
  }
}

function resultRow(body, cells) {
  const row = body.insertRow();
  for (const value of cells) {
    const cell = row.insertCell();
    if (value instanceof HTMLElement) cell.append(value);
    else cell.textContent = value;
  }
}

async function scanHistory(event) {
  event.preventDefault();
  const target = $('scanTarget');
  const date = $('scanDate');
  if (target.value === 'TVC:DXY' || $('scanSubmit').disabled) return;
  const group = scanGroups.get(target.value);
  const symbols = group ?? [target.value];
  target.disabled = true;
  updateScanActions();
  $('scanResults').hidden = $('scanDetails').hidden = true;
  $('scanRows').replaceChildren();
  $('scanZoneRows').replaceChildren();
  const failures = [];
  let count = 0;
  try {
    // Yield between symbols so requests for the chart and session alerts can run.
    for (const [index, symbol] of symbols.entries()) {
      message('scanStatus', 'Leyendo ' + symbol + ' en MT5 · ' + (index + 1) + '/' + symbols.length);
      const query = new URLSearchParams({symbol});
      if (group) query.set('summary', '1');
      if (date.value) query.set('date', date.value);
      try {
        const {results, errors} = await api('/api/poi-history?' + query);
        if (errors[symbol]) throw new Error(errors[symbol]);
        renderScanAsset(results[0], group);
        count++;
      } catch (error) {
        if (error.status === 404) {
          showScanUnavailable();
          return;
        }
        failures.push(symbol + ' · ' + error.message);
      }
    }
    const completed = count + (count === 1 ? ' activo revisado.' : ' activos revisados.');
    message('scanStatus', [completed, ...failures].join(' '), failures.length > 0);
  } finally {
    target.disabled = false;
    updateScanActions();
  }
}

function renderScanAsset(result, group) {
  const asset = document.createElement(group ? 'button' : 'span');
  asset.textContent = scanNames.get(result.symbol) ?? result.symbol;
  if (group) {
    asset.type = 'button';
    asset.addEventListener('click', () => {
      if ($('scanSubmit').disabled) return;
      $('scanTarget').value = result.symbol;
      $('scanForm').requestSubmit();
    });
  }
  const coverage = result.has_history_before_window ? '' : ' · cobertura parcial';
  resultRow($('scanRows'), [asset, result.closed_bars + coverage, result.last_closed_d1,
    result.zone_count, result.candidate_count]);
  $('scanResults').hidden = false;
  for (const zone of result.zones ?? []) {
    resultRow($('scanZoneRows'), [
      zone.kind + (zone.direction === 'bullish' ? ' alcista' : ' bajista'),
      zone.origin.opened.slice(0, 10), zone.confirmation.closed.slice(0, 10),
      zone.low + ' – ' + zone.high, zone.classification === 'poi_candidate' ? 'POI candidato' : 'Geometría',
      zone.contact_bars + ' velas / ' + zone.contact_episodes + ' episodios',
      zone.first_wick_breach?.opened.slice(0, 10) ?? '—',
      zone.first_close_invalidation?.opened.slice(0, 10) ?? '—',
    ]);
  }
  $('scanDetails').hidden = $('scanZoneRows').rows.length === 0;
}
function money(value) {
  return new Intl.NumberFormat('es-EC', {
    style: 'currency', currency: journal.account.currency,
  }).format(value);
}
function price(value) {
  return Number(value.toFixed(8)).toString();
}

const referenceKey = 'smc3.tradingview-references.v1';
const brokerAliases = mt5Catalog.indices;
let references = [];

function referenceInstrument(symbol) {
  const ticker = symbol.split(':').at(-1);
  return ticker === 'DXY' ? null : (brokerAliases[ticker] ?? ticker);
}

function selectedReference() {
  return references.find(item => item.id === $('referenceSelect').value);
}

function referenceMatches(ref, scope) {
  return Boolean(ref && scope && ref.tf === scope.tf && referenceInstrument(ref.symbol) === scope.symbol);
}

function saveReferences(next) {
  try {
    localStorage.setItem(referenceKey, JSON.stringify(next));
    references = next;
    return true;
  } catch {
    message('referenceStatus', 'El navegador no permitió guardar la referencia.', true);
    return false;
  }
}

function drawReferenceControls() {
  const ref = selectedReference();
  const symbol = ref && referenceInstrument(ref.symbol);
  $('referenceSaved').hidden = !ref;
  $('referenceActions').hidden = !symbol;
  $('referenceDxy').hidden = ref?.symbol.split(':').at(-1) !== 'DXY';
  $('referenceMeasure').disabled = !referenceMatches(ref, chartScope);
  if (!ref) return;
  message('referenceSource', ref.symbol + ' · ' + ref.tf + ' · TradingView manual' +
    (symbol ? (referenceMatches(ref, chartScope) ? ' · Gráfico MT5: ' : ' · Buscar en MT5: ') + symbol
      : ' · Sin equivalente MT5 en esta cuenta.'));
  const data = ref.measurement;
  if (!data || !referenceMatches(ref, data)) {
    message('referenceResult', '');
    return;
  }
  const decimals = Math.max(data.digits, ref.price.split('.')[1]?.length ?? 0);
  const delta = (data.price - Number(ref.price)).toFixed(decimals);
  const signed = Number(delta) > 0 ? '+' + delta : Number(delta) === 0 ? (0).toFixed(decimals) : delta;
  const time = new Date(data.time * 1000).toISOString().slice(0, 16).replace('T', ' ');
  message('referenceResult', data.symbol + ' · ' + data.field + ' ' + data.price.toFixed(data.digits) +
    ' · ' + time + ' (MT5) · TradingView ' + ref.price + ' · Diferencia MT5 − TradingView: ' + signed);
}

function refreshReferences(id = $('referenceSelect').value) {
  const select = $('referenceSelect');
  select.replaceChildren(...references.map(ref => new Option(ref.symbol + ' · ' + ref.tf + ' · ' + ref.price, ref.id)));
  if (references.some(ref => ref.id === id)) select.value = id;
  drawReferenceControls();
  drawNotes();
}

function resetReferenceTool() {
  if ($('tool').value !== 'referencia') return;
  $('tool').value = '';
  $('tool').dispatchEvent(new Event('change'));
}

function captureReference(event) {
  event.preventDefault();
  const symbol = $('referenceSymbol').value.trim().toUpperCase();
  const price = $('referencePrice').value.trim().replace(',', '.');
  if (!/^(?:[A-Z0-9_.-]{1,20}:)?[A-Z0-9_.#-]{1,26}$/.test(symbol) ||
      !/^-?\d{1,8}(?:\.\d{1,8})?$/.test(price)) {
    message('referenceStatus', 'Escribe el símbolo de TradingView y un precio decimal válido.', true);
    return;
  }
  const tf = $('referenceFrame').value;
  const duplicate = references.find(ref => ref.symbol === symbol && ref.tf === tf && ref.price === price);
  const item = duplicate ?? {id: crypto.randomUUID(), symbol, tf, price};
  if (duplicate || saveReferences([item, ...references])) {
    resetReferenceTool();
    refreshReferences(item.id);
    message('referenceStatus', duplicate ? 'La referencia ya estaba guardada.' : 'Referencia guardada en este navegador.');
  }
}

function recordReferenceMeasurement(scope, data) {
  const ref = selectedReference();
  if (!referenceMatches(ref, scope)) {
    message('referenceStatus', 'Abre el mismo instrumento y marco en MT5 antes de comparar.', true);
    return false;
  }
  const measurement = {...scope, ...data, digits: chartData.digits};
  if (!saveReferences(references.map(item => item.id === ref.id ? {...item, measurement} : item))) return false;
  drawReferenceControls();
  return true;
}

function measureReferenceCandle(point) {
  const index = point?.t == null ? -1 : chartData.rows.findIndex(row => row[0] === point.t);
  if (index < 0 || (!reviewAt && index === chartData.rows.length - 1)) {
    message('markStatus', 'Selecciona una vela MT5 ya cerrada.', true);
    return;
  }
  const field = $('referenceField').selectedOptions[0];
  const row = chartData.rows[index];
  if (recordReferenceMeasurement(chartScope, {time: row[0], price: row[Number(field.value)], field: field.textContent + ' de vela'})) {
    resetReferenceTool();
    message('markStatus', 'Medición de MT5 guardada en la referencia.');
  }
}
function showJournal(snapshot) {
  if (!snapshot) return;
  journal = snapshot;
  const a = journal.account;
  $('account').textContent = a.server + ' · ' + (a.trade_mode === 0 ? 'Demo' : 'Cuenta') + ' · ••••' + String(a.login).slice(-4);
  $('balance').textContent = money(a.balance);
  $('equity').textContent = money(a.equity);
  $('net').textContent = money(journal.execution_net);
  $('net').className = journal.execution_net < 0 ? 'negative' : 'positive';
  $('closedCount').textContent = journal.closed.length.toLocaleString('es-EC');
  const difference = journal.balance_difference;
  const unresolved = journal.incomplete_positions.length;
  const issues = [];
  if (difference) issues.push('Diferencia de saldo ' + money(difference));
  if (unresolved) issues.push(unresolved + ' sin reconstruir');
  message('recon', (issues.length ? issues.join(' · ') : 'Saldo conciliado') + ' · '
    + journal.open_positions.length + ' abiertas · ' + journal.pending_orders + ' órdenes pendientes', !!issues.length);
  const contents = document.createDocumentFragment();
  for (const trade of [...journal.closed].reverse()) {
    const row = document.createElement('tr');
    const values = [trade.closed, trade.symbol, trade.side, trade.volume, price(trade.entry_price),
      price(trade.exit_price), trade.reason, money(trade.net)];
    values.forEach((value, index) => {
      const cell = row.insertCell();
      cell.textContent = value;
      if (index === values.length - 1) cell.className = trade.net < 0 ? 'negative' : 'positive';
    });
    const review = row.insertCell();
    if (trade.symbol === 'EURUSD' && trade.open_time) {
      const button = document.createElement('button');
      button.textContent = 'Revisar entrada';
      button.setAttribute('aria-label', 'Revisar entrada EURUSD ' + trade.opened);
      button.addEventListener('click', () => {
        reviewAt = trade.open_time;
        $('symbol').value = trade.symbol;
        $('tf').value = 'M15';
        $('liveView').hidden = false;
        loadChart(true);
        $('chartForm').scrollIntoView({block: 'start'});
      });
      review.append(button);
    }
    contents.append(row);
  }
  $('tradeRows').replaceChildren(contents);
  render();
}

async function refreshJournal() {
  if ($('sync').disabled) return;
  $('sync').disabled = true;
  try {
    const {journal: snapshot} = await api('/api/sync', {method: 'POST'});
    showJournal(snapshot);
    message('syncStatus', 'Actualizado · ' + timeFormat.format(new Date(snapshot.updated_at)));
  } catch (error) {
    message('syncStatus', error.message + (journal ? ' · Última copia guardada en pantalla' : ''), true);
  } finally {
    $('sync').disabled = false;
  }
}

async function loadChart(changeScope = false) {
  const scope = {symbol: $('symbol').value.trim().toUpperCase(), tf: $('tf').value};
  if (!scope.symbol) return;
  if (!changeScope && (reviewAt || requestedMarketScope !== scopeKey(scope))) return;
  const request = ++chartRequest;
  const cutoff = reviewAt;
  if (changeScope) {
    requestedMarketScope = scopeKey(scope);
    shownAnalysis = null;
    resetReferenceTool();
    pending = null;
    clearChartHover();
    offset = 0;
    manualPriceRange = null;
    ictData = null;
    book22Selection = '';
    $('book22Panel').hidden = true;
    message('ictStatus', 'Leyendo velas cerradas…');
    message('ictZones', '');
    message('dailyLevels', '');
    message('fridayLevels', '');
    message('dailyEvents', '');
    message('chartStatus', 'Cargando ' + scopeKey(scope));
  }
  try {
    const market = cutoff ? null : await readMarket(scope, request);
    if (request !== chartRequest) return;
    if (market && !market.chart) {
      message('chartStatus', market.state === 'loading' ? 'Esperando datos de ' + scopeKey(scope)
        : 'Sin velas disponibles para ' + scopeKey(scope), market.state !== 'loading');
      return;
    }
    if (cutoff) message('marketStatus', 'Revisión histórica · las velas del gráfico se limitan al corte elegido.');
    const data = market ? market.chart : await api('/api/chart?' + new URLSearchParams(scope));
    if (request !== chartRequest) return;
    const priorEnd = !changeScope && offset > 0 ? chartData?.rows.at(-1 - offset)?.[0] : null;
    chartData = cutoff ? {...data, rows: data.rows.filter((row, i, rows) =>
      i < rows.length - 1 && Math.min(row[0] + frameSeconds[scope.tf], rows[i + 1][0]) <= cutoff)} : data;
    if (priorEnd != null) {
      const endIndex = chartData.rows.findIndex(row => row[0] === priorEnd);
      offset = chartData.rows.length - 1 - endIndex;
    }
    const scopeChanged = !chartScope || scopeKey(chartScope) !== scopeKey(scope);
    chartScope = scope;
    drawReferenceControls();
    if (changeScope || scopeChanged) drawNotes();
    $('markScope').textContent = scope.symbol + ' · ' + scope.tf;
    if (changeScope) {
      message('openingSchedule', '');
      message('openingNotice', '');
      if (!market) refreshOpenings();
    }
    message('chartStatus', cutoff
      ? 'Revisión · ' + dateFormat.format(new Date(cutoff * 1000)) + ' · hora MT5'
      : data.rows.length + ' velas de MT5');
    render();
    if (market) {
      if (market.analysis && market.analysis_at !== shownAnalysis) {
        showIct(market.analysis, scope);
        shownAnalysis = market.analysis_at;
      } else if (!market.analysis) {
        message('ictStatus', market.errors?.ict || 'Esperando análisis de velas cerradas.', !!market.errors?.ict);
      }
      if (market.openings) await refreshOpenings(market.openings);
      else if (market.errors?.openings) message('openingSchedule', market.errors.openings, true);
    } else {
      await loadIct(scope, cutoff, request);
    }
  } catch (error) {
    if (request === chartRequest) {
      message('chartStatus', error.message + (chartData ? ' · Se conserva el último gráfico' : ''), true);
    }
  }
}

async function readMarket(scope, request) {
  if (marketAvailable === false) {
    message('marketStatus', 'Servidor anterior · gráfico y análisis disponibles en modo anterior.');
    return null;
  }
  try {
    const result = await api('/api/market?' + new URLSearchParams(scope));
    if (request !== chartRequest) return null;
    marketAvailable = true;
    const state = {loading: 'Preparando', current: 'Motor al día', stale: 'Datos en revisión',
      unavailable: 'MT5 no disponible'}[result.state];
    const last = result.last_success && 'Última lectura ' + timeFormat.format(new Date(result.last_success));
    const checked = result.checked_at && 'Latido ' + timeFormat.format(new Date(result.checked_at));
    const analysis = result.analysis_at && 'Último análisis ' + timeFormat.format(new Date(result.analysis_at));
    const quote = result.quote_age > 180 ? 'sin cotización reciente'
      : result.last_tick_mt5 && 'Última cotización ' + chartTime(result.last_tick_mt5);
    const errors = Object.values(result.errors ?? {});
    message('marketStatus', [state, checked, last, analysis, quote, ...errors].filter(Boolean).join(' · '),
      result.state === 'stale' || result.state === 'unavailable');
    return result;
  } catch (error) {
    if (request !== chartRequest) return null;
    if (error.status === 404) {
      marketAvailable = false;
      message('marketStatus', 'Servidor anterior · gráfico y análisis disponibles en modo anterior.');
      return null;
    }
    if (error.status === 400) {
      message('marketStatus', error.message, true);
      return null;
    }
    message('marketStatus', 'Motor sin respuesta · ' + error.message, true);
    throw error;
  }
}

async function loadIct(scope, cutoff, request) {
  const query = new URLSearchParams(scope);
  if (cutoff) query.set('at', cutoff);
  try {
    const result = await api('/api/ict?' + query);
    if (request !== chartRequest) return;
    showIct(result, scope);
  } catch (error) {
    if (request !== chartRequest) return;
    ictData = null;
    $('book22Panel').hidden = true;
    message('ictStatus', error.message, true);
    message('ictZones', '');
    message('dailyLevels', '');
    message('dailyEvents', '');
    render();
  }
}

function showIct(result, scope) {
  ictData = result.enabled ? result : null;
  if (!ictData) {
    message('ictStatus', result.reason);
    $('book22Panel').hidden = true;
    return;
  }
  const bias = {BULLISH: 'alcista', BEARISH: 'bajista', RANGING: 'sin dirección'}[result.bias] || result.bias;
  const reason = ictReasons[result.context_reason];
  const status = ictStates[result.status] || result.status;
  message('ictStatus', status + ' · Sesgo ' + bias + (reason ? ' · ' + reason : '')
    + ' · ' + dateFormat.format(new Date(result.asof * 1000)) + ' MT5');
  const count = kind => result.marks.filter(mark => mark.kind === kind).length;
  const candidates = result.pois.map(poi => poi.tf + ' ' + poi.base + ' '
    + price(poi.low) + '–' + price(poi.high));
  message('ictZones', 'Ventana ' + scope.tf + ' · ' + count('FVG') + ' FVG · ' + count('OB') + ' OB'
    + ' · ' + (candidates.length ? 'POI al corte · ' + candidates.join(' · ') : 'Sin POI candidato al corte'));
  showDailyLiquidity(result.daily_liquidity);
  showFridayReference(result.friday_reference);
  renderIct3Detail(result, scope);
  updateBook22();
  render();
}

function analysisCard(title, body, tone = '') {
  const card = document.createElement('section');
  card.className = 'analysis-card ' + tone;
  const heading = document.createElement('h3');
  heading.textContent = title;
  const paragraph = document.createElement('p');
  paragraph.textContent = body;
  card.append(heading, paragraph);
  return card;
}

function ict3Stamp(time) {
  return time == null || time === '' ? '' : chartTime(Number(time));
}
function ict3Price(value) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : price(Number(value));
}
function ict3Step(name, status, state, time, reason, options = {}) {
  const row = document.createElement('div');
  row.className = 'ict3-step ict3-step--' + status;
  row.dataset.stage = options.stage || '';
  row.setAttribute('data-ict3-stage', options.key || options.stage || '');
  row.dataset.status = status;
  row.setAttribute('data-ict3-state', state);
  row.setAttribute('data-ict3-time', time || '');
  row.setAttribute('data-ict3-reason', reason);
  const term = document.createElement('dt');
  term.textContent = name;
  const desc = document.createElement('dd');
  const head = document.createElement('p');
  head.className = 'ict3-step-head';
  const stateEl = document.createElement('strong');
  stateEl.textContent = state;
  const badge = document.createElement('span');
  badge.className = 'ict3-badge ict3-badge--' + status;
  badge.textContent = {observed: 'observado', wait: 'esperar', closed: 'cerrado'}[status];
  head.append(stateEl, badge);
  if (time) {
    const stamp = document.createElement('time');
    stamp.textContent = time;
    head.append(stamp);
  }
  const why = document.createElement('p');
  why.className = 'ict3-step-reason';
  why.textContent = reason;
  desc.append(head, why);
  if (options.note) {
    const note = document.createElement('p');
    note.className = 'ict3-step-note';
    note.textContent = options.note;
    desc.append(note);
  }
  row.append(term, desc);
  return row;
}

function ict3Band(kind, title, text) {
  const band = document.createElement('section');
  band.className = 'ict3-band ict3-band--' + kind;
  const heading = document.createElement('h4');
  heading.textContent = title;
  const body = document.createElement('p');
  body.textContent = text;
  band.append(heading, body);
  return band;
}

function ict3EventCard(event, scope) {
  const state = String(event.current_state || '');
  const closed = ict3ClosedStates.has(state);
  const pending = (event.pending_evidence || []).filter(Boolean);
  const waiting = !closed && state !== 'OBSERVABLE_SETUP' && pending.length > 0;
  const status = closed ? 'closed' : waiting ? 'wait' : 'observed';
  const symbol = event.symbol || scope.symbol;
  const levelName = event.level_name === 'PDH' ? 'máximo anterior'
    : event.level_name === 'PDL' ? 'mínimo anterior' : (event.level_name || 'nivel');
  const history = Array.isArray(event.transition_history) ? event.transition_history : [];
  const lastTransition = history.at(-1);
  const retestStep = history.find(step => step.to === 'RETESTING_POI');
  const poiCandidates = Array.isArray(event.poi_candidates) ? event.poi_candidates : [];
  const primaryId = typeof event.primary_poi === 'string' ? event.primary_poi : event.primary_poi?.zone_id;
  // El contrato expone primary_poi como zone_id (cadena) y lo detalla en
  // poi_candidates. Solo se muestra la zona cuando existe en esa lista.
  const primary = event.primary_poi && typeof event.primary_poi === 'object'
    ? event.primary_poi
    : poiCandidates.find(candidate => candidate.zone_id === primaryId) ?? null;
  const targetStatus = event.target_policy_status == null ? '' : String(event.target_policy_status);
  const targetText = targetStatus
    ? (ict3TargetStates[targetStatus] || targetStatus.replace(/_/g, ' ').toLowerCase())
    : 'sin estado de objetivo informado por el motor';
  const targetOk = targetStatus === 'SATISFIED_TP1_3R_TP2_5R';
  // En un caso cerrado la evidencia que no llegó a existir no está "pendiente":
  // se marca como cerrada para no sugerir una entrada futura. Un setup completo
  // tampoco puede quedar a la espera de un dato que el motor ya dio por cerrado.
  const complete = state === 'OBSERVABLE_SETUP';
  const missingStatus = closed ? 'closed' : complete ? 'observed' : 'wait';
  const missingState = text => closed ? 'Sin evidencia · caso cerrado' : complete ? 'Sin dato registrado' : text;
  const missingReason = text => closed ? 'Caso cerrado antes de disponer de esta evidencia: ' + text
    : complete ? 'Configuración observable: el motor no entregó este dato.' : text;

  const card = document.createElement('article');
  card.className = 'analysis-card ict3-event ict3-event--' + status;
  card.dataset.eventId = event.event_id || '';
  card.dataset.state = state;
  card.dataset.symbol = symbol;
  card.dataset.status = status;

  const head = document.createElement('header');
  head.className = 'ict3-event-head';
  const title = document.createElement('h3');
  title.textContent = symbol + ' · Ruptura de ' + levelName
    + (event.level != null ? ' ' + ict3Price(event.level) : '');
  const chip = document.createElement('span');
  chip.className = 'ict3-chip ict3-chip--' + status;
  chip.textContent = closed ? 'Caso cerrado' : waiting ? 'Esperar' : 'Lectura completa';
  head.append(title, chip);
  const sub = document.createElement('p');
  sub.className = 'ict3-event-sub';
  sub.textContent = 'Expediente ' + (event.event_id || 'sin identificador') + ' · pertenece a ' + symbol
    + ' · ' + (ict3EventStates[state] || state.replace(/_/g, ' ').toLowerCase())
    + ' · solo observación: entrada no autorizada.';
  head.append(sub);
  card.append(head);

  const steps = document.createElement('dl');
  steps.className = 'ict3-steps';

  const acceptedAt = event.accept_time ?? event.observed_at;
  steps.append(ict3Step('Ruptura', acceptedAt ? 'observed' : missingStatus,
    acceptedAt ? 'Ruptura aceptada al cierre M15' : missingState('Esperar cierre de aceptación'),
    ict3Stamp(acceptedAt),
    acceptedAt
      ? 'El cierre quedó fuera de ' + levelName + (event.level != null ? ' ' + ict3Price(event.level) : '') + '.'
      : missingReason('Sin hora de aceptación registrada; no se inventa el cierre.'),
    {stage: 'break', key: 'ruptura', note: 'Evidencia: vela M15 cerrada.'}));

  const poiDesc = primary
    ? 'Zona ' + (primary.kind || 'POI').toUpperCase() + ' ' + ict3Price(primary.low) + '–' + ict3Price(primary.high)
      + ' · candidata, no entrada.'
    : poiCandidates.length
      ? poiCandidates.length + ' registro(s) de zonas examinadas; ninguna asociada causalmente como principal; no son entradas.'
      : 'Sin zona candidata asociada causalmente.';
  steps.append(ict3Step('Zona POI · candidata', primary ? 'observed' : missingStatus,
    primary ? 'Zona candidata principal' : missingState('Esperar POI causal'),
    ict3Stamp(primary?.confirmed_at),
    poiDesc + (primary ? '' : ' · ' + missingReason(ict3Evidence('CAUSAL_POI_NOT_CONFIRMED')) + '.'),
    {stage: 'poi', key: 'zona', note: 'Una zona candidata no se presenta nunca como entrada confirmada.'}));

  const retestReason = retestStep
    ? ict3Reason(retestStep.reason)
    : ict3Evidence(pending.includes('RETEST_NOT_OBSERVED') ? 'RETEST_NOT_OBSERVED' : 'RETEST_EVIDENCE_INCOMPLETE');
  steps.append(ict3Step('Retest', event.retest_at ? 'observed' : missingStatus,
    event.retest_at ? 'Retest observado' : missingState('Esperar retest'),
    ict3Stamp(event.retest_at),
    missingReason(retestReason) + '.',
    {stage: 'retest', key: 'retest'}));

  const m5Kind = event.m5_structure_kind;
  const m5Ok = Boolean(event.defense_at && m5Kind);
  const m5Reasons = [];
  if (!event.defense_at) m5Reasons.push(ict3Evidence('DEFENSE_NOT_CONFIRMED_M5'));
  if (!m5Kind) m5Reasons.push(ict3Evidence('M5_STRUCTURE_NOT_CONFIRMED'));
  steps.append(ict3Step('Defensa y estructura M5', m5Ok ? 'observed' : missingStatus,
    m5Ok ? 'Defensa M5 y estructura confirmadas' : missingState('Esperar defensa y estructura M5'),
    ict3Stamp(event.defense_at ?? event.m5_structure_at),
    (m5Ok
      ? (m5Kind ? ict3Structures[m5Kind] || m5Kind : '') + ' · cierre M5 ' + ict3Stamp(event.m5_structure_at)
      : m5Reasons.map(missingReason).join('; ')) || (ict3ConfirmationStates[event.confirmation_state] || event.confirmation_state || 'sin confirmación'),
    {stage: 'm5', key: 'm5', note: closed ? '' : (ict3ConfirmationStates[event.confirmation_state] || '')}));

  const m1Kind = event.m1_structure_kind;
  steps.append(ict3Step('Corroboración M1', 'observed',
    m1Kind ? 'Corroboración M1 observada' : 'Sin corroboración M1 · opcional',
    ict3Stamp(event.m1_structure_at),
    m1Kind
      ? (ict3Structures[m1Kind] || m1Kind) + ' · cierre M1 ' + ict3Stamp(event.m1_structure_at) + '.'
      : 'M1 es opcional: no sustituye la confirmación M5; no se inventa estructura.',
    {stage: 'm1', key: 'm1'}));

  const stopBasis = String(event.stop_basis || 'NO_STRUCTURAL_STOP');
  const hasStop = stopBasis !== 'NO_STRUCTURAL_STOP' && event.stop_price != null;
  steps.append(ict3Step('Stop informativo', hasStop ? 'observed' : missingStatus,
    hasStop ? 'Stop estructural informativo' : missingState('Esperar stop estructural'),
    ict3Stamp(event.stop_observed_at),
    missingReason((hasStop
      ? (ict3StopBases[stopBasis] || stopBasis) + ' · ' + ict3Price(event.stop_price)
      : ict3Evidence(stopBasis === 'NO_STRUCTURAL_STOP' || !stopBasis ? 'NO_STRUCTURAL_STOP' : 'STRUCTURAL_STOP_NOT_DEFINED')) + '.'),
    {stage: 'stop', key: 'stop', note: 'Referencia informativa: no es una entrada ni un stop operativo.'}));

  const targetLiquidity = Array.isArray(event.target_liquidity) ? event.target_liquidity : [];
  const targetLiquidityAt = (targetLiquidity.find(item => event.target_price != null
    && Number(item.price) === Number(event.target_price)) ?? targetLiquidity[0])?.observed_at;
  steps.append(ict3Step('Objetivos (3R / 5R)', targetOk ? 'observed' : missingStatus,
    targetOk ? 'Objetivo simulado alcanzado' : missingState('Esperar objetivo'),
    ict3Stamp(targetLiquidityAt),
    missingReason(targetText + (event.target_price != null ? ' · liquidez ' + ict3Price(event.target_price) : '')
      + ' · ' + targetLiquidity.length + ' nivel(es) conocido(s) al corte.'),
    {stage: 'targets', key: 'objetivos', note: 'Simulación: R usa una referencia estructural, no una entrada. No es una promesa.'}));

  const lastReason = lastTransition ? ict3Reason(lastTransition.reason) : '';
  steps.append(ict3Step('Invalidación y cierre', closed ? 'closed' : pending.length ? 'wait' : 'observed',
    closed ? 'Lectura invalidada o cerrada' : pending.length ? 'Esperar evidencia' : 'Sin invalidación observada',
    ict3Stamp(lastTransition?.at ?? event.state_time),
    [lastReason, ...pending.map(ict3Evidence)].filter(Boolean).join(' · ') || 'Sin motivo registrado.',
    {stage: 'invalidation', key: 'invalidacion'}));

  card.append(steps);

  const provenance = document.createElement('div');
  provenance.className = 'ict3-provenance';
  const observed = [
    acceptedAt ? 'ruptura ' + ict3Stamp(acceptedAt) : null,
    event.retest_at ? 'retest ' + ict3Stamp(event.retest_at) : null,
    event.defense_at ? 'defensa M5 ' + ict3Stamp(event.defense_at) : null,
    m5Kind ? 'estructura M5 ' + ict3Stamp(event.m5_structure_at) : null,
    m1Kind ? 'M1 ' + ict3Stamp(event.m1_structure_at) : null,
    hasStop ? 'stop ' + ict3Stamp(event.stop_observed_at) : null,
  ].filter(Boolean);
  provenance.append(
    ict3Band('observed', 'Observado', observed.length
      ? observed.join(' · ') + '. Todo procede de velas cerradas al corte.'
      : 'Todavía no hay evidencia cerrada observable en este expediente.'),
    ict3Band('hypothesis', 'Hipótesis', waiting
      ? 'Si aparece la evidencia pendiente, el expediente podría avanzar de estado; hoy no hay entrada confirmada.'
        + (primary ? ' La zona ' + (primary.kind || 'POI').toUpperCase() + ' sigue siendo candidata, no una entrada.' : '')
      : closed
        ? 'Caso cerrado: la lectura no se reabre con datos posteriores. No se plantea escenario nuevo.'
        : 'Lectura descriptiva coherente con la evidencia cerrada, sin autorización de entrada.'),
    ict3Band('simulation', 'Simulación', 'Objetivo informativo TP1 ≥ 3R y TP2 ≥ 5R calculado con liquidez conocida. '
      + 'Estado: ' + targetText + '. R se mide desde una referencia estructural, no desde una entrada. No es una orden.'),
  );
  card.append(provenance);

  if (waiting) {
    const wait = document.createElement('p');
    wait.className = 'ict3-wait';
    wait.setAttribute('role', 'status');
    const strong = document.createElement('strong');
    strong.textContent = 'Esperar';
    wait.append(strong, document.createTextNode(' · faltan: ' + pending.map(ict3Evidence).join('; ') + '. No se presenta una entrada.'));
    card.append(wait);
  } else if (closed) {
    const closedNote = document.createElement('p');
    closedNote.className = 'ict3-wait ict3-wait--closed';
    const strong = document.createElement('strong');
    strong.textContent = 'Caso cerrado';
    closedNote.append(strong, document.createTextNode(' · ' + (ict3EventStates[state] || state) + '. Motivo: '
      + (lastReason || pending.map(ict3Evidence).join('; ') || 'sin motivo registrado') + '.'));
    card.append(closedNote);
  }

  return card;
}

function renderIct3EventFicha(events, result, scope) {
  $('ict3Final').replaceChildren(...events.map(event => ict3EventCard(event, scope)));
  const waiting = events.filter(event => !ict3ClosedStates.has(String(event.current_state))
    && String(event.current_state) !== 'OBSERVABLE_SETUP'
    && (event.pending_evidence || []).length).length;
  const asof = result?.asof ?? events.map(event => event.state_time).filter(Boolean).at(-1);
  message('ict3DetailStatus', scope.symbol + ' · ' + events.length
    + (events.length === 1 ? ' expediente ICT 3.0 · ' : ' expedientes ICT 3.0 · ')
    + (waiting ? 'esperando evidencia en ' + waiting : 'sin esperas')
    + (asof ? ' · actualizado al ' + chartTime(asof) : ' · sin hora de actualización'));
}

function renderIct3Detail(result, scope) {
  if ($('analysisSymbol').value !== scope.symbol) return;
  const ict3Events = result?.ict3?.events ?? [];
  if (ict3Events.length) {
    renderIct3EventFicha(ict3Events, result, scope);
    return;
  }
  const events = (result?.ict3_breaks ?? []).slice().sort((a, b) => a.signal_close - b.signal_close);
  const latest = events.at(-1);
  const daily = result.daily_liquidity || {};
  const regimes = result.regime || {};
  const direction = {BULLISH: 'alcista', BEARISH: 'bajista', RANGING: 'lateral'};
  const bias = direction[result.bias] || 'sin dirección clara';
  const aligned = regimes.D1 === regimes.H4 && regimes.H4 === regimes.H1;
  let verdict = 'Esperar: todavía no hay una entrada confirmada.';
  let liquidity = 'El precio no ha dejado un rompimiento diario reciente que el motor considere decisivo.';
  let next = 'Esperar una reacción clara en el máximo o mínimo del día anterior y después una confirmación en M5/M1.';
  let invalidation = 'No anticipar dirección mientras el precio permanezca entre las referencias del día anterior.';
  let tone = 'wait';
  if (latest?.state === 'ACCEPTED_BREAK_WAIT_RETEST') {
    const side = latest.level_name === 'PDH' ? 'máximo' : 'mínimo';
    verdict = 'Rompimiento aceptado; no perseguir el precio.';
    liquidity = 'El mercado cerró fuera del ' + side + ' del día anterior. La continuación sigue siendo posible, pero falta un retorno ordenado.';
    next = 'Esperar el regreso al FVG u OB que originó el impulso y exigir confirmación en M5/M1 antes de considerar una idea.';
    invalidation = 'La lectura pierde validez si el precio vuelve a cerrar dentro del rango anterior y no logra defender el nivel roto.';
    tone = 'ready';
  } else if (latest?.state === 'FAILED_BREAK') {
    const side = latest.level_name === 'PDH' ? 'máximo' : 'mínimo';
    verdict = 'Último intento fallido: conviene esperar.';
    liquidity = 'El precio intentó superar el ' + side + ' del día anterior, pero volvió al rango. Por ahora no hay continuación aceptada.';
    next = 'Esperar un nuevo desplazamiento con cierre sostenido, o una reacción contraria con cambio de estructura antes de plantear escenario.';
    invalidation = 'No tratar la mecha aislada como ruptura ni entrar sólo porque el nivel fue tocado.';
  }
  const context = 'El sesgo general es ' + bias + '. ' + (aligned
    ? 'D1, H4 y H1 apuntan en la misma dirección.'
    : 'Las temporalidades principales no están completamente alineadas, por lo que la lectura exige más paciencia.');
  const levels = daily.pdh != null && daily.pdl != null
    ? ' Referencias vigentes: máximo anterior ' + price(daily.pdh) + ' y mínimo anterior ' + price(daily.pdl) + '.' : '';
  $('ict3Final').replaceChildren(
    analysisCard(scope.symbol, verdict, 'verdict ' + tone),
    analysisCard('Contexto', context + levels),
    analysisCard('Qué está diciendo la liquidez', liquidity),
    analysisCard('Qué debe pasar ahora', next),
    analysisCard('Cuándo descartar la lectura', invalidation),
  );
  message('ict3DetailStatus', 'Lectura de M15 actualizada al ' + chartTime(result.asof));
}

let detailRequest = 0;
async function loadDetailedAnalysis() {
  const symbol = $('analysisSymbol').value || 'EURUSD';
  const request = ++detailRequest;
  $('ict3Final').replaceChildren();
  message('ict3DetailStatus', 'Preparando el análisis final de ' + symbol + '…');
  try {
    const result = await api('/api/ict?' + new URLSearchParams({symbol, tf: 'M15'}));
    if (request === detailRequest) renderIct3Detail(result, {symbol, tf: 'M15'});
  } catch (error) {
    if (request === detailRequest) message('ict3DetailStatus', 'No se pudo analizar ' + symbol + ': ' + error.message, true);
  }
}

function activateAppTab(name, focus = false) {
  const tabs = [['market', 'marketTab', 'marketPanel'], ['analysis', 'analysisTab', 'analysisPanel'],
    ['journal', 'journalTab', 'journalPanel']];
  for (const [key, tabId, panelId] of tabs) {
    const active = key === name;
    const tab = $(tabId);
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
    $(panelId).hidden = !active;
    if (active && focus) tab.focus();
  }
  if (name === 'market') {
    requestAnimationFrame(render);
  }
}
function selectedBook22() {
  return ictData?.book22?.find(setup => setup.id === $('book22Signal').value);
}
function book22Prices(setup) {
  const format = value => value.toFixed(chartData.digits);
  return [setup.entry != null && 'Referencia ' + format(setup.entry),
    setup.sl != null && 'SL ' + format(setup.sl),
    setup.tp != null && 'TP ' + format(setup.tp) + ' (' + setup.target + ')',
    setup.rr != null && setup.rr.toFixed(2) + 'R'].filter(Boolean);
}
function book22Description(setup) {
  return [book22States[setup.status], book22Reasons[setup.reason], ...book22Prices(setup)].join(' · ');
}
function showBook22Status() {
  const setup = selectedBook22();
  message('book22Status', setup
    ? (setup.direction === 1 ? 'Compra' : 'Venta') + ' · ' + book22Alignments[setup.alignment]
      + ' · ' + book22Description(setup)
    : 'Sin barridos ni rupturas de dos cierres en el historial M15 disponible.');
  showBook22Detail(setup);
}
function showBook22Detail(setup) {
  const title = $('book22DetailTitle');
  const list = $('book22DetailRows');
  list.replaceChildren();
  if (!setup || (reviewAt && setup.evaluated > reviewAt)) {
    title.textContent = 'Selecciona una marca M15 o una señal disponible al corte.';
    return;
  }
  const format = value => value.toFixed(chartData.digits);
  const dated = time => new Date(time * 1000).toISOString().slice(0, 16).replace('T', ' ') + ' MT5';
  title.textContent = (setup.direction === 1 ? 'Compra' : 'Venta') + ' · ' + book22Models[setup.model]
    + ' · ' + book22States[setup.status];
  const item = (key, value) => {
    const term = document.createElement('dt');
    const data = document.createElement('dd');
    term.textContent = key;
    data.textContent = value;
    list.append(term, data);
  };
  item('Instrumento', chartScope.symbol + ' · M15' + (reviewAt ? ' · revisión hasta ' + dated(reviewAt) : ''));
  item('Vela de señal', 'Cerró ' + dated(setup.signal_close));
  item('Evaluación', dated(setup.evaluated) + ' · ' + (book22Reasons[setup.reason] ?? setup.reason));
  item('Contexto al cierre', setup.side + ' ' + format(setup.level)
    + (setup.source_d1 ? ' · D1 de ' + dated(setup.source_d1).slice(0, 10) : '')
    + ' · ' + book22Alignments[setup.alignment]);
  if (setup.zone_low != null && setup.zone_high != null) {
    item('Zona M15', (setup.zone === 'order_block' ? 'OB' : setup.zone?.toUpperCase() ?? 'Zona')
      + ' ' + priceRange(setup.zone_low, setup.zone_high)
      + (setup.confirmation ? ' · confirmada ' + dated(setup.confirmation) : ''));
    if (setup.displacement_close) item('Desplazamiento', 'Cerró ' + dated(setup.displacement_close));
    if (setup.retest) item('Retesteo', dated(setup.retest)
      + (setup.retest_level != null ? ' · punto medio ' + format(setup.retest_level) : ''));
  } else {
    item('Zona M15', 'Sin FVG u OB confirmado en la evaluación.');
  }
  if (setup.sl != null) {
    const basis = {sweep_wick: 'mecha del barrido', m15_swing: 'swing M15'}[setup.stop_basis];
    item('Invalidación del plan', 'SL ' + format(setup.sl) + (basis ? ' · ' + basis + ' ' + format(setup.stop_anchor) : ''));
  } else item('Invalidación del plan', 'Sin SL estructural calculado.');
  if (setup.entry != null) item('Entrada de referencia', format(setup.entry)
    + (setup.reference_open ? ' · apertura de ' + dated(setup.reference_open) : ''));
  if (setup.tp != null) item('Objetivo', format(setup.tp) + ' · ' + setup.target);
  if (setup.rr != null) item('Relación', setup.rr.toFixed(2) + 'R');
  item('Calidad de datos', 'Velas M15 cerradas de MT5. '
    + (setup.entry == null ? 'Entrada pendiente o descartada.' : setup.reference_spread == null
      ? 'Referencia teórica. Spread histórico sin detallar.' :
      'Referencia teórica con spread histórico aproximado de ' + format(setup.reference_spread) + '.'));
  if (setup.status === 'qualified') item('Alcance', 'Cumplimiento al cierre de evaluación. Evolución posterior sin evaluar.');
}
function openBook22Tab(detail, focus = false) {
  $('book22Overview').hidden = detail;
  $('book22Detail').hidden = !detail;
  for (const [id, active] of [['book22OverviewTab', !detail], ['book22DetailTab', detail]]) {
    const tab = $(id);
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
    if (active && focus) tab.focus();
  }
}
function updateBook22() {
  const select = $('book22Signal');
  $('book22Panel').hidden = chartScope.tf !== 'M15';
  if ($('book22Panel').hidden) return;
  const setups = ictData.book22 ?? [];
  const newest = setups.slice().reverse();
  const options = newest.map(setup => new Option(
    chartTime(setup.signal_close) + ' · ' + book22Models[setup.model] + ' ' + setup.side,
    setup.id));
  if (!options.length) options.push(new Option('Sin señales en el historial', ''));
  select.replaceChildren(...options);
  select.disabled = !newest.length;
  select.value = newest.some(setup => setup.id === book22Selection) ? book22Selection : options[0].value;
  showBook22Status();
}

function showDailyLiquidity(daily) {
  if (!daily) {
    message('dailyLevels', 'La última D1 cerrada no está disponible.');
    message('dailyEvents', '');
    return;
  }
  const date = new Date(daily.source_open * 1000).toISOString().slice(0, 10);
  const wickTime = time => time == null ? 'mecha sin verificar' : dateFormat.format(new Date(time * 1000));
  const wick = chartScope.tf === 'M15';
  message('dailyLevels', 'D1 ' + date + ' MT5 · PDH ' + price(daily.pdh)
    + (wick ? ' (' + wickTime(daily.pdh_m15_open) + ')' : '')
    + ' · PDL ' + price(daily.pdl) + (wick ? ' (' + wickTime(daily.pdl_m15_open) + ')' : ''));
  const eventNames = {
    sweep: 'Barrido', break: 'Ruptura al cierre', late_return: 'Retorno tardío',
    boundary_close: 'Cierre en el nivel', both: 'Ambos extremos', gap: 'Apertura fuera',
  };
  const events = daily.events.filter(event => event.kind !== 'touch').slice(-4)
    .map(event => eventNames[event.kind] + (event.level ? ' ' + event.level : '')
      + ' · ' + dateFormat.format(new Date(event.time * 1000)));
  const touches = daily.events.filter(event => event.kind === 'touch');
  const empty = touches.length ? 'Solo toques, sin barrido ni ruptura' : 'Sin toques, barrido ni ruptura';
  message('dailyEvents', 'M15 · ' + daily.m15_count + ' velas cerradas · '
    + (events.length ? events.join(' / ') : daily.m15_count ? empty : 'Esperando el primer cierre de la jornada'));
}

function showFridayReference(friday) {
  if (!friday) {
    message('fridayLevels', 'Referencia semanal · todavía no hay un viernes D1 cerrado disponible.');
    return;
  }
  const date = new Date(friday.source_open * 1000).toISOString().slice(0, 10);
  message('fridayLevels', 'Último viernes D1 ' + date + ' MT5 · F-HH ' + price(friday.high)
    + ' · F-LL ' + price(friday.low));
}

async function refreshOpenings(payload = null) {
  const symbol = chartScope?.symbol;
  if (!payload && (marketAvailable && !reviewAt || !marketAvailable && !openingSymbols.has(symbol))) return;
  if (!symbol || readingOpenings.has(symbol)) return;
  readingOpenings.add(symbol);
  try {
    const result = payload ?? await api('/api/openings?' + new URLSearchParams({symbol}));
    if (chartScope.symbol !== result.symbol) return;
    openings = result;
    const day = reviewAt ? new Date(reviewAt * 1000).toISOString().slice(0, 10) : result.today;
    const today = result.checks.filter(check => check.session_date === day
      && (!reviewAt || check.open + frameSeconds.M15 <= reviewAt));
    const labels = {
      upcoming: 'pendiente', waiting_close: 'esperando cierre',
      missing: 'vela de apertura no disponible',
    };
    const summary = today.map(check => {
      const range = check.high != null && check.low != null
        ? 'máx. ' + check.high.toFixed(chartData.digits) + ' · mín. ' + check.low.toFixed(chartData.digits)
        : labels[check.status];
      return check.name + ' · ' + chartTime(check.open) + ' · ' + range;
    });
    message('openingSchedule', summary.join(' / '));
    const rangeEvents = today.flatMap(check => (check.events ?? [])
      .filter(event => !reviewAt || event.open + frameSeconds.M15 <= reviewAt)
      .map(event => ({check, event})));
    const latest = Math.max(-Infinity, ...rangeEvents.map(({event}) => event.open));
    let notice = rangeEvents.length
      ? chartTime(latest + frameSeconds.M15) + ' · ' + rangeEvents.filter(({event}) => event.open === latest)
        .map(({check, event}) => openingRangeLabel(check, event)).join(' · ')
      : today.some(check => check.high != null) ? 'Sin barrido ni ruptura confirmados en los rangos de apertura.' : '';
    if (symbol === 'EURUSD' && !reviewAt) {
      const newest = today.findLast(check => check.alerts?.length
        && Date.now() >= check.close_utc * 1000 && Date.now() - check.close_utc * 1000 <= 240000);
      if (newest) lastOpeningNotice = newest;
      if (lastOpeningNotice?.session_date === day && lastOpeningNotice.open > latest) {
        notice = 'Cierre de ' + lastOpeningNotice.name + ' · ' + lastOpeningNotice.alerts.join(' · ');
      }
    }
    if ($('openingNotice').textContent !== notice) message('openingNotice', notice);
    render();
  } catch (error) {
    if (chartScope?.symbol === symbol) message('openingSchedule', error.message, true);
  } finally {
    readingOpenings.delete(symbol);
  }
}

function openingRangeLabel(check, event) {
  const kind = event.kind === 'sweep' ? 'Barrido' : 'Ruptura';
  return kind + ' del ' + (event.side === 'high' ? 'alto' : 'bajo') + ' de ' + check.name;
}

function scopeKey(scope) {
  return scope.symbol + '/' + scope.tf;
}
function activeNotes() {
  return chartScope ? notes[scopeKey(chartScope)] || [] : [];
}
function line(ax, ay, bx, by, color) {
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.moveTo(ax, ay);
  ctx.lineTo(bx, by);
  ctx.stroke();
}
function label(text, x, y, color = '#a6b6ca') {
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
}
const zoneNames = {FVG: 'FVG · desequilibrio de precio', OB: 'OB · bloque de órdenes',
  POI: 'POI candidato', CHOCH: 'CHOCH · cambio de carácter', BOS: 'BOS · ruptura de estructura'};

function chartTime(time) {
  return dateFormat.format(new Date(time * 1000)) + ' · hora MT5';
}
function priceRange(low, high) {
  return low.toFixed(chartData.digits) + ' – ' + high.toFixed(chartData.digits);
}
function boxHint(g, x, y, width, height, info, padding = 3) {
  g.hints.push({info, contains: (px, py) => px >= x - padding && px <= x + width + padding
    && py >= y - padding && py <= y + height + padding});
}
function lineHint(g, x1, y1, x2, y2, info) {
  const dx = x2 - x1, dy = y2 - y1;
  const lengthSquared = dx * dx + dy * dy || 1;
  g.hints.push({info, contains: (x, y) => {
    const t = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / lengthSquared));
    return Math.hypot(x - x1 - t * dx, y - y1 - t * dy) <= 5;
  }});
}
function candleHint(g, x, y) {
  const row = g.rows[Math.floor((x - g.left) / g.step)];
  if (!row) return null;
  const [at, open, high, low, close] = row;
  if (y < g.y(high) - 3 || y > g.y(low) + 3) return null;
  const formatted = [open, high, low, close].map(value => value.toFixed(chartData.digits));
  return {title: 'Vela', tf: chartScope.tf, details: [chartTime(at),
    'Apertura ' + formatted[0] + ' · Máximo ' + formatted[1],
    'Mínimo ' + formatted[2] + ' · Cierre ' + formatted[3]]};
}
function updateChartTooltip() {
  const g = geometry;
  if (!g || !chartHover || drag) {
    chartTooltip.hidden = true;
    return;
  }
  const bounds = canvas.getBoundingClientRect();
  const x = chartHover.x - bounds.left, y = chartHover.y - bounds.top;
  let info;
  if (x >= g.left && x <= g.width && y >= g.top && y <= g.bottom) {
    info = g.hints.findLast(hint => hint.contains(x, y))?.info ?? candleHint(g, x, y);
  }
  chartTooltip.hidden = !info;
  if (!info) return;
  $('chartTooltipTitle').textContent = info.title;
  $('chartTooltipFrame').textContent = info.tf;
  $('chartTooltipDetails').textContent = info.details.filter(Boolean).join('\n');
  const right = window.innerWidth - chartTooltip.offsetWidth - 8;
  const below = chartHover.y + 15;
  const above = chartHover.y - chartTooltip.offsetHeight - 12;
  chartTooltip.style.left = Math.max(8, Math.min(right, chartHover.x + 13)) + 'px';
  chartTooltip.style.top = (below + chartTooltip.offsetHeight <= window.innerHeight - 8
    ? below : Math.max(8, above)) + 'px';
}
function clearChartHover() {
  chartHover = null;
  chartTooltip.hidden = true;
}
function drawMark(mark, g) {
  const {kind, first, second} = mark;
  if (kind !== 'Nivel' && first.t > g.end) return;
  const x = g.where(first.t);
  const y = g.y(first.p);
  const info = {title: kind === 'POI' ? 'POI candidato · manual' : kind + ' · manual',
    tf: chartScope.tf, details: [second
      ? priceRange(Math.min(first.p, second.p), Math.max(first.p, second.p))
      : first.p.toFixed(chartData.digits), mark.label]};
  if (kind === 'POI') {
    const bottom = g.y(second.p);
    const left = Math.max(g.left, x - g.step / 2);
    const top = Math.min(y, bottom);
    ctx.fillStyle = 'rgba(234, 185, 89, .19)';
    ctx.fillRect(left, top, g.width - left, Math.abs(bottom - y));
    ctx.strokeStyle = '#eab959';
    ctx.strokeRect(left, top, g.width - left, Math.max(1, Math.abs(bottom - y)));
    boxHint(g, left, top, g.width - left, Math.abs(bottom - y), info);
    if (mark.label) label(mark.label.slice(0, 46), left + 4, top + 13, '#eab959');
  } else if (kind === 'Nivel') {
    line(g.left, y, g.width, y, '#eab959');
    lineHint(g, g.left, y, g.width, y, info);
    if (mark.label) label(mark.label.slice(0, 46), g.left + 4, y - 4, '#eab959');
  } else if (kind === 'Tendencia') {
    if (Math.max(first.t, second.t) >= g.start) {
      const endX = g.where(second.t), endY = g.y(second.p);
      line(x, y, endX, endY, '#bba3f7');
      lineHint(g, x, y, endX, endY, info);
    }
  } else if (first.t >= g.start) {
    const caption = '◆ ' + (mark.label || 'Idea').slice(0, 42);
    label(caption, x, y, '#eab959');
    boxHint(g, x, y - 10, ctx.measureText(caption).width, 12, info);
  }
}
function drawTrades(g) {
  if (!journal || !$('showDeals').checked) return;
  for (const deal of journal.deals) {
    if (reviewAt && deal.time === reviewAt && deal.symbol === chartScope.symbol && deal.entry === 0
        && [0, 1].includes(deal.type) && deal.price >= g.min && deal.price <= g.max
        && g.visibleUntil <= reviewAt && g.visibleUntil + frameSeconds[chartScope.tf] > reviewAt) {
      drawTradeMarker(g, deal, g.dataRight + g.step / 2, g.y(deal.price));
      continue;
    }
    if (deal.symbol !== chartScope.symbol || !deal.position_id || ![0, 1].includes(deal.type)
        || deal.time < g.start || deal.time >= g.visibleUntil || (reviewAt && deal.time > reviewAt)) continue;
    drawTradeMarker(g, deal, g.where(deal.time), g.y(deal.price));
  }
}
function drawTradeMarker(g, deal, x, y) {
  const isOpen = deal.entry === 0;
  label(isOpen ? (deal.type === 0 ? '▲' : '▼') : '×', x - 4, y + 4,
    isOpen ? '#8fc3ff' : '#ffc395');
  boxHint(g, x - 5, y - 6, 10, 12, {
    title: isOpen ? (deal.type === 0 ? 'Compra · entrada MT5' : 'Venta · entrada MT5') : 'Salida · MT5',
    tf: chartScope.tf + ' · vista del gráfico',
    details: [chartTime(deal.time), deal.price.toFixed(chartData.digits) + ' · ' + deal.volume + ' lotes'],
  });
}
function drawIct(g) {
  if (!ictData) return;
  const show = {FVG: $('ictFvg').checked, OB: $('ictOb').checked, POI: $('ictPoi').checked};
  const visible = mark => mark.high >= g.min && mark.low <= g.max && mark.confirmed <= g.visibleUntil;
  const shapes = ['FVG', 'OB'].flatMap(kind => !show[kind] ? []
    : ictData.marks.filter(mark => mark.kind === kind && visible(mark)
      && (mark.touch ?? g.visibleUntil) >= g.start).slice(-12));
  if (show.POI) shapes.push(...ictData.pois.filter(visible));
  for (const mark of shapes) {
    // The mark starts after the confirmation candle closed. POI annotations
    // also wait for their parent structure to have been confirmed.
    const from = Math.max(mark.confirmed, mark.anchor?.time ?? 0);
    if (from >= g.visibleUntil) continue;
    const x = Math.max(g.left, g.where(from) - g.step / 2);
    const right = mark.touch && mark.touch < g.visibleUntil
      ? Math.min(g.width, g.where(mark.touch) + g.step / 2) : g.width;
    const top = g.y(mark.high), height = Math.max(1, g.y(mark.low) - top);
    if (right <= x) continue;
    const color = ictColors[mark.kind];
    ctx.fillStyle = color + (mark.kind === 'POI' ? '38' : '1d');
    ctx.fillRect(x, top, right - x, height);
    ctx.strokeStyle = color;
    ctx.setLineDash(mark.touch ? [3, 3] : []);
    ctx.strokeRect(x, top, right - x, height);
    ctx.setLineDash([]);
    boxHint(g, x, top, right - x, height, {
      title: zoneNames[mark.kind] ?? mark.kind, tf: mark.tf,
      details: [priceRange(mark.low, mark.high) + (mark.direction > 0 ? ' · alcista'
        : mark.direction < 0 ? ' · bajista' : ''),
        mark.base ? 'Zona de origen · ' + mark.base : null,
        'Confirmación · ' + chartTime(mark.confirmed),
        mark.touch ? 'Primer toque · ' + chartTime(mark.touch) : null],
    });
    if (height >= 13 && right - x >= 45) {
      const title = mark.kind + (mark.kind === 'POI' ? ' ' + mark.tf : '') + (mark.direction > 0 ? ' ↑' : ' ↓');
      label(title, x + 4, top + 11, color);
    }
  }
}
function drawDailyLevels(g, daily) {
  if (!daily) return;
  const tf = chartScope.tf;
  const levels = [
    {name: 'PDH', value: daily.pdh, color: '#85baff', wick: daily.pdh_m15_open, labelOffset: -6},
    {name: 'PDL', value: daily.pdl, color: '#f1a9d8', wick: daily.pdl_m15_open, labelOffset: 14},
  ];
  ctx.save();
  ctx.lineWidth = 1.5;
  for (const {name, value, color, wick, labelOffset} of levels) {
    const anchor = tf === 'D1' ? daily.source_open : wick;
    const from = anchor ?? daily.session_open;
    if (from > g.visibleUntil || (from === g.visibleUntil && anchor !== null)) continue;
    const start = from === g.visibleUntil ? g.dataRight : Math.max(g.left, g.where(from));
    const y = g.y(value);
    const onScale = y >= g.top && y <= g.bottom;
    if (onScale) {
      ctx.setLineDash([5, 4]);
      line(start, y, g.width, y, color);
      ctx.setLineDash([]);
      if (anchor !== null && (tf === 'D1' || tf === 'M15') && g.rows.some(row => row[0] === anchor)) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(start, y, 2.5, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
    const edge = y < g.top
      ? g.top + (name === 'PDL' && daily.pdh > g.max ? 28 : 12)
      : g.bottom - (name === 'PDH' && daily.pdl < g.min ? 19 : 3);
    const caption = (onScale ? '' : y < g.top ? '↑ ' : '↓ ') + name + ' ' + value.toFixed(chartData.digits);
    const baseline = onScale
      ? Math.max(g.top + 12, Math.min(g.bottom - 3, y + labelOffset))
      : edge;
    const width = ctx.measureText(caption).width + 10;
    g.levelLabels.push({left: g.width - width - 2, right: g.width - 2, baseline});
    ctx.fillStyle = '#101722';
    ctx.fillRect(g.width - width - 2, baseline - 11, width, 15);
    ctx.textAlign = 'right';
    label(caption, g.width - 7, baseline, color);
    const info = {title: name + (name === 'PDH' ? ' · máximo del día anterior' : ' · mínimo del día anterior'),
      tf: 'D1', details: [value.toFixed(chartData.digits), 'Vela diaria · ' + chartTime(daily.source_open),
        wick != null ? 'Mecha M15 · ' + chartTime(wick) : null]};
    if (onScale) lineHint(g, start, y, g.width, y, info);
    boxHint(g, g.width - width - 2, baseline - 11, width, 15, info, 0);
  }
  ctx.restore();
}

function drawFridayReference(g, friday) {
  if (!friday) return;
  const levels = [
    {name: 'F-HH', value: friday.high, color: '#f5c86b', labelOffset: -7},
    {name: 'F-LL', value: friday.low, color: '#67d7cf', labelOffset: 14},
  ];
  ctx.save();
  ctx.lineWidth = 1.5;
  for (const {name, value, color, labelOffset} of levels) {
    const start = friday.source_open < g.start ? g.left : Math.max(g.left, g.where(friday.source_open));
    const y = g.y(value);
    const onScale = y >= g.top && y <= g.bottom;
    if (onScale) {
      ctx.setLineDash([9, 4, 2, 4]);
      line(start, y, g.width, y, color);
      ctx.setLineDash([]);
    }
    const edge = y < g.top ? g.top + (name === 'F-LL' ? 44 : 28)
      : g.bottom - (name === 'F-HH' ? 35 : 19);
    const caption = (onScale ? '' : y < g.top ? '↑ ' : '↓ ') + name + ' ' + value.toFixed(chartData.digits);
    const baseline = onScale
      ? Math.max(g.top + 12, Math.min(g.bottom - 3, y + labelOffset))
      : edge;
    const width = ctx.measureText(caption).width + 10;
    g.levelLabels.push({left: g.width - width - 2, right: g.width - 2, baseline});
    ctx.fillStyle = '#101722';
    ctx.fillRect(g.width - width - 2, baseline - 11, width, 15);
    ctx.textAlign = 'right';
    label(caption, g.width - 7, baseline, color);
    const info = {title: name + (name === 'F-HH' ? ' · máximo del último viernes' : ' · mínimo del último viernes'),
      tf: 'D1', details: [value.toFixed(chartData.digits), 'Viernes D1 · ' + chartTime(friday.source_open)]};
    if (onScale) lineHint(g, start, y, g.width, y, info);
    boxHint(g, g.width - width - 2, baseline - 11, width, 15, info, 0);
  }
  ctx.restore();
}

function drawBook22(g, selected) {
  if (chartScope.tf !== 'M15' || !$('showBook22').checked) return;
  for (const setup of ictData?.book22 ?? []) {
    if (setup.signal_open < g.start || setup.signal_close > g.visibleUntil) continue;
    const x = g.where(setup.signal_open);
    const upper = setup.side === 'PDH';
    const y = upper ? g.top + 13 : g.bottom - 10;
    const color = setup.id === selected?.id ? '#e9eff7'
      : setup.model === 'continuation' ? '#85baff' : '#f4bd69';
    const glyph = setup.model === 'continuation' ? (setup.direction === 1 ? '▲' : '▼') : '◆';
    label(glyph, x - ctx.measureText(glyph).width / 2, y, color);
    const observed = setup.evaluated <= g.visibleUntil;
    boxHint(g, x - Math.min(g.step / 2, 5), y - 10, Math.min(g.step, 10), 12, {
      setupId: setup.id,
      title: (setup.direction === 1 ? 'Compra' : 'Venta') + ' · ' + book22Models[setup.model] + ' · ' + setup.side,
      tf: 'M15 · ' + book22Alignments[setup.alignment],
      details: [chartTime(setup.signal_close),
        observed ? book22Description(setup) : 'La evaluación terminó después de este tramo.', 'Clic para ver el análisis.'],
    }, 0);
  }
  if (!selected) return;
  const start = g.where(selected.signal_open);
  for (const [name, value, color] of [['SL', selected.sl, '#ff9b9b'], ['TP', selected.tp, '#64d6b2']]) {
    if (value == null) continue;
    const rawY = g.y(value);
    const y = Math.max(g.top + 22, Math.min(g.bottom - 20, rawY));
    const caption = name + ' ' + value.toFixed(chartData.digits);
    const outside = rawY < g.top || rawY > g.bottom;
    if (!outside) {
      ctx.setLineDash([3, 4]);
      line(start, rawY, g.width, rawY, color);
      ctx.setLineDash([]);
    }
    const text = outside ? (rawY < g.top ? '↑ ' : '↓ ') + caption : caption;
    const width = ctx.measureText(text).width;
    ctx.fillStyle = '#101824';
    ctx.fillRect(g.width - width - 11, y - 12, width + 9, 14);
    label(text, g.width - width - 6, y - 2, color);
    boxHint(g, g.width - width - 11, y - 12, width + 9, 14,
      {title: caption + ' · Libro 22', tf: 'M15', details: [book22Description(selected)]});
  }
}
function drawOpeningMarks(g) {
  if (openings?.symbol !== chartScope.symbol || chartScope.tf !== 'M15'
      || !$('showOpenings').checked) return;
  const markedCandles = new Map();
  for (const check of openings.checks) {
    const closed = check.open + frameSeconds.M15;
    if (check.high == null || check.low == null || closed > g.visibleUntil
        || (reviewAt && closed > reviewAt) || check.session_end <= g.start) continue;
    const anchorVisible = g.rows.some(row => row[0] === check.open);
    if (!anchorVisible && check.open >= g.start) continue;
    const x = anchorVisible ? g.where(check.open) : g.left;
    const nextDay = g.rows.find(row => row[0] >= check.session_end);
    const end = nextDay ? g.where(nextDay[0]) - g.step / 2
      : check.session_end <= g.visibleUntil ? g.dataRight : g.width;
    if (end <= x) continue;
    const color = check.name === 'Londres' ? '#f1bd69' : '#cb9fff';
    for (const event of check.events ?? []) {
      if (event.open + frameSeconds.M15 > Math.min(g.visibleUntil, reviewAt ?? Infinity)
          || !g.rows.some(row => row[0] === event.open)) continue;
      const key = event.open + '/' + event.side;
      if (!markedCandles.has(key)) markedCandles.set(key, []);
      markedCandles.get(key).push({check, event, color});
    }
    if (anchorVisible && chartScope.symbol === 'EURUSD' && check.alerts?.length) {
      const width = Math.max(5, g.step * .9);
      const y = g.y(check.high);
      const height = Math.max(3, g.y(check.low) - y);
      ctx.fillStyle = color + '40';
      ctx.fillRect(x - width / 2, y, width, height);
      ctx.strokeStyle = color;
      ctx.strokeRect(x - width / 2, y, width, height);
      boxHint(g, x - width / 2, y, width, height, {
        title: 'Confirmación de apertura · ' + check.name, tf: 'M15',
        details: [...check.alerts, 'Cierre · ' + chartTime(closed)],
      });
    }
    for (const [name, value, shift] of [['Máximo', check.high, -5], ['Mínimo', check.low, 13]]) {
      const y = g.y(value);
      if (y < g.top || y > g.bottom) continue;
      const formatted = value.toFixed(chartData.digits);
      const info = {title: name + ' de apertura · ' + check.name, tf: 'M15',
        details: [formatted, 'Vela · ' + chartTime(check.open), 'Cierre · ' + chartTime(closed),
          ...(check.alerts ?? [])]};
      line(x, y, end, y, color);
      lineHint(g, x, y, end, y, info);
      if (anchorVisible) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
        ctx.fill();
      }
      const caption = (check.name === 'Londres' ? 'LON ' : 'NY ') + (name === 'Máximo' ? '↑ ' : '↓ ') + formatted;
      const width = ctx.measureText(caption).width;
      if (end - x > width + 10) {
        const left = end - width - 8;
        const baselines = [y + shift, y + (shift < 0 ? 13 : -5)]
          .map(at => Math.max(g.top + 11, Math.min(g.bottom - 3, at)));
        const baseline = baselines.find(at => !g.levelLabels.some(other =>
          left < other.right && end > other.left && Math.abs(at - other.baseline) < 15));
        if (baseline == null) continue;
        g.levelLabels.push({left, right: end, baseline});
        ctx.fillStyle = '#101722';
        ctx.fillRect(left, baseline - 10, width + 6, 13);
        label(caption, left + 3, baseline, color);
        boxHint(g, left, baseline - 10, width + 6, 13, info, 1);
      }
    }
  }
  for (const group of markedCandles.values()) {
    const {event, color} = group[0];
    const x = g.where(event.open);
    const upper = event.side === 'high';
    const y = Math.max(g.top + 12, Math.min(g.bottom - 3, g.y(event.wick) + (upper ? -5 : 13)));
    const glyph = group.some(mark => mark.event.kind === 'break') ? (upper ? '▲' : '▼') : '◆';
    const glyphWidth = ctx.measureText(glyph).width;
    label(glyph, x - glyphWidth / 2, y, group.length > 1 ? '#e9eff7' : color);
    boxHint(g, x - glyphWidth / 2, y - 10, glyphWidth, 12, {
      title: 'Libro 22 · Rango de apertura', tf: 'M15',
      details: [...group.map(mark => openingRangeLabel(mark.check, mark.event)
        + ' · ' + mark.event.level.toFixed(chartData.digits)),
      'Cierre ' + event.close.toFixed(chartData.digits) + ' · ' + chartTime(event.open + frameSeconds.M15)],
    }, 1);
  }
}
function render() {
  const {clientWidth: width, clientHeight: height} = canvas;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.scale(ratio, ratio);
  ctx.font = (width < 500 ? 12 : 13) + 'px system-ui';
  geometry = null;
  if (!chartData?.rows?.length || width < 120 || height < 120) {
    updateChartTooltip();
    return;
  }
  const left = 12, right = width - (width < 500 ? 76 : 92), top = 20, bottom = height - 39;
  const count = windowSize.value === 'auto'
    ? Math.max(20, Math.floor((right - left) / defaultBarSpacing) - rightMarginBars)
    : Number(windowSize.value);
  const series = chartData.rows;
  offset = Math.min(offset, Math.max(0, series.length - count));
  $('back').disabled = series.length - offset <= count;
  $('forward').disabled = offset === 0;
  $('centerChart').disabled = offset === 0 && !manualPriceRange;
  $('resetPriceScale').disabled = !manualPriceRange;
  const endIndex = series.length - offset;
  const firstIndex = Math.max(0, endIndex - count);
  const rows = series.slice(firstIndex, endIndex);
  const start = rows[0][0], end = rows.at(-1)[0];
  const visibleUntil = Math.min(series[endIndex]?.[0] ?? Infinity, end + frameSeconds[chartScope.tf]);
  const liquidity = ictData?.daily_liquidity;
  const daily = $('showDailyLiquidity').checked && liquidity?.source_open < visibleUntil ? liquidity : null;
  const fridayData = ictData?.friday_reference;
  const friday = $('showFridayReference').checked && fridayData?.source_open < visibleUntil ? fridayData : null;
  const fitLevels = $('fitDailyLevels').checked ? daily : null;
  const fitFriday = $('fitDailyLevels').checked ? friday : null;
  const book22 = chartScope.tf === 'M15' && $('showBook22').checked ? selectedBook22() : null;
  const visibleSetup = book22?.signal_open >= start && book22.evaluated <= visibleUntil ? book22 : null;
  const setupPrices = [visibleSetup?.sl, visibleSetup?.tp].filter(value => value != null);
  const low = Math.min(fitLevels?.pdl ?? Infinity, fitFriday?.low ?? Infinity,
    ...setupPrices, ...rows.map(row => row[3]));
  const high = Math.max(fitLevels?.pdh ?? -Infinity, fitFriday?.high ?? -Infinity,
    ...setupPrices, ...rows.map(row => row[2]));
  const pad = (high - low) * .075 || 10 ** -chartData.digits;
  const {min, max} = manualPriceRange ?? {min: low - pad, max: high + pad};
  const step = (right - left) / (rows.length + rightMarginBars);
  const dataRight = right - rightMarginBars * step;
  const candleX = index => left + (index + .5) * step;
  const y = price => top + (max - price) / (max - min) * (bottom - top);
  const where = time => {
    if (time < start) return left - step;
    if (time >= visibleUntil) return right + step;
    const later = rows.findIndex(row => row[0] > time);
    return candleX(later < 0 ? rows.length - 1 : later - 1);
  };
  const g = {left, width: right, dataRight, top, bottom, rows, count, firstIndex, start, end,
    visibleUntil, step, where, y, min, max, hints: [], levelLabels: []};
  geometry = g;
  const yIntervals = Math.max(4, Math.min(11, Math.floor((bottom - top) / 64)));
  for (let i = 0; i <= yIntervals; i++) {
    const price = min + (max - min) * i / yIntervals;
    const labelY = y(price);
    line(left, labelY, right, labelY, '#26364a');
    line(right, labelY, right + 5, labelY, '#49617d');
    label(price.toFixed(chartData.digits), right + 10, labelY + 4);
  }
  line(left, bottom, right, bottom, '#49617d');
  line(right, top, right, bottom, '#49617d');
  const formatter = chartScope.tf === 'D1' ? dailyAxisFormat : dateFormat;
  const formatTick = index => formatter.format(new Date(rows[index][0] * 1000));
  const labelWidth = Math.max(...[0, Math.floor(rows.length / 2), rows.length - 1]
    .map(index => ctx.measureText(formatTick(index)).width));
  const ticks = Math.min(rows.length, 12, Math.max(2, Math.floor((dataRight - left) / (labelWidth + 24))));
  let lastLabelEnd = -Infinity;
  for (let i = 0; i < ticks; i++) {
    const index = Math.floor((rows.length - 1) * i / Math.max(1, ticks - 1));
    const text = formatTick(index);
    const textWidth = ctx.measureText(text).width;
    const at = candleX(index);
    const x = Math.max(left, Math.min(right - textWidth, at - textWidth / 2));
    if (x < lastLabelEnd + 8) continue;
    line(at, bottom, at, bottom + 5, '#49617d');
    label(text, x, bottom + 23);
    lastLabelEnd = x + textWidth;
  }
  ctx.font = '11px system-ui';
  ctx.save();
  ctx.beginPath();
  ctx.rect(left, top, right - left, bottom - top);
  ctx.clip();
  drawIct(g);
  rows.forEach(([, open, high, low, close], index) => {
    const x = candleX(index);
    const color = close >= open ? '#57cfaa' : '#f18186';
    line(x, y(high), x, y(low), color);
    ctx.fillStyle = color;
    const body = Math.min(20, Math.max(1, step * .68));
    ctx.fillRect(x - body / 2, y(Math.max(open, close)), body, Math.max(1, Math.abs(y(open) - y(close))));
  });
  activeNotes().forEach(mark => drawMark(mark, g));
  drawDailyLevels(g, daily);
  drawFridayReference(g, friday);
  drawOpeningMarks(g);
  drawTrades(g);
  drawBook22(g, visibleSetup);
  if (pending) label('◆', where(pending.t) - 4, y(pending.p) + 4, '#eab959');
  ctx.restore();
  updateChartTooltip();
}

canvas.addEventListener('wheel', event => {
  const g = geometry;
  if (!g || drag || !event.deltaY || event.ctrlKey || event.metaKey) return;
  const bounds = canvas.getBoundingClientRect();
  const x = event.clientX - bounds.left;
  if (x < g.left || x >= g.width) return;
  const fraction = Math.min(1, (x - g.left) / (g.dataRight - g.left));
  event.preventDefault();

  const total = chartData.rows.length;
  const count = g.rows.length;
  const limit = Math.min(20, total);
  const delta = event.deltaY * (event.deltaMode === 1 ? 24 : event.deltaMode === 2 ? 120 : 1);
  const scale = Math.exp(Math.max(-.26, Math.min(.26, delta / 625)));
  const next = Math.max(limit, Math.min(total, Math.round(count * scale)));
  if (next === count) return;

  const anchor = g.firstIndex + fraction * count;
  const nextStep = (g.width - g.left) / (next + rightMarginBars);
  const nextAnchor = Math.min(next, (x - g.left) / nextStep);
  const first = Math.max(0, Math.min(total - next, Math.round(anchor - nextAnchor)));
  offset = total - first - next;
  if ([80, 160, 320].includes(next)) {
    windowSize.value = String(next);
    customWindowSize.hidden = true;
  } else {
    customWindowSize.value = String(next);
    customWindowSize.textContent = String(next);
    customWindowSize.hidden = false;
    windowSize.value = String(next);
  }
  render();
}, {passive: false});

function point(event) {
  const g = geometry;
  if (!g) return null;
  const bounds = canvas.getBoundingClientRect();
  const x = event.clientX - bounds.left, y = event.clientY - bounds.top;
  if (x < g.left || x >= g.width || y < g.top || y > g.bottom) return null;
  const at = Math.floor((x - g.left) / g.step);
  const price = g.max - (y - g.top) / (g.bottom - g.top) * (g.max - g.min);
  return {t: g.rows[at]?.[0] ?? null, p: Number(price.toFixed(chartData.digits))};
}
async function changeNote(scope, payload) {
  if (editing || !scope) return false;
  editing = true;
  try {
    notes = await api('/api/notes', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...scope, ...payload}),
    });
    message('markStatus', 'Marcajes guardados en esta PC.');
    drawNotes();
    render();
    return true;
  } catch (error) {
    message('markStatus', error.message, true);
    return false;
  } finally {
    editing = false;
  }
}
function drawNotes() {
  const container = $('marks');
  container.replaceChildren();
  for (const mark of [...activeNotes()].reverse()) {
    const scope = chartScope;
    const box = document.createElement('div');
    box.className = 'mark';
    const title = document.createElement('strong');
    const kind = mark.kind === 'POI' ? 'POI candidato' : mark.kind;
    title.textContent = kind + ' · ' + mark.first.p + (mark.second ? ' / ' + mark.second.p : '');
    const note = document.createElement('p');
    note.textContent = mark.label || 'Sin nota';
    const edit = document.createElement('button');
    edit.textContent = 'Editar nota';
    edit.addEventListener('click', () => {
      const label = window.prompt('Nota de la idea', mark.label);
      if (label !== null) changeNote(scope, {action: 'update', id: mark.id, label});
    });
    const remove = document.createElement('button');
    remove.textContent = 'Borrar';
    remove.addEventListener('click', () => {
      if (window.confirm('¿Borrar este marcaje?')) changeNote(scope, {action: 'delete', id: mark.id});
    });
    box.append(title, note, edit, remove);
    if (referenceMatches(selectedReference(), scope) && ['Nivel', 'POI'].includes(mark.kind)) {
      for (const [label, point] of mark.kind === 'POI'
        ? [['Comparar límite bajo', mark.first.p <= mark.second.p ? mark.first : mark.second],
          ['Comparar límite alto', mark.first.p <= mark.second.p ? mark.second : mark.first]]
        : [['Comparar nivel', mark.first]]) {
        const compare = document.createElement('button');
        compare.textContent = label;
        compare.addEventListener('click', () => recordReferenceMeasurement(scope, {
          time: point.t, price: point.p, field: label.replace('Comparar ', '') + ' del marcaje MT5',
        }));
        box.append(compare);
      }
    }
    container.append(box);
  }
}

function overPriceAxis(event) {
  const g = geometry;
  if (!g) return false;
  const bounds = canvas.getBoundingClientRect();
  const x = event.clientX - bounds.left, y = event.clientY - bounds.top;
  return x >= g.width && x < bounds.width && y >= g.top && y <= g.bottom;
}
function book22At(event) {
  if (chartScope?.tf !== 'M15' || !geometry) return null;
  const bounds = canvas.getBoundingClientRect();
  return geometry.hints.findLast(hint => hint.info.setupId
    && hint.contains(event.clientX - bounds.left, event.clientY - bounds.top))?.info.setupId;
}
canvas.addEventListener('pointerdown', event => {
  if (event.pointerType !== 'mouse' || event.button !== 0) return;
  const axis = overPriceAxis(event);
  if (!axis && !$('tool').value && book22At(event)) return;
  if (!axis && ($('tool').value || !point(event))) return;
  const g = geometry;
  clearChartHover();
  const span = g.max - g.min;
  const fraction = (event.clientY - canvas.getBoundingClientRect().top - g.top) / (g.bottom - g.top);
  drag = {
    id: event.pointerId, x: event.clientX, y: event.clientY,
    axis, offset, step: g.step, min: g.min, max: g.max, span, fraction,
    pricePerPixel: span / (g.bottom - g.top),
  };
  canvas.classList.toggle('price-axis', axis);
  canvas.setPointerCapture(event.pointerId);
  canvas.classList.add('dragging');
});
canvas.addEventListener('pointermove', event => {
  if (drag?.id === event.pointerId) {
    const dy = event.clientY - drag.y;
    if (drag.axis) {
      const span = Math.max(10 ** -chartData.digits,
        drag.span * Math.exp(Math.max(-2, Math.min(2, dy / 175))));
      const fixed = drag.max - drag.fraction * drag.span;
      const max = fixed + drag.fraction * span;
      manualPriceRange = {min: max - span, max};
    } else {
      const maxOffset = Math.max(0, chartData.rows.length - geometry.count);
      offset = Math.min(maxOffset, Math.max(0, drag.offset + Math.round((event.clientX - drag.x) / drag.step)));
      if (drag.vertical || Math.abs(dy) >= 4) {
        drag.vertical = true;
        const shift = dy * drag.pricePerPixel;
        manualPriceRange = {min: drag.min + shift, max: drag.max + shift};
      }
    }
    render();
    return;
  }
  if (event.pointerType === 'mouse' && !event.buttons) {
    canvas.classList.toggle('price-axis', overPriceAxis(event));
    chartHover = {x: event.clientX, y: event.clientY};
    updateChartTooltip();
  }
  const p = point(event);
  if (p) {
    const time = p.t === null ? '' : dateFormat.format(new Date(p.t * 1000)) + ' · ';
    message('pointer', time + p.p.toFixed(chartData.digits) + ' · Reloj de MT5');
  }
});
function finishDrag(event) {
  if (drag?.id !== event.pointerId) return;
  drag = null;
  canvas.classList.remove('dragging');
  if (event.type === 'pointerup') {
    chartHover = {x: event.clientX, y: event.clientY};
    updateChartTooltip();
  }
}
for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
  canvas.addEventListener(type, finishDrag);
}
canvas.addEventListener('pointerleave', clearChartHover);
canvas.addEventListener('dblclick', event => {
  if (overPriceAxis(event)) resetPriceScale();
});
window.addEventListener('scroll', clearChartHover, {passive: true});
window.addEventListener('keydown', event => {
  if (event.key === 'Escape') clearChartHover();
});
canvas.addEventListener('click', async event => {
  const kind = $('tool').value;
  const p = point(event);
  if (!kind) {
    const id = book22At(event);
    if (id) {
      $('book22Signal').value = book22Selection = id;
      openBook22Tab(true);
      showBook22Status();
      render();
    }
    return;
  }
  if (kind === 'referencia') {
    measureReferenceCandle(p);
    return;
  }
  if (!kind || !p || editing || (p.t === null && kind !== 'Nivel')) return;
  if (p.t === null) p.t = geometry.end;
  const twoPoints = kind === 'POI' || kind === 'Tendencia';
  if (twoPoints && !pending) {
    pending = p;
    message('markStatus', 'Marca el segundo punto sobre el gráfico.');
    render();
    return;
  }
  const label = $('label').value;
  const scope = chartScope;
  const saved = await changeNote(scope, {
    action: 'add', kind, first: pending || p, second: twoPoints ? p : null, label,
  });
  if (saved) {
    pending = null;
    if ($('label').value === label) {
      $('label').value = '';
      $('ictTemplate').disabled = false;
    }
    render();
  }
});
$('label').addEventListener('input', () => {
  $('ictTemplate').disabled = !!$('label').value.trim();
});
$('ictTemplate').addEventListener('click', () => {
  const note = $('label');
  if (note.value.trim()) return;
  note.value = ictFields.join(': \n') + ': ';
  $('ictTemplate').disabled = true;
  note.focus();
  const firstAnswer = ictFields[0].length + 2;
  note.setSelectionRange(firstAnswer, firstAnswer);
});
$('tool').addEventListener('change', () => {
  pending = null;
  canvas.classList.toggle('pan-ready', !$('tool').value);
  message('markStatus', $('tool').value === 'referencia' ? 'Haz clic en una vela cerrada de MT5.' :
    $('tool').value ? 'Haz clic sobre el gráfico.' : 'Elige una herramienta para marcar sobre el gráfico.');
  render();
});
$('referenceForm').addEventListener('submit', captureReference);
$('referenceSelect').addEventListener('change', () => {
  resetReferenceTool();
  message('referenceStatus', '');
  drawReferenceControls();
  drawNotes();
});
$('referenceOpen').addEventListener('click', () => {
  const ref = selectedReference();
  const symbol = ref && referenceInstrument(ref.symbol);
  if (!symbol) return;
  reviewAt = null;
  $('symbol').value = symbol;
  $('tf').value = ref.tf;
  loadChart(true);
});
$('referenceMeasure').addEventListener('click', () => {
  if (!referenceMatches(selectedReference(), chartScope)) return;
  $('tool').value = 'referencia';
  $('tool').dispatchEvent(new Event('change'));
  canvas.scrollIntoView({block: 'center'});
});
$('referenceDelete').addEventListener('click', () => {
  const ref = selectedReference();
  if (ref && window.confirm('¿Borrar esta referencia guardada en este navegador?') &&
      saveReferences(references.filter(item => item.id !== ref.id))) {
    resetReferenceTool();
    refreshReferences();
    message('referenceStatus', 'Referencia borrada.');
  }
});
try {
  const stored = JSON.parse(localStorage.getItem(referenceKey) || '[]');
  if (Array.isArray(stored)) references = stored;
} catch {
  message('referenceStatus', 'No se pudieron leer las referencias guardadas.');
}
refreshReferences();
$('chartForm').addEventListener('submit', event => { event.preventDefault(); loadChart(true); });
$('symbol').addEventListener('change', () => loadChart(true));
$('marketTab').addEventListener('click', () => activateAppTab('market'));
$('analysisTab').addEventListener('click', () => { activateAppTab('analysis'); loadDetailedAnalysis(); });
$('analysisSymbol').addEventListener('change', loadDetailedAnalysis);
$('journalTab').addEventListener('click', () => activateAppTab('journal'));
for (const id of ['marketTab', 'analysisTab', 'journalTab']) $(id).addEventListener('keydown', event => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const ids = ['marketTab', 'analysisTab', 'journalTab'];
  const index = ids.indexOf(id);
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? ids.length - 1
    : (index + (event.key === 'ArrowRight' ? 1 : ids.length - 1)) % ids.length;
  $(ids[next]).focus();
  activateAppTab(ids[next].replace('Tab', ''));
});
$('scanTarget').addEventListener('change', changeScanTarget);
$('scanOpenChart').addEventListener('click', openSelectedScanChart);
$('scanForm').addEventListener('submit', scanHistory);
$('dxyWidget').addEventListener('toggle', loadDxyWidget);
loadScanUniverse();
$('tf').addEventListener('change', () => loadChart(true));
windowSize.addEventListener('change', () => {
  customWindowSize.hidden = windowSize.selectedOptions[0] !== customWindowSize;
  render();
});
$('showDeals').addEventListener('change', render);
$('showBook22').addEventListener('change', render);
$('book22OverviewTab').addEventListener('click', () => openBook22Tab(false));
$('book22DetailTab').addEventListener('click', () => openBook22Tab(true));
for (const id of ['book22OverviewTab', 'book22DetailTab']) $(id).addEventListener('keydown', event => {
  if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
    event.preventDefault();
    openBook22Tab(event.key === 'End' || (event.key !== 'Home' && id === 'book22OverviewTab'), true);
  }
});
$('book22Signal').addEventListener('change', () => {
  const setup = selectedBook22();
  if (!setup) return;
  book22Selection = setup.id;
  const rows = chartData.rows;
  const index = rows.findIndex(row => row[0] === setup.signal_open);
  if (index >= 0 && (setup.signal_open < geometry?.start || setup.evaluated > geometry?.visibleUntil)) {
    offset = Math.max(0, rows.length - 1 - index - 24);
  }
  showBook22Status();
  render();
});
for (const id of ['ictPoi', 'ictFvg', 'ictOb', 'showDailyLiquidity', 'showFridayReference', 'showOpenings']) {
  $(id).addEventListener('change', render);
}
$('liveView').addEventListener('click', () => {
  reviewAt = null;
  $('liveView').hidden = true;
  loadChart(true);
});
function resetPriceScale() {
  manualPriceRange = null;
  render();
}
$('back').addEventListener('click', () => { offset += Math.round((geometry?.rows.length ?? 0) / 2); render(); });
$('forward').addEventListener('click', () => { offset = Math.max(0, offset - Math.round((geometry?.rows.length ?? 0) / 2)); render(); });
$('centerChart').addEventListener('click', () => {
  offset = 0;
  resetPriceScale();
});
$('resetPriceScale').addEventListener('click', resetPriceScale);
$('fitDailyLevels').addEventListener('change', resetPriceScale);
fullscreenButton.addEventListener('click', async () => {
  try {
    if (document.fullscreenElement === chartPanel) await document.exitFullscreen();
    else await chartPanel.requestFullscreen();
  } catch {
    message('chartStatus', 'El navegador no pudo cambiar el modo de pantalla completa.', true);
  }
});
document.addEventListener('fullscreenchange', () => {
  const expanded = document.fullscreenElement === chartPanel;
  fullscreenButton.textContent = expanded ? 'Salir de pantalla completa' : 'Pantalla completa';
  clearChartHover();
});
$('sync').addEventListener('click', refreshJournal);
new ResizeObserver(render).observe(canvas);

async function start() {
  await Promise.all([
    api('/api/notes').then(data => { notes = data; drawNotes(); render(); })
      .catch(error => message('markStatus', error.message, true)),
    api('/api/journal').then(data => showJournal(data.journal))
      .catch(error => message('syncStatus', error.message, true)),
    loadChart(true),
  ]);
  refreshJournal();
  setInterval(refreshJournal, 30000);
  setInterval(loadChart, 10000);
  setInterval(refreshOpenings, 10000);
  refreshUniverseMonitor();
  setInterval(refreshUniverseMonitor, 30000);
}
start();
