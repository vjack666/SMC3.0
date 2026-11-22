"""Confirmación observacional M5/M1 para eventos ICT 3.0 en ``RETESTING_POI``.

Módulo puro: no importa MT5, pandas, ``ict.py`` ni ningún cliente de órdenes.
Solo lee las velas que se le entregan y muta el dict de resultado que recibe.
No crea ``entry``, ``order``, ``fill``, ``lots``, riesgo monetario ni usa ATR
como sustituto de estructura. Todo evento conserva ``entry_authorized=False``
y ``mode=OBSERVE_ONLY_NO_ORDER``.

API
---
``attach_confirmations(result, lower_source, cutoff, *, digits=2, loader_error=None)``

* ``result``: dict devuelto por ``analyze_cached``; contiene ``result['ict3']['events']``.
* ``lower_source``: ``(digits, tick, bars, spreads)`` de ``ict.read_bars`` con
  claves ``'M5'`` y ``'M1'`` (o ``None``). Solo se lee cuando existe un evento
  en ``RETESTING_POI`` (carga causal bajo demanda).
* ``cutoff``: epoch de corte; solo son visibles velas con cierre ``<= cutoff``.
* ``loader_error``: motivo explícito de fallo de lectura; bloquea cualquier
  confirmación y jamás inventa datos.

Reglas explícitas (documentadas para auditoría)
----------------------------------------------
C1. Vela cerrada: una fila ``(time, open, high, low, close)`` es observable en
    ``t`` solo si ``time + SECONDS[tf] <= cutoff``. No se exige sucesora: el
    cierre nominal se deriva de la propia vela, por lo que un prefijo que termina
    en ``t`` y la serie completa evaluada en ``t`` ven exactamente las mismas
    velas (invariancia ``prefix_to_t == full_series_at_t``). Se ignoran filas
    vacías/de relleno (``high < low`` o OHLC todo cero).

C2. Swings con ventana de 2 velas cerradas: en el índice ``i`` de una serie ya
    truncada a ``<= cutoff`` hay un **swing high** si
    ``H[i] >= max(H[i-2], H[i-1])`` y ``H[i] > max(H[i+1], H[i+2])``; un
    **swing low** si ``L[i] <= min(L[i-2], L[i-1])`` y
    ``L[i] < min(L[i+1], L[i+2])``. Regla simétrica por cambio de signo.
    El pivote solo es **confirmado** cuando ``i+2`` ya cerró; su marca de
    disponibilidad es ``closed[i+2]``. Un empate en el lado futuro impide el
    pivote (evita niveles ambiguos). Ningún pivote se computa con velas futuras.

C3. Clasificación BOS/CHOCH/MSS determinista y simétrica. Para una ruptura
    alcista (+1) se usa el último swing high confirmado antes de la vela que
    rompe; para bajista (-1), el último swing low confirmado. La ruptura debe
    ser por **cierre** de una vela M5 cerrada (no por mecha). Si el pivote
    anterior del mismo tipo es más bajo (+1) / más alto (-1) → tendencia
    previa a favor → ``BOS`` (continuación). Si es más alto (+1) / más bajo
    (-1) → tendencia previa en contra → ``CHOCH`` (cambio de carácter). Si no
    hay pivote anterior o hay empate → ``MSS``. Espejo exacto para -1.

C4. Defensa: tras ``retest_at``, una vela M5 cerrada cuyo rango toca la POI
    primaria (o el nivel roto si no hay POI) y que cierra de vuelta al lado
    favorable del nivel roto, sin cerrar más allá del límite estructural de la
    POI. Es evidencia descriptiva, no una entrada.

C5. Stop informativo, por orden de autoridad (el primero disponible gana):
    1. ``ORIGIN_SWING_INTACT``: swing de origen del impulso (último pivote
       previo al retest en contra de la dirección) sin cierre que lo atraviese
       después del retest;
    2. ``M5_REACTION_EXTREME``: extremo M5 confirmado (pivote) entre el retest
       y la confirmación M5;
    3. ``M1_CONFIRMED_EXTREME``: extremo M1 confirmado, igual definición;
    4. ``NO_STRUCTURAL_STOP``: motivo pendiente, nunca una invalidación.
    No hay lotaje, riesgo monetario ni ATR.

C6. Objetivo: solo liquidez **conocida al corte** — nivel roto y pivotes M5/M1
    confirmados, todos con marca de disponibilidad ``<= cutoff``. No se
    fabrican niveles. ``target_policy_status`` es observacional: con una unidad
    informativa ``R = |precio_de_referencia_estructural - stop|`` (referencia =
    cierre de defensa, o cierre M5 de estructura si no hay defensa; NO es una
    entrada), se exige liquidez conocida a ``>=3R`` para TP1 y ``>=5R`` para
    TP2. Una liquidez a ``>=5R`` satisface ambas condiciones; no se inventa un
    segundo nivel. Sin stop no hay ``R`` y el estado queda pendiente.

C7. ``OBSERVABLE_SETUP`` solo si hay retest + defensa + estructura M5 + stop
    estructural + política de objetivo satisfecha. M1 es corroboración
    opcional: nunca sustituye a M5. ``entry_authorized`` sigue siendo ``False``
    y ``mode`` sigue siendo ``OBSERVE_ONLY_NO_ORDER`` en TODOS los eventos.

C8. Un estado terminal (``ACCEPTANCE_LOST``, ``POI_INVALID``,
    ``EXPANSION_NO_ENTRY``, y ``OBSERVABLE_SETUP`` ya alcanzado) no se
    reescribe. No se procesan M5/M1 para esos eventos.

La identidad del evento, ``observed_at`` y el ``transition_history`` previo se
conservan; solo se anota una transición nueva cuando el estado cambia a
``OBSERVABLE_SETUP``, con``at`` = primer instante en que toda la evidencia es
conocida (siempre ``<= cutoff``).
"""

from __future__ import annotations

SECONDS = {"D1": 86400, "H4": 14400, "H1": 3600, "M15": 900, "M5": 300, "M1": 60}

RETESTING = "RETESTING_POI"
WAIT = "WAIT_M5_M1_CONFIRMATION"
CONFIRMED = "M5_STRUCTURE_CONFIRMED"
OBSERVABLE = "OBSERVABLE_SETUP"
NO_STOP = "NO_STRUCTURAL_STOP"
MODE = "OBSERVE_ONLY_NO_ORDER"

_TARGET_SATISFIED = "SATISFIED_TP1_3R_TP2_5R"
_PLACEHOLDERS = frozenset({"M5_M1_CONFIRMATION_NOT_LOADED", "STRUCTURAL_STOP_NOT_DEFINED"})
_TERMINAL = frozenset({"ACCEPTANCE_LOST", "POI_INVALID", "EXPANSION_NO_ENTRY", OBSERVABLE})


# --------------------------------------------------------------------------- #
# lectura de velas cerradas                                                    #
# --------------------------------------------------------------------------- #
def _closed_bars(rows, tf, cutoff):
    """C1: filas con cierre nominal ``<= cutoff``, sin mirar el futuro."""
    seconds = SECONDS.get(tf)
    if seconds is None or not rows:
        return []
    cutoff = int(cutoff)
    bars = []
    for row in rows:
        try:
            opened = int(row[0])
            o, h, low, c = (float(row[1]), float(row[2]), float(row[3]), float(row[4]))
        except (TypeError, ValueError, IndexError):
            continue
        closed = opened + seconds
        if closed > cutoff or h < low or (h == 0.0 and low == 0.0 and c == 0.0):
            continue
        bars.append({"opened": opened, "closed": closed, "open": o,
                     "high": h, "low": low, "close": c})
    return bars


def _ts(value):
    """Epoch entero o ``None``; acepta ints, floats y objetos con timestamp."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(value.timestamp())
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _pivots(bars, digits):
    """C2: swings confirmados con dos velas cerradas a cada lado."""
    found = []
    for i in range(2, len(bars) - 2):
        high = [round(bars[j]["high"], digits) for j in range(i - 2, i + 3)]
        low = [round(bars[j]["low"], digits) for j in range(i - 2, i + 3)]
        price = round(bars[i]["high"], digits)
        if price >= max(high[0], high[1]) and price > max(high[3], high[4]):
            found.append({"kind": "H", "price": price, "index": i,
                          "at": bars[i]["closed"], "confirmed_at": bars[i + 2]["closed"]})
        price = round(bars[i]["low"], digits)
        if price <= min(low[0], low[1]) and price < min(low[3], low[4]):
            found.append({"kind": "L", "price": price, "index": i,
                          "at": bars[i]["closed"], "confirmed_at": bars[i + 2]["closed"]})
    return found


# --------------------------------------------------------------------------- #
# evidencia estructural                                                        #
# --------------------------------------------------------------------------- #
def _structure(bars, direction, not_before, digits):
    """C3: primera ruptura por cierre de un swing confirmado en ``direction``."""
    wanted = "H" if direction > 0 else "L"
    refs = [p for p in _pivots(bars, digits) if p["kind"] == wanted]
    for bar in bars:
        if bar["closed"] < not_before:
            continue
        known = [p for p in refs if p["confirmed_at"] < bar["closed"]]
        if not known:
            continue
        ref = known[-1]
        price = round(ref["price"], digits)
        close = round(bar["close"], digits)
        if not (close > price if direction > 0 else close < price):
            continue
        prior = [p for p in refs if p["confirmed_at"] < ref["confirmed_at"]]
        if not prior:
            kind = "MSS"
        else:
            previous = round(prior[-1]["price"], digits)
            if (direction > 0 and previous < price) or (direction < 0 and previous > price):
                kind = "BOS"
            elif (direction > 0 and previous > price) or (direction < 0 and previous < price):
                kind = "CHOCH"
            else:
                kind = "MSS"
        return {"kind": kind, "at": bar["closed"], "level": price,
                "reference_at": ref["at"], "close": close}
    return None


def _defense(bars, direction, level, poi, retest_at, digits):
    """C4: primer cierre M5 que defiende la POI/nivel tras el retest."""
    if poi is not None:
        zone_low = round(float(poi.get("low")), digits)
        zone_high = round(float(poi.get("high")), digits)
    else:
        zone_low = zone_high = round(float(level), digits)
    broken = round(float(level), digits)
    for bar in bars:
        if bar["closed"] < retest_at:
            continue
        low = round(bar["low"], digits)
        high = round(bar["high"], digits)
        close = round(bar["close"], digits)
        if not (low <= zone_high and high >= zone_low):
            continue
        favorable = (close > broken and close >= zone_low) if direction > 0 \
            else (close < broken and close <= zone_high)
        if favorable:
            return bar["closed"]
    return None


def _origin_swing(m5_bars, m1_bars, pivots5, direction, retest_at, digits):
    """C5.1: swing de origen previo al retest, intacto tras él."""
    wanted = "L" if direction > 0 else "H"
    # A pivot whose two confirmation candles close after the retest was not
    # knowable when the retest occurred.  Filtering by ``confirmed_at`` keeps
    # the origin swing causal instead of allowing a later replay to rewrite
    # the stop basis.
    candidates = [p for p in pivots5 if p["kind"] == wanted
                  and p["at"] < retest_at
                  and p["confirmed_at"] <= retest_at]
    if not candidates:
        return None
    swing = candidates[-1]
    for bar in list(m5_bars) + list(m1_bars):
        if bar["closed"] <= retest_at:
            continue
        close = round(bar["close"], digits)
        if (direction > 0 and close < swing["price"]) or \
                (direction < 0 and close > swing["price"]):
            return None
    return swing


def _reaction_pivot(bars, direction, start, end, digits):
    """C5.2/C5.3: extremo estructural confirmado dentro de la reacción."""
    wanted = "L" if direction > 0 else "H"
    candidates = [p for p in _pivots(bars, digits)
                  if p["kind"] == wanted and p["at"] >= start
                  and p["confirmed_at"] >= start
                  and (end is None or p["confirmed_at"] <= end)]
    return candidates[-1] if candidates else None


def _stop(m5_bars, m1_bars, pivots5, direction, retest_at,
          m5_structure_at, m1_structure_at, digits, cutoff):
    """C5: stop informativo siguiendo el orden de autoridad."""
    origin = _origin_swing(m5_bars, m1_bars, pivots5, direction, retest_at, digits)
    if origin is not None:
        return {"basis": "ORIGIN_SWING_INTACT", "price": origin["price"],
                "at": origin["at"]}
    m5 = _reaction_pivot(m5_bars, direction, retest_at,
                         m5_structure_at if m5_structure_at is not None else cutoff, digits)
    if m5 is not None:
        return {"basis": "M5_REACTION_EXTREME", "price": m5["price"], "at": m5["at"]}
    m1 = _reaction_pivot(m1_bars, direction, retest_at,
                         m1_structure_at if m1_structure_at is not None else cutoff, digits)
    if m1 is not None:
        return {"basis": "M1_CONFIRMED_EXTREME", "price": m1["price"], "at": m1["at"]}
    return {"basis": NO_STOP, "price": None, "at": None}


def _primary_poi(event):
    primary = event.get("primary_poi")
    for candidate in event.get("poi_candidates") or ():
        if candidate.get("zone_id") == primary:
            return candidate
    return None


def _known_liquidity(m5_bars, m1_bars, direction, level, accept_time,
                     reference, digits):
    """C6: liquidez conocida al corte, ordenada de más cercana a más lejana."""
    found = []

    def add(kind, price, observed_at):
        value = round(float(price), digits)
        favorable = value > reference if direction > 0 else value < reference
        if favorable:
            found.append({"kind": kind, "price": value,
                          "observed_at": _ts(observed_at)})

    if level is not None and accept_time is not None:
        add("BROKEN_LEVEL", level, accept_time)
    wanted = "H" if direction > 0 else "L"
    for tf, bars in (("M5", m5_bars), ("M1", m1_bars)):
        for pivot in _pivots(bars, digits):
            if pivot["kind"] == wanted:
                add(tf + "_SWING", pivot["price"], pivot["confirmed_at"])
    found.sort(key=lambda row: (row["price"] if direction > 0 else -row["price"],
                                row["observed_at"], row["kind"]))
    return found


def _target_policy(liquidity, stop, reference, direction, digits):
    """C6: TP1>=3R y TP2>=5R como observación, jamás como promesa."""
    empty = {"status": "NO_STRUCTURAL_REFERENCE", "price": None, "at": None}
    if reference is None:
        return empty
    if stop["basis"] == NO_STOP or stop["price"] is None:
        return {"status": "NO_STOP_NO_RISK_UNIT", "price": None, "at": None}
    if not liquidity:
        return {"status": "NO_KNOWN_LIQUIDITY_AT_CUTOFF", "price": None, "at": None}
    risk = round(abs(reference - stop["price"]), digits)
    if risk <= 0:
        return {"status": "NO_STOP_NO_RISK_UNIT", "price": None, "at": None}
    nearest = liquidity[0]
    distance = round((nearest["price"] - reference) * direction, digits)
    if distance < 3 * risk:
        status = "TP1_BELOW_3R"
    elif distance < 5 * risk:
        status = "TP2_BELOW_5R"
    else:
        status = _TARGET_SATISFIED
    return {"status": status, "price": nearest["price"], "at": nearest["observed_at"]}


# --------------------------------------------------------------------------- #
# payload                                                                      #
# --------------------------------------------------------------------------- #
def _base_fields():
    """Campos de confirmación presentes pero vacíos: nunca datos inventados."""
    return {
        "confirmation_state": WAIT,
        "defense_at": None,
        "m5_structure_kind": None,
        "m5_structure_at": None,
        "m1_structure_kind": None,
        "m1_structure_at": None,
        "stop_basis": NO_STOP,
        "stop_price": None,
        "stop_observed_at": None,
        "target_policy_status": "NO_STRUCTURAL_REFERENCE",
        "target_price": None,
        "target_liquidity": [],
    }


def _finish(event, fields, pending, reason):
    kept = [item for item in (event.get("pending_evidence") or [])
            if item not in _PLACEHOLDERS]
    for item in pending:
        if item not in kept:
            kept.append(item)
    event.update(fields)
    event["pending_evidence"] = kept
    event["wait_reason"] = "; ".join(kept) if kept else "OBSERVATION_ONLY"
    event["reason"] = reason


def _wait(event, cause, *, extra=()):
    """C1/C7: espera explícita sin estructura inventada."""
    fields = _base_fields()
    pending = ["M5_M1_CONFIRMATION_NOT_LOADED", *extra]
    _finish(event, fields, pending, cause)


def attach_confirmations(result, lower_source, cutoff, *, digits=2, loader_error=None):
    """Añade confirmación M5/M1 observacional a ``result`` y lo devuelve.

    Solo los eventos en ``current_state == RETESTING_POI`` se analizan. Los
    estados terminales y los eventos sin retest no se tocan salvo por los
    indicadores de seguridad ``mode`` / ``entry_authorized``.

    ``result['ict3']['load']`` informa ``m5_loaded``, ``m1_loaded``,
    ``last_closed_m5``, ``last_closed_m1``, ``coverage`` y ``load_reason``.
    Si ``lower_source`` es ``None`` o hay ``loader_error``, el evento queda en
    ``WAIT_M5_M1_CONFIRMATION`` con el motivo explícito y sin datos inventados.
    """
    block = result.setdefault("ict3", {})
    events = block.get("events") or []
    block["mode"] = MODE
    for event in events:
        event["entry_authorized"] = False
        event["mode"] = MODE

    load = {
        "m5_loaded": False,
        "m1_loaded": False,
        "last_closed_m5": None,
        "last_closed_m1": None,
        "coverage": {"m5_bars_closed": 0, "m1_bars_closed": 0,
                     "m5_first_closed": None, "m1_first_closed": None,
                     "events_requested": 0},
        "load_reason": "NOT_REQUESTED_NO_M15_RETEST",
    }
    block["load"] = load

    retesting = [event for event in events
                 if event.get("current_state") == RETESTING
                 and event.get("current_state") not in _TERMINAL]
    if not retesting:
        return result

    load["coverage"]["events_requested"] = len(retesting)

    def wait_all(cause):
        for event in retesting:
            _wait(event, cause)
        return result

    if loader_error:
        load["load_reason"] = "LOWER_SOURCE_ERROR: " + str(loader_error)
        return wait_all(load["load_reason"])
    if lower_source is None:
        load["load_reason"] = "LOWER_SOURCE_UNAVAILABLE"
        return wait_all(load["load_reason"])
    try:
        _, _, bars, _ = lower_source
    except (TypeError, ValueError):
        load["load_reason"] = "LOWER_SOURCE_MALFORMED"
        return wait_all(load["load_reason"])

    m5_bars = _closed_bars(bars.get("M5") if hasattr(bars, "get") else None, "M5", cutoff)
    m1_bars = _closed_bars(bars.get("M1") if hasattr(bars, "get") else None, "M1", cutoff)
    if not m5_bars:
        load["load_reason"] = "NO_CLOSED_M5_BARS_AT_CUTOFF"
        return wait_all(load["load_reason"])

    load["m5_loaded"] = True
    load["m1_loaded"] = bool(m1_bars)
    load["last_closed_m5"] = m5_bars[-1]["closed"]
    load["coverage"]["m5_bars_closed"] = len(m5_bars)
    load["coverage"]["m5_first_closed"] = m5_bars[0]["closed"]
    load["load_reason"] = "M5_M1_LOADED" if m1_bars else "M1_BARS_UNAVAILABLE_M5_USED"
    if m1_bars:
        load["last_closed_m1"] = m1_bars[-1]["closed"]
        load["coverage"]["m1_bars_closed"] = len(m1_bars)
        load["coverage"]["m1_first_closed"] = m1_bars[0]["closed"]

    pivots5 = _pivots(m5_bars, digits)
    for event in retesting:
        direction = int(event.get("direction") or 0)
        level = event.get("level")
        retest_at = _ts(event.get("retest_at"))
        if direction == 0 or level is None or retest_at is None:
            _wait(event, "RETEST_EVIDENCE_INCOMPLETE")
            continue
        level = float(level)
        poi = _primary_poi(event)

        defense_at = _defense(m5_bars, direction, level, poi, retest_at, digits)
        m5_structure = _structure(m5_bars, direction, retest_at, digits)
        m1_structure = _structure(m1_bars, direction, retest_at, digits) if m1_bars else None
        stop = _stop(m5_bars, m1_bars, pivots5, direction, retest_at,
                     m5_structure["at"] if m5_structure else None,
                     m1_structure["at"] if m1_structure else None, digits, int(cutoff))

        if defense_at is not None:
            defense_bar = next((bar for bar in m5_bars if bar["closed"] == defense_at), None)
            reference = round(defense_bar["close"], digits) if defense_bar else None
        elif m5_structure is not None:
            reference = m5_structure["close"]
        else:
            reference = None
        liquidity = (_known_liquidity(m5_bars, m1_bars, direction, level,
                                     event.get("accept_time"), reference, digits)
                     if reference is not None else [])
        target = _target_policy(liquidity, stop, reference, direction, digits)

        fields = _base_fields()
        fields.update({
            "confirmation_state": CONFIRMED if defense_at is not None and m5_structure else WAIT,
            "defense_at": defense_at,
            "m5_structure_kind": m5_structure["kind"] if m5_structure else None,
            "m5_structure_at": m5_structure["at"] if m5_structure else None,
            "m1_structure_kind": m1_structure["kind"] if m1_structure else None,
            "m1_structure_at": m1_structure["at"] if m1_structure else None,
            "stop_basis": stop["basis"],
            "stop_price": stop["price"],
            "stop_observed_at": stop["at"],
            "target_policy_status": target["status"],
            "target_price": target["price"],
            "target_liquidity": liquidity,
        })

        pending = []
        if defense_at is None:
            pending.append("DEFENSE_NOT_CONFIRMED_M5")
        if m5_structure is None:
            pending.append("M5_STRUCTURE_NOT_CONFIRMED")
        if stop["basis"] == NO_STOP:
            pending.append("NO_STRUCTURAL_STOP")
        if target["status"] != _TARGET_SATISFIED:
            pending.append("TARGET_POLICY_" + target["status"])
        if fields["confirmation_state"] == WAIT:
            pending.append("M5_M1_CONFIRMATION_NOT_COMPLETE")

        complete = (defense_at is not None and m5_structure is not None
                    and stop["basis"] != NO_STOP and stop["price"] is not None
                    and target["status"] == _TARGET_SATISFIED
                    and target["price"] is not None)
        if complete:
            known = [value for value in (defense_at, fields["m5_structure_at"],
                                         stop["at"], target["at"]) if value is not None]
            at = int(max(known)) if known else int(cutoff)
            fields["confirmation_state"] = CONFIRMED
            event["current_state"] = OBSERVABLE
            event["state_time"] = at
            history = list(event.get("transition_history") or [])
            history.append({"from": RETESTING, "to": OBSERVABLE, "at": at,
                            "reason": "retest_defense_m5_structure_stop_and_known_liquidity"})
            event["transition_history"] = history
        _finish(event, fields, pending,
                "OBSERVABLE_ONLY_EVIDENCE_COMPLETE" if complete
                else "; ".join(pending))
    return result


__all__ = [
    "SECONDS", "RETESTING", "WAIT", "CONFIRMED", "OBSERVABLE", "NO_STOP", "MODE",
    "attach_confirmations",
]
