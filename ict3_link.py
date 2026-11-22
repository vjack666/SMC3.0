"""Enlace causal y máquina de estados M15 de ICT 3.0 (solo observación).

Este módulo es deliberadamente independiente de ``ict.py`` y de ``test_ict.py``:
consume eventos de ruptura ya producidos por ``daily_break_studies`` y objetos
FVG/OB M15 producidos por ``build_ltf_canonical_feed`` de la revisión fijada
``f453bf2``. No crea zonas propias, no lee M5/M1, no calcula entrada, stop,
objetivo, lotaje ni órdenes.

Tarea 2 -- asociación causal
----------------------------
Para cada ruptura aceptada se examinan todas las zonas M15 canónicas y se
conserva un registro de auditoría por zona en ``poi_candidates`` con:
``zone_id, kind, direction, low, high, confirmed_at, first_touch_at,
association_reason, rejected_reason``. Una zona es candidata válida cuando:

1. su ``origin_tf`` es M15;
2. su dirección es la misma que la de la ruptura;
3. su ``confirmation_time`` es conocida y ``<= cutoff`` (zona confirmada
   después del corte es invisible);
4. su **impulso** pertenece a la secuencia de ruptura.

Ventana causal documentada (no cercanía por precio):

    CAUSAL_IMPULSE_RULE

El impulsor es la vela de desplazamiento del FVG (``meta["middle_bar"]``) o la
vela de ``followthrough`` del OB (``meta["followthrough"]``), con ``confirmation_bar``
como respaldo. Debe caer en el intervalo cerrado de barras M15
``[signal_bar, accept_bar]``, donde ``signal_bar`` es la vela del primer cierre
fuera (``signal_open``) y ``accept_bar`` la del segundo cierre fuera
(``accept_open`` / ``accept_time``). La pertenencia se mide por índice de vela
cerrada, no por distancia entre el precio de la zona y el nivel roto. La
confirmación de la zona puede ocurrir una vela después del impulso siempre que
ya esté cerrada en el corte; la zona se hace visible solo desde entonces.

Un toque anterior a la confirmación de la zona nunca cuenta: ``first_touch_at``
se recompute sobre velas cerradas con índice estrictamente posterior a la
confirmación, sin fiarse de un ``first_touch_time`` heredado del objeto que
pudiera provenir de un corte posterior.

La zona primaria se elige por prioridad causal explícita: la de impulso más
reciente dentro de la secuencia (desempate por confirmación y ``zone_id``).
Nunca por precio. ``accepted_without_poi`` / ``accepted_with_poi`` son campos
descriptivos alongside ``link_state``; el estado principal ``state`` del evento
no se reemplaza.

Tarea 3 -- máquina de estados M15
---------------------------------
Transiciones sobre velas cerradas ``closed <= cutoff``:

* ``RETESTING_POI``: primer contacto (rango de la vela toca ``[low, high]``,
  comparación inclusiva) posterior a la confirmación de la zona primaria.
* ``ACCEPTANCE_LOST``: cierre M15 de vuelta dentro de PDH/PDL tras la
  aceptación y antes de un retest válido.
* ``POI_INVALID``: cierre que atraviesa el límite estructural de la zona en
  contra de la dirección (``close < low`` si dirección +1; ``close > high`` si -1).
  Se evalúa **desde la confirmación de la zona**, aunque no haya habido contacto
  geométrico previo: un gap que salta la zona también la invalida.
* ``EXPANSION_NO_ENTRY``: sin retest al cierre exacto de la mayor ventana
  configurada. Es un estado **terminal** de este evento: un toque en velas
  posteriores al horizonte no puede reabrir el setup ni reescribirlo como
  ``RETESTING_POI``. Las ventanas 4/8/16/32 M15 se publican como resultados
  comparables en ``window_results``; usar la mayor como horizonte de la
  afirmación observable no constituye una regla normativa validada.

Precedencia determinista (C6), evaluada en orden sobre cada vela cerrada mientras
el estado siga siendo ``ACCEPTED``:

1. pérdida del nivel diario roto (``close <= level`` si +1, ``close >= level``
   si -1) antes de cualquier retest → ``ACCEPTANCE_LOST``;
2. tránsito del límite estructural de la POI conservando el nivel roto →
   ``POI_INVALID``;
3. contacto con ``[low, high]`` → ``RETESTING_POI``.

Así, si un mismo cierre pierde el nivel diario **y** atraviesa la zona, gana
``ACCEPTANCE_LOST``; si atraviesa la POI pero conserva el nivel roto, gana
``POI_INVALID``. La precedencia se aplica de forma simétrica para +1 y -1.

``transition_history`` conserva ``from, to, at, reason`` en orden cronológico,
producido en un único recorrido de velas. ``at`` es siempre el cierre de una
vela M15 ya cerrada. No se registran transiciones duplicadas por permanencia
fuera del nivel. Cada ventana de ``window_results`` se deriva únicamente de
transiciones con ``at <= horizon`` de esa ventana (y ``retest_within`` respeta
el mismo límite), de modo que ningún estado de ventana depende de evidencia
posterior a su propio horizonte.
"""

from __future__ import annotations

from copy import deepcopy
import pandas as pd

M15_SECONDS = 900
DEFAULT_OBSERVATION_WINDOWS = (4, 8, 16, 32)
ACCEPTED = "ACCEPTED_BREAK_WAIT_RETEST"
RETESTING = "RETESTING_POI"
ACCEPTANCE_LOST = "ACCEPTANCE_LOST"
POI_INVALID = "POI_INVALID"
EXPANSION = "EXPANSION_NO_ENTRY"

CAUSAL_IMPULSE_RULE = (
    "La vela impulsora de la zona (middle_bar/displacement del FVG o "
    "followthrough del OB) debe caer en la secuencia de ruptura "
    "[signal_open, accept_time] inclusive, medida por índice de vela M15 "
    "cerrada; no se usa cercanía por precio."
)

_REJECT_NOT_M15 = "not_m15_zone"
_REJECT_NO_CONFIRMATION = "confirmation_time_unavailable"
_REJECT_AFTER_CUTOFF = "confirmed_after_cutoff"
_REJECT_OPPOSITE = "opposite_direction"
_REJECT_NO_IMPULSE = "impulse_bar_unavailable"
_REJECT_NO_SEQUENCE = "break_sequence_unavailable"
_REJECT_BEFORE = "impulse_before_break_sequence"
_REJECT_AFTER = "impulse_after_break_sequence"


# --------------------------------------------------------------------------- #
# utilidades temporales                                                        #
# --------------------------------------------------------------------------- #

def _epoch(value):
    """Epoch seconds for ints, floats, pandas/datetimes or ISO strings."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if hasattr(value, "timestamp"):
        try:
            return int(value.timestamp())
        except (TypeError, ValueError, OSError, OverflowError):
            pass
    try:
        return int(pd.Timestamp(value, tz="UTC").timestamp())
    except (TypeError, ValueError, OverflowError):
        return None


def _closed_frame(m15_frame, cutoff=None):
    """Copy of the M15 frame truncated to ``closed <= cutoff``, 0-based index."""
    if m15_frame is None or len(m15_frame) == 0:
        base = m15_frame.iloc[0:0].copy() if m15_frame is not None else pd.DataFrame()
        if "_closed_epoch" not in base.columns:
            base["_closed_epoch"] = pd.Series(dtype="int64")
        return base
    frame = m15_frame.copy().reset_index(drop=True)
    if "closed" in frame.columns:
        frame["_closed_epoch"] = frame["closed"].map(_epoch)
    elif "time" in frame.columns:
        frame["_closed_epoch"] = frame["time"].map(_epoch)
    else:
        raise ValueError("El marco M15 debe tener 'closed' o 'time'.")
    if cutoff is not None:
        frame = frame.loc[frame["_closed_epoch"] <= int(cutoff)].reset_index(drop=True)
    return frame


def _bar_index(frame, *, opened=None, closed=None):
    """Index of the M15 bar with that opening (preferred) or closing epoch."""
    if opened is not None and "opened" in frame.columns:
        hits = frame.index[frame["opened"].map(_epoch) == int(opened)].tolist()
        if hits:
            return int(hits[0])
    if closed is not None and len(frame):
        target = int(closed)
        hits = frame.index[frame["_closed_epoch"] == target].tolist()
        if hits:
            return int(hits[-1])
    return None


def _zone_kind(obj):
    value = getattr(getattr(obj, "type", None), "value", None)
    if value == "FVG":
        return "FVG"
    if value in ("ORDER_BLOCK", "OB"):
        return "OB"
    return str(value or "")


def _impulse_bar(obj, kind, confirmation_bar):
    meta = getattr(obj, "meta", None) or {}
    field = "middle_bar" if kind == "FVG" else "followthrough"
    value = meta.get(field)
    if value is None:
        value = getattr(obj, "confirmation_bar", None)
    if value is None:
        value = confirmation_bar
    return int(value) if value is not None else None


def _touch(frame, zone_low, zone_high, confirmation_bar):
    """First closed bar strictly after confirmation overlapping the zone."""
    if confirmation_bar is None or confirmation_bar >= len(frame) - 1:
        return None, None
    for index in range(confirmation_bar + 1, len(frame)):
        row = frame.iloc[index]
        low = float(row["low"])
        high = float(row["high"])
        if low <= zone_high and high >= zone_low:
            return int(row["_closed_epoch"]), index
    return None, None


def _overlaps(row, low, high):
    return float(row["low"]) <= high and float(row["high"]) >= low


def _reject(candidate, reason):
    candidate["rejected_reason"] = reason
    return candidate


def _new_candidate(obj, kind, direction):
    zone_low = float(getattr(obj, "zone_low", 0.0))
    zone_high = float(getattr(obj, "zone_high", 0.0))
    return {
        "zone_id": str(getattr(obj, "id", "")),
        "kind": kind,
        "direction": int(getattr(obj, "direction", 0)),
        "low": zone_low,
        "high": zone_high,
        "confirmed_at": _epoch(getattr(obj, "confirmation_time", None)),
        "first_touch_at": None,
        "association_reason": None,
        "rejected_reason": None,
    }


# --------------------------------------------------------------------------- #
# Tarea 2 -- asociación causal                                                 #
# --------------------------------------------------------------------------- #

def associate_pois(event, zones, m15_frame, cutoff, *, observation_windows=DEFAULT_OBSERVATION_WINDOWS):
    """Link one accepted break to the causal M15 FVG/OB canonically produced.

    ``zones`` must be the ``["zones"]["M15"]`` list of ``build_ltf_canonical_feed``.
    All evidence is recomputed from bars closed at ``cutoff`` so a prefix replay
    equals the same instant of the full series.
    """
    cutoff = int(cutoff)
    frame = _closed_frame(m15_frame, cutoff)
    direction = int(event["direction"])
    level = float(event["level"])
    signal_open = int(event["signal_open"])
    accept_time = int(event.get("accept_time", event.get("state_time", cutoff)))
    accept_open = event.get("accept_open")
    signal_bar = _bar_index(frame, opened=signal_open, closed=event.get("signal_close"))
    accept_bar = _bar_index(frame, opened=accept_open, closed=accept_time)
    if accept_bar is None and len(frame):
        # An accepted break always has a second closed outside bar; this is a
        # defensive fallback for hand-made events so replay never reads ahead.
        accept_bar = len(frame) - 1

    candidates = []
    impulse_by_id = {}
    for obj in zones or ():
        if str(getattr(obj, "origin_tf", "")).upper() != "M15":
            continue
        kind = _zone_kind(obj)
        candidate = _new_candidate(obj, kind, direction)
        confirmed_at = candidate["confirmed_at"]
        confirmation_bar = getattr(obj, "confirmation_bar", None)
        if confirmation_bar is None:
            confirmation_bar = _bar_index(frame, closed=confirmed_at)
        else:
            confirmation_bar = int(confirmation_bar)

        if confirmed_at is None:
            _reject(candidate, _REJECT_NO_CONFIRMATION)
        elif confirmed_at > cutoff:
            _reject(candidate, _REJECT_AFTER_CUTOFF)
        elif confirmation_bar is None or confirmation_bar >= len(frame):
            _reject(candidate, _REJECT_AFTER_CUTOFF)
        elif int(candidate["direction"]) != direction:
            _reject(candidate, _REJECT_OPPOSITE)
        else:
            impulse = _impulse_bar(obj, kind, confirmation_bar)
            if impulse is None:
                _reject(candidate, _REJECT_NO_IMPULSE)
            elif signal_bar is None:
                _reject(candidate, _REJECT_NO_SEQUENCE)
            elif impulse < signal_bar:
                _reject(candidate, _REJECT_BEFORE)
            elif impulse > accept_bar:
                _reject(candidate, _REJECT_AFTER)
            else:
                touch_at, _ = _touch(frame, candidate["low"], candidate["high"], confirmation_bar)
                candidate["first_touch_at"] = touch_at
                candidate["association_reason"] = (
                    f"same_direction; impulse_bar={impulse} in_break_sequence=[{signal_bar},{accept_bar}]; "
                    f"confirmed_at={confirmed_at}<=cutoff={cutoff}"
                )
                impulse_by_id[candidate["zone_id"]] = (impulse, confirmed_at or 0)
        candidates.append(candidate)

    valid = [row for row in candidates if row["association_reason"]]
    ordered = sorted(valid, key=lambda row: (
        -impulse_by_id[row["zone_id"]][0], -impulse_by_id[row["zone_id"]][1], row["zone_id"]))
    primary = ordered[0]["zone_id"] if ordered else None
    with_poi = primary is not None

    return {
        "event_id": event.get("event_id"),
        # estado principal intacto: el enlace no lo promueve ni lo sustituye.
        "state": event.get("state", ACCEPTED),
        "link_state": "accepted_with_poi" if with_poi else "accepted_without_poi",
        "accepted_with_poi": with_poi,
        "accepted_without_poi": not with_poi,
        "mode": "OBSERVE_ONLY_NO_ORDER",
        "direction": direction,
        "level_name": event.get("level_name"),
        "level": level,
        "signal_open": signal_open,
        "accept_open": int(accept_open) if accept_open is not None else None,
        "accept_time": accept_time,
        "causal_window": {
            "from_open": signal_open,
            "to_closed": accept_time,
            "from_bar": signal_bar,
            "to_bar": accept_bar,
            "rule": CAUSAL_IMPULSE_RULE,
        },
        "poi_candidates": candidates,
        "primary_poi": primary,
        "selection_reason": "latest_causal_impulse_in_break_sequence" if primary else None,
        "observation_windows": [int(w) for w in observation_windows],
        "transition_history": [],
        "current_state": event.get("state", ACCEPTED),
        "window_results": {},
        "retest_at": None,
    }


# --------------------------------------------------------------------------- #
# Tarea 3 -- máquina de estados M15                                             #
# --------------------------------------------------------------------------- #

def advance_state(link, m15_frame, cutoff, *, observation_windows=None):
    """Advance the observation state machine using only bars closed at cutoff.

    Transitions are produced in chronological order in a single pass over the
    closed bars. At the exact close of the widest observation window, an
    untouched setup becomes ``EXPANSION_NO_ENTRY``: a terminal state, so a
    later touch cannot rewrite it. Each window result is derived only from
    transitions at or before that window's own horizon.
    """
    cutoff = int(cutoff)
    result = deepcopy(link)
    windows = tuple(int(w) for w in (observation_windows or result.get("observation_windows")
                                     or DEFAULT_OBSERVATION_WINDOWS))
    result["observation_windows"] = list(windows)
    result["transition_history"] = []
    result["window_results"] = {}
    result["current_state"] = result["state"]
    result["retest_at"] = None

    frame = _closed_frame(m15_frame, cutoff)
    state = result["state"]
    accept_bar = _bar_index(frame, opened=result.get("accept_open"), closed=result.get("accept_time"))
    if accept_bar is None and len(frame):
        accept_bar = len(frame) - 1
    level = float(result["level"])
    primary = next((row for row in result["poi_candidates"]
                    if row["zone_id"] == result.get("primary_poi")), None)
    history = []

    def transition(to, at, reason):
        nonlocal state
        history.append({"from": state, "to": to, "at": int(at), "reason": reason})
        state = to

    # Exact close bar of the widest window (all bars after the acceptance bar).
    max_width = max(windows) if windows else None
    max_horizon_index = (accept_bar + max_width
                         if accept_bar is not None and max_width is not None else None)
    max_horizon_complete = max_horizon_index is not None and max_horizon_index < len(frame)
    expansion_reason = "no_retest_within_max_observation_window_comparable_results"

    if primary:
        zlo, zhi = float(primary["low"]), float(primary["high"])
        zdir = int(primary["direction"])
        confirmation_bar = _bar_index(frame, closed=primary["confirmed_at"])
        start = accept_bar + 1 if accept_bar is not None else 0
        if confirmation_bar is not None:
            start = max(start, confirmation_bar + 1)

        # A zone confirmed beyond the widest horizon can never be retested in
        # that window; still close the case at the horizon (no look-ahead).
        if (max_horizon_index is not None and max_horizon_complete
                and max_horizon_index < start and state == ACCEPTED):
            transition(EXPANSION, int(frame.iloc[max_horizon_index]["_closed_epoch"]), expansion_reason)

        # Single chronological pass. Terminal states end the pass immediately,
        # so nothing after the horizon can reopen the setup (C4).
        index = start
        while index < len(frame) and state not in (ACCEPTANCE_LOST, POI_INVALID, EXPANSION):
            row = frame.iloc[index]
            closed = int(row["_closed_epoch"])
            close = float(row["close"])
            back_inside = close <= level if zdir == 1 else close >= level
            through = close < zlo if zdir == 1 else close > zhi

            if state == ACCEPTED:
                # Deterministic precedence (C6): losing the broken daily level
                # before any retest outranks the zone boundary.
                if back_inside:
                    transition(ACCEPTANCE_LOST, closed, "m15_close_back_inside_level_before_retest")
                    break
                # Structural invalidity holds from confirmation even with no
                # prior geometric contact: a gap that skips the zone counts.
                if through:
                    transition(POI_INVALID, closed, "close_through_structural_boundary_against_direction")
                    break
                if _overlaps(row, zlo, zhi):
                    result["retest_at"] = closed
                    transition(RETESTING, closed, "first_touch_after_confirmation")
                    index += 1
                    continue
            elif state == RETESTING:
                if through:
                    transition(POI_INVALID, closed, "close_through_structural_boundary_against_direction")
                    break

            # Terminal at the exact close of the widest window: no retest by
            # then means expansion, and later contacts cannot change it (C4).
            if state == ACCEPTED and max_horizon_complete and index == max_horizon_index:
                transition(EXPANSION, closed, expansion_reason)
                break
            index += 1

    # Comparable observation windows, all measured in closed M15 bars after
    # the acceptance bar. No window is declared normative by this module.
    # Every window is derived only from transitions at or before its horizon:
    # an invalidation after a window's horizon cannot leak back into it (C5).
    for width in windows:
        scope = frame.iloc[accept_bar + 1: accept_bar + 1 + width] if accept_bar is not None else frame.iloc[0:0]
        complete = len(scope) == width
        horizon = int(scope.iloc[-1]["_closed_epoch"]) if complete else None
        effective_horizon = (horizon if horizon is not None
                             else (int(frame.iloc[-1]["_closed_epoch"]) if len(frame) else cutoff))
        touch_within = any(item["to"] == RETESTING and item["at"] <= effective_horizon
                           for item in history)
        within = [item for item in history if item["at"] <= effective_horizon]
        if not primary:
            window_state = result["state"]
        elif within:
            window_state = within[-1]["to"]
        elif complete and not touch_within:
            # No transition yet at this horizon but the window is complete and
            # untouched: the comparable "no entry here" state, with no future
            # evidence involved.
            window_state = EXPANSION
        else:
            window_state = result["state"]
        result["window_results"][str(width)] = {
            "window_bars": width,
            "retest_within": touch_within,
            "state": window_state,
            "bars_observed": len(scope),
            "window_complete": complete,
            "horizon": horizon,
        }

    result["transition_history"] = history
    result["current_state"] = state
    return result


def build_ict3_link(event, zones, m15_frame, cutoff, *, observation_windows=DEFAULT_OBSERVATION_WINDOWS):
    """Tarea 2 + Tarea 3 for a single accepted break."""
    link = associate_pois(event, zones, m15_frame, cutoff,
                          observation_windows=observation_windows)
    return advance_state(link, m15_frame, cutoff, observation_windows=observation_windows)


def link_breaks(events, zones, m15_frame, cutoff, *, observation_windows=DEFAULT_OBSERVATION_WINDOWS):
    """Apply the link and state machine to a sequence of accepted breaks."""
    return [build_ict3_link(event, zones, m15_frame, cutoff,
                            observation_windows=observation_windows)
            for event in events]


__all__ = [
    "M15_SECONDS", "DEFAULT_OBSERVATION_WINDOWS", "CAUSAL_IMPULSE_RULE",
    "ACCEPTED", "RETESTING", "ACCEPTANCE_LOST", "POI_INVALID", "EXPANSION",
    "associate_pois", "advance_state", "build_ict3_link", "link_breaks",
]
