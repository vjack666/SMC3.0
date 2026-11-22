"""Fase 7 -- validacion fuera de muestra (OOS) de ICT 3.0, solo observacion.

Modulo puro y determinista.  No importa MT5, no abre conexiones, no lee ni
escribe ``data/`` y no produce ordenes, fills, lotaje, P&L ni curva de capital.
Mide unicamente estados observados y su cobertura, para que otra persona pueda
reproducir los conteos con las mismas fuentes declaradas.

Todo dato producido aqui es SINTETICO y esta declarado como tal.  La cobertura
real queda marcada como PENDIENTE hasta que el agente de datos entregue una
fuente verificable; este modulo nunca inventa velas reales ni credenciales.

API principal
-------------
``build_inventory(dataset)``            inventario por activo/marco.
``pending_inventory(symbols, frames)``  inventario de cobertura real pendiente.
``FROZEN_PARAMETERS``                   parametros congelados de la particion.
``separate_calibration_evaluation(p, obs)``  fecha de separacion, sin solape.
``group_observed_states(obs)``          agrupacion por las seis dimensiones.
``verify_prefix_invariance(...)``       ``prefix_to_t == full_series_at_t``.
``refuse_execution_metrics(...)``       rechazo explicito de metricas prohibidas.
``build_report(dataset=None)``          informe completo, reproducible.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import random

# --------------------------------------------------------------------------- #
# Vocabulario y constantes congeladas                                          #
# --------------------------------------------------------------------------- #
MODE = "OBSERVE_ONLY_NO_ORDER"

# Coincide con ict.SECONDS; se replica para no importar ict.py (que importa MT5).
SECONDS = {"D1": 86400, "H4": 14400, "H1": 3600,
           "M15": 900, "M5": 300, "M1": 60}

# Claves que nunca pueden aparecer en un bloque observacional (Fase 5/7).
FORBIDDEN_KEYS = frozenset({
    "entry", "order", "fill", "fills", "lot", "lots", "volume", "pnl", "pnl_curve",
    "profit", "position", "cash_value", "balance", "equity", "margin",
    "ticket", "deal", "trade", "slippage", "commission", "equity_curve",
})

SYNTHETIC_SOURCE = "SYNTHETIC_DECLARED"
REAL_PENDING = "REAL_COVERAGE_PENDING"

LEVELS = ("PDH", "PDL")
POI_TYPES = ("FVG", "OB")
STATES = (
    "BREAK_CANDIDATE", "FAILED_BREAK", "ACCEPTED_BREAK_WAIT_RETEST",
    "RETESTING_POI", "EXPANSION_NO_ENTRY", "ACCEPTANCE_LOST", "POI_INVALID",
)
SESSIONS = ("ASIA", "LONDON", "NEW_YORK", "OTHER")
DEFAULT_WINDOWS = (4, 8, 16, 32)  # velas M15, igual que ict3_link.DEFAULT_OBSERVATION_WINDOWS
DIMENSIONS = ("symbol", "level", "session", "poi_type", "window", "state")

ALIASES = {
    "EURUSD": "EUR/USD", "GBPJPY": "GBP/JPY", "USDJPY": "USD/JPY",
    "EURJPY": "EUR/JPY", "AUDUSD": "AUD/USD", "USDCAD": "USD/CAD",
    "US30": "US30/DJI", "US100": "US100/NDX", "US500": "US500/SPX",
}


@dataclass(frozen=True)
class FrozenParameters:
    """Parametros congelados de la particion calibracion/evaluacion."""

    separation_date: str = "2026-11-15"
    windows: tuple = DEFAULT_WINDOWS
    force_body_ratio: float = 0.70
    force_body_multiple: float = 1.5
    force_close_extension: float = 0.50
    source_policy: str = SYNTHETIC_SOURCE
    mode: str = MODE

    def as_dict(self):
        return asdict(self)


FROZEN_PARAMETERS = FrozenParameters()


class ExecutionMetricsForbidden(RuntimeError):
    """Se lanza cuando se pide calcular una metrica de ejecucion prohibida."""


# --------------------------------------------------------------------------- #
# Utilidades de fecha / sesion / alias                                         #
# --------------------------------------------------------------------------- #
def _iso(timestamp):
    """Epoch -> 'YYYY-MM-DD HH:MM UTC' legible y auditable."""
    return datetime.fromtimestamp(int(timestamp), timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC")


def _date_str(timestamp):
    """Epoch -> 'YYYY-MM-DD' para comparar contra la fecha de separacion."""
    return datetime.fromtimestamp(int(timestamp), timezone.utc).strftime("%Y-%m-%d")


def alias_for(symbol):
    """Alias legible del activo; el simbolo original se conserva siempre."""
    return ALIASES.get(symbol, symbol)


def session_for_time(timestamp):
    """Sesion declarada por hora UTC (mapa fijo, sin DST).

    ASIA 00-07, LONDON 07-12, NEW_YORK 12-21, OTHER el resto.  Es una
    convencion declarada para agrupar, no una afirmacion de liquidez.
    """
    hour = datetime.fromtimestamp(int(timestamp), timezone.utc).hour
    if 0 <= hour < 7:
        return "ASIA"
    if 7 <= hour < 12:
        return "LONDON"
    if 12 <= hour < 21:
        return "NEW_YORK"
    return "OTHER"


# --------------------------------------------------------------------------- #
# Rechazo explicito de metricas de ejecucion                                    #
# --------------------------------------------------------------------------- #
def refuse_execution_metrics(metric, *args, **kwargs):
    """Rechaza cualquier intento de calcular fills/lotaje/P&L/curva.

    La Fase 7 mide estados y cobertura, no rentabilidad.  Esta funcion existe
    para que el rechazo sea explicito y auditable, no un silencio.
    """
    raise ExecutionMetricsForbidden(
        "Fase 7 (OBSERVE_ONLY_NO_ORDER): se rechaza '%s'. No se calculan fills, "
        "lotaje, P&L, balance, equity ni curva de capital; solo estados "
        "observados y su frecuencia." % metric)


def assert_no_execution_metrics(node):
    """Verifica recursivamente que no aparezca ninguna clave prohibida.

    Devuelve ``True`` si el objeto es observacional; lanza
    ``ExecutionMetricsForbidden`` si detecta una clave de ejecucion.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise ExecutionMetricsForbidden(
                    "Clave de ejecucion prohibida en el informe OOS: %r" % key)
            assert_no_execution_metrics(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            assert_no_execution_metrics(value)
    return True


# --------------------------------------------------------------------------- #
# Datos sinteticos declarados                                                  #
# --------------------------------------------------------------------------- #
def synthetic_candles(symbol, frame, count, *, start_epoch, seed=0, gap_every=0):
    """Velas SINTETICAS deterministas ``(opened, o, h, l, c)``.

    ``gap_every=k`` salta una posicion cada k velas para poder medir huecos en
    el inventario.  Solo se usa para demostrar el protocolo: no representan
    ningun feed real.
    """
    if frame not in SECONDS:
        raise ValueError("marco desconocido: %r" % frame)
    rnd = random.Random("oos|candles|%s|%s|%s" % (symbol, frame, seed))
    step = SECONDS[frame]
    opened = int(start_epoch)
    price = 1.0000 + rnd.uniform(0, 0.5)
    candles = []
    for index in range(count):
        if gap_every and index and index % gap_every == 0:
            opened += step  # hueco declarado: falta la vela de ese intervalo
        close = max(1e-5, price + rnd.uniform(-0.004, 0.004))
        high = max(price, close) + rnd.uniform(0, 0.002)
        low = min(price, close) - rnd.uniform(0, 0.002)
        candles.append((opened,
                        round(price, 5), round(high, 5),
                        round(low, 5), round(close, 5)))
        price = close
        opened += step
    return candles


def synthetic_observations(parameters, symbols=("EURUSD", "GBPJPY", "US30"),
                           *, seed=7, start_epoch=None, days=20):
    """Observaciones SINTETICAS con las seis dimensiones de agrupacion."""
    params = parameters or FROZEN_PARAMETERS
    start = int(start_epoch) if start_epoch is not None else int(
        datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp())
    observations = []
    for symbol in symbols:
        rnd = random.Random("oos|observations|%s|%s" % (symbol, seed))
        for day in range(days):
            observed = start + day * SECONDS["D1"] + rnd.randrange(0, 21) * SECONDS["M15"]
            poi = rnd.choice(POI_TYPES + (None,))
            observations.append({
                "symbol": symbol,
                "level": rnd.choice(LEVELS),
                "session": session_for_time(observed),
                "poi_type": poi,
                "window": int(rnd.choice(params.windows)),
                "state": rnd.choice(STATES),
                "observed_at": int(observed),
                "observed_date": _date_str(observed),
                "has_poi": poi is not None,
                "window_complete": rnd.random() < 0.85,
                "declared_synthetic": True,
            })
    return observations


# --------------------------------------------------------------------------- #
# 1. Inventario por activo / marco                                             #
# --------------------------------------------------------------------------- #
def _gap_count(candles, frame):
    step = SECONDS[frame]
    closes = [row[0] + step for row in candles]
    return sum(1 for first, second in zip(closes, closes[1:]) if second - first > step)


def inventory_entry(symbol, frame, candles, *, alias=None, source=SYNTHETIC_SOURCE,
                    declared_synthetic=True):
    """Fila de inventario: alias, fuente, primer/ultimo cierre, velas y huecos."""
    if frame not in SECONDS:
        raise ValueError("marco desconocido: %r" % frame)
    step = SECONDS[frame]
    first_close = candles[0][0] + step if candles else None
    last_close = candles[-1][0] + step if candles else None
    return {
        "symbol": symbol,
        "alias": alias or alias_for(symbol),
        "frame": frame,
        "source": source,
        "declared_synthetic": declared_synthetic,
        "first_close": _iso(first_close) if first_close is not None else None,
        "last_close": _iso(last_close) if last_close is not None else None,
        "first_close_epoch": first_close,
        "last_close_epoch": last_close,
        "candles": len(candles),
        "gaps": _gap_count(candles, frame),
        "real_coverage": REAL_PENDING,
    }


def build_inventory(dataset, *, source=SYNTHETIC_SOURCE, aliases=None):
    """Inventario de un ``dataset = {symbol: {frame: candles}}`` declarado.

    El dataset se recibe, nunca se lee de disco ni de MT5.  Si es vacio se
    devuelve cobertura real pendiente.
    """
    aliases = aliases or {}
    inventory = []
    for symbol, frames in (dataset or {}).items():
        for frame, candles in frames.items():
            inventory.append(inventory_entry(
                symbol, frame, candles,
                alias=aliases.get(symbol), source=source,
                declared_synthetic=source == SYNTHETIC_SOURCE))
    return sorted(inventory, key=lambda row: (row["symbol"], row["frame"]))


def pending_inventory(symbols=("EURUSD", "GBPJPY", "US30"),
                      frames=("D1", "M15", "M5", "M1")):
    """Inventario de cobertura real PENDIENTE: sin fuente, sin velas inventadas."""
    return [{
        "symbol": symbol, "alias": alias_for(symbol), "frame": frame,
        "source": REAL_PENDING, "declared_synthetic": False,
        "first_close": None, "last_close": None,
        "first_close_epoch": None, "last_close_epoch": None,
        "candles": 0, "gaps": 0, "real_coverage": REAL_PENDING,
    } for symbol in symbols for frame in frames]


def common_coverage(inventory, *, frames=("M15",)):
    """Interseccion de activos con velas en todos los marcos pedidos.

    Toda exclusion queda registrada con su motivo para que no se silencie.
    """
    by_symbol = defaultdict(dict)
    for row in inventory:
        by_symbol[row["symbol"]][row["frame"]] = row
    included, excluded = [], []
    for symbol, frames_map in sorted(by_symbol.items()):
        missing = [frame for frame in frames
                   if frames_map.get(frame, {}).get("candles", 0) == 0]
        if missing:
            excluded.append({"symbol": symbol, "reason": "MISSING_FRAMES",
                             "frames": missing})
        else:
            included.append(symbol)
    return {"frames": tuple(frames), "included": included, "excluded": excluded}


# --------------------------------------------------------------------------- #
# 2. Separacion calibracion / evaluacion con parametros congelados             #
# --------------------------------------------------------------------------- #
def separate_calibration_evaluation(parameters, observations):
    """Parte las observaciones por fecha sin solape ni perdida.

    calibracion: ``observed_date < separation_date``;
    evaluacion:  ``observed_date >= separation_date`` (fuera de muestra).
    """
    params = parameters or FROZEN_PARAMETERS
    separation = params.separation_date
    calibration, evaluation = [], []
    for observation in observations:
        day = observation.get("observed_date") or _date_str(observation["observed_at"])
        (calibration if day < separation else evaluation).append(observation)
    return {
        "separation_date": separation,
        "frozen_parameters": params.as_dict(),
        "calibration": calibration,
        "evaluation": evaluation,
        "counts": {"calibration": len(calibration),
                   "evaluation": len(evaluation),
                   "total": len(observations)},
    }


def calibration_evaluation_integrity(partition):
    """Verifica que la particion sea disjunta y completa (denominadores)."""
    def identity(obs):
        return (obs.get("symbol"), obs.get("observed_at"),
                obs.get("level"), obs.get("state"), obs.get("window"))

    calibration = partition["calibration"]
    evaluation = partition["evaluation"]
    cal = {identity(obs) for obs in calibration}
    eva = {identity(obs) for obs in evaluation}
    return {
        "disjoint": not (cal & eva),
        "complete": len(cal) + len(eva) == len(cal | eva),
        "counts": partition["counts"],
        "separated": bool(calibration) and bool(evaluation) and not (cal & eva),
    }


# --------------------------------------------------------------------------- #
# 3. Agrupacion de estados observados                                          #
# --------------------------------------------------------------------------- #
def group_observed_states(observations):
    """Agrupa por symbol, PDH/PDL, sesion, tipo de POI, ventana y estado."""
    counts = Counter(tuple(obs.get(dim) for dim in DIMENSIONS)
                     for obs in observations)
    rows = [dict(zip(DIMENSIONS, key), count=value)
            for key, value in sorted(counts.items(),
                                     key=lambda item: tuple(str(x) for x in item[0]))]
    by_symbol = Counter(obs.get("symbol") for obs in observations)
    by_symbol_level = Counter((obs.get("symbol"), obs.get("level"))
                              for obs in observations)
    total = len(observations)
    with_poi = sum(1 for obs in observations if obs.get("has_poi"))
    complete = sum(1 for obs in observations if obs.get("window_complete"))
    both = sum(1 for obs in observations
               if obs.get("has_poi") and obs.get("window_complete"))
    return {
        "dimensions": DIMENSIONS,
        "rows": rows,
        "total": total,
        "denominators": {
            "total": total,
            "by_symbol": dict(sorted(by_symbol.items())),
            "by_symbol_level": {
                "%s|%s" % key: value
                for key, value in sorted(by_symbol_level.items(),
                                         key=lambda item: tuple(str(x) for x in item[0]))
            },
        },
        "effective_coverage": {
            "with_poi": with_poi,
            "complete_window": complete,
            "with_poi_and_complete_window": both,
            "total": total,
            "ratio": round(both / total, 4) if total else 0.0,
        },
    }


# --------------------------------------------------------------------------- #
# 4. Invariancia prefijo == serie completa en cada corte                       #
# --------------------------------------------------------------------------- #
def prefix_of(candles, frame, cutoff):
    """Velas cerradas a mas tardar en ``cutoff`` (sin fuga al futuro)."""
    step = SECONDS[frame]
    return [row for row in candles if row[0] + step <= int(cutoff)]


def causal_break_states(candles, frame, cutoff, level):
    """Estados M15 derivados solo de velas cerradas ``<= cutoff``.

    Es un reductor casual de proposito general: ignora cualquier vela que cierre
    despues del corte, de modo que evaluar la serie completa o solo su prefijo
    en ``t`` debe dar exactamente el mismo resultado.
    """
    closed = prefix_of(candles, frame, cutoff)
    step = SECONDS[frame]
    series = []
    candidate_dir = 0
    previous_side = 0
    for row in closed:
        side = 1 if row[4] > level else -1 if row[4] < level else 0
        if side and side != previous_side and candidate_dir == 0:
            candidate_dir = side
            state = "BREAK_CANDIDATE"
        elif candidate_dir and side == 0:
            state = "FAILED_BREAK"
            candidate_dir = 0
        elif candidate_dir and previous_side == candidate_dir:
            state = "ACCEPTED_BREAK_WAIT_RETEST"
            candidate_dir = 0
        else:
            state = "INSIDE" if side == 0 else "OUTSIDE"
        series.append((row[0] + step, state))
        previous_side = side
    return tuple(series)


def verify_prefix_invariance(candles, frame, cutoffs, *, reducer=None, level=1.0):
    """Comprueba ``prefix_to_t == full_series_at_t`` en cada corte.

    ``reducer(candles, frame, cutoff, level)`` debe ser casual; por defecto se
    usa ``causal_break_states``.  Devuelve un informe con los cortes revisados y
    las divergencias (vacia si la invariancia se cumple).
    """
    reducer = reducer or causal_break_states
    checks, mismatches = [], []
    for cutoff in cutoffs:
        full = reducer(candles, frame, cutoff, level)
        prefix = reducer(prefix_of(candles, frame, cutoff), frame, cutoff, level)
        equal = full == prefix
        checks.append({"cutoff": int(cutoff), "cutoff_utc": _iso(cutoff),
                       "states": len(full), "equal": equal})
        if not equal:
            mismatches.append({"cutoff": int(cutoff),
                               "full": full, "prefix": prefix})
    return {
        "frame": frame,
        "level": level,
        "invariant": not mismatches,
        "cutoffs_checked": len(checks),
        "checks": checks,
        "mismatches": mismatches,
    }


# --------------------------------------------------------------------------- #
# 5. Informe reproducible                                                      #
# --------------------------------------------------------------------------- #
def build_report(dataset=None, parameters=None, *,
                 symbols=("EURUSD", "GBPJPY", "US30"), seed=7):
    """Informe OOS: inventario, particion, agrupacion, invariancia y rechazo.

    Sin ``dataset`` no se inventa cobertura real: el inventario queda como
    PENDIENTE y la invariancia se demuestra con velas sinteticas declaradas.
    """
    params = parameters or FROZEN_PARAMETERS
    sample_frame = "M15"
    sample_candles = synthetic_candles(
        symbols[0], sample_frame, 64,
        start_epoch=int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp()),
        seed=seed, gap_every=17)
    if dataset:
        inventory = build_inventory(dataset)
        first_symbol = next(iter(dataset))
        first_frame = next(iter(dataset[first_symbol]))
        sample_frame = first_frame
        sample_candles = dataset[first_symbol][first_frame]
        source = SYNTHETIC_SOURCE
    else:
        inventory = pending_inventory(symbols)
        source = REAL_PENDING

    observations = synthetic_observations(params, symbols=symbols, seed=seed)
    partition = separate_calibration_evaluation(params, observations)
    grouped = group_observed_states(observations)
    step = SECONDS[sample_frame]
    cutoffs = [row[0] + step
               for index, row in enumerate(sample_candles) if index % 8 == 0]
    invariance = verify_prefix_invariance(
        sample_candles, sample_frame, cutoffs, level=1.002)

    report = {
        "protocol": "FASE_07_PROTOCOLO_OOS",
        "mode": MODE,
        "source": source,
        "declared_synthetic": True,
        "real_coverage": REAL_PENDING,
        "inventory": inventory,
        "coverage_common": common_coverage(inventory),
        "calibration_evaluation": partition,
        "integrity": calibration_evaluation_integrity(partition),
        "grouped_states": grouped,
        "prefix_invariance": invariance,
        "execution_metrics_check": "REJECTED: fills/lotaje/P&L/curva no calculados",
    }
    assert_no_execution_metrics(report)
    return report


def render_report(report):
    """Markdown compacto y auditable a partir de ``build_report``."""
    counts = report["calibration_evaluation"]["counts"]
    inv = report["prefix_invariance"]
    lines = [
        "# ICT 3.0 — Protocolo OOS (Fase 7)",
        "",
        "> Solo estados observados y cobertura. No es backtest: no hay fills,",
        "> lotaje, P&L ni curva de capital.",
        "",
        "- Fuente: `%s` (sintética declarada); cobertura real: `%s`." % (
            report["source"], report["real_coverage"]),
        "- Modo: `%s`." % report["mode"],
        "- Separación: `%s`." % report["calibration_evaluation"]["separation_date"],
        "- Calibración / evaluación / total: %d / %d / %d." % (
            counts["calibration"], counts["evaluation"], counts["total"]),
        "- Invariancia prefijo==completa: %s en %d cortes." % (
            "OK" if inv["invariant"] else "FALLA", inv["cutoffs_checked"]),
        "",
        "## Inventario",
        "",
        "| Símbolo | Alias | Marco | Fuente | Primer cierre | Último cierre | Velas | Huecos |",
        "|---|---|---|---|---|---|---:|---:|",
    ]
    for row in report["inventory"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %d | %d |" % (
            row["symbol"], row["alias"], row["frame"], row["source"],
            row["first_close"] or "—", row["last_close"] or "—",
            row["candles"], row["gaps"]))
    lines += ["", "## Estados agrupados (symbol, nivel, sesión, POI, ventana, estado)",
              "", "| " + " | ".join(DIMENSIONS) + " | count |",
              "|" + "---|" * (len(DIMENSIONS) + 1)]
    for row in report["grouped_states"]["rows"]:
        lines.append("| " + " | ".join(str(row[dim]) for dim in DIMENSIONS)
                     + " | %d |" % row["count"])
    return "\n".join(lines)


__all__ = [
    "MODE", "SECONDS", "FORBIDDEN_KEYS", "SYNTHETIC_SOURCE", "REAL_PENDING",
    "LEVELS", "POI_TYPES", "STATES", "SESSIONS", "DEFAULT_WINDOWS", "DIMENSIONS",
    "FrozenParameters", "FROZEN_PARAMETERS", "ExecutionMetricsForbidden",
    "refuse_execution_metrics", "assert_no_execution_metrics",
    "synthetic_candles", "synthetic_observations", "alias_for", "session_for_time",
    "inventory_entry", "build_inventory", "pending_inventory", "common_coverage",
    "separate_calibration_evaluation", "calibration_evaluation_integrity",
    "group_observed_states", "prefix_of", "causal_break_states",
    "verify_prefix_invariance", "build_report", "render_report",
]
