"""Read-only MT5 adapter for the pinned ICT 2.0 market engine."""
from bisect import bisect_right
from datetime import datetime, timezone
from functools import lru_cache
import math
import hashlib
import sys
import time

import MetaTrader5 as mt5
import pandas as pd

from diario import ROOT, FRAMES, checked, connection, mt5_time, workspace_key
from ict22 import book22_setups
from ict3_link import link_breaks
from ict3_confirm import attach_confirmations
from motor_smc.instrumentos import MT5_SYMBOLS

REVISION = "f453bf2a9d35997cec774048a7ead25237399ac9"
SOURCE = ROOT / "motor_smc" / "fuentes" / "ict2"
SYMBOL = "EURUSD"
EURUSD_DIGITS = 5
PROFILE = ("D1", "H4", "H1", "M15")
SECONDS = {"D1": 86400, "H4": 14400, "H1": 3600, "M15": 900, "M5": 300, "M1": 60}
# Fixed warm-up for comparisons at the same market cutoff.
BAR_COUNT = 550
MIN_HISTORY = 40


@lru_cache(maxsize=1)
def engine():
    head = SOURCE / ".git" / "HEAD"
    if not head.is_file() or head.read_text().strip() != REVISION:
        raise RuntimeError("Falta la revisión de ICT 2.0 indicada en el README.")
    sys.path.insert(0, str(SOURCE))
    from engine.bos import detect_market_structure
    from engine.daily_motor import build_daily_motor_snapshot
    from engine.ltf_canonical_feed import build_ltf_canonical_feed
    from engine.plan import dealing_range_pd
    from tools.displacement import detect_displacement
    return (detect_market_structure, build_daily_motor_snapshot, build_ltf_canonical_feed,
            dealing_range_pd, detect_displacement)


def read_bars(settings, symbol, timeframes):
    with connection(settings):
        info = checked(mt5.symbol_info(symbol), f"símbolo {symbol}")
        rates = {
            tf: checked(mt5.copy_rates_from_pos(symbol, FRAMES[tf], 0, BAR_COUNT + 1), f"velas {symbol} {tf}")
            for tf in timeframes
        }
    bars = {
        tf: tuple((int(row["time"]), *[float(row[k]) for k in ("open", "high", "low", "close")])
                  for row in rows)
        for tf, rows in rates.items()
    }
    spreads = tuple((int(row["time"]), int(row["spread"]) * info.point)
                    for row in rates["M15"][:-1]) if "M15" in rates else ()
    return info.digits, info.trade_tick_size or info.point, bars, spreads


def closed_frame(rows, tf, cutoff=None):
    # The MT5 position-zero bar is never sent to the engine. A successor
    # confirms that the previous bar is no longer the terminal's live bar.
    # Nominal maturity prevents a weekend gap from stretching Friday's bar.
    values = []
    for row, successor in zip(rows, rows[1:]):
        opened, o, h, low, c = row
        closed = min(opened + SECONDS[tf], successor[0])
        if cutoff is None or closed <= cutoff:
            values.append((opened, closed, o, h, low, c))
    frame = pd.DataFrame(values, columns=("opened", "closed", "open", "high", "low", "close"))
    frame["time"] = pd.to_datetime(frame["closed"], unit="s", utc=True)
    return frame


def timestamp(value):
    return int(value.timestamp()) if value is not None else None


def previous_daily(daily_rows, cutoff):
    sessions = [row for row in daily_rows if row[0] <= cutoff]
    return sessions[-2:] if len(sessions) >= 2 else None


def classify_range_bar(opened, high, low, close, previous, pdh, pdl, *, digits=EURUSD_DIGITS):
    """Book 22 event for a closed candle against two known range levels."""
    o, h, low, close, previous, pdh, pdl = (
        round(value, digits) for value in (opened, high, low, close, previous, pdh, pdl))

    def side(value):
        return "PDH" if value > pdh else "PDL" if value < pdl else None

    above, below = h > pdh, low < pdl
    close_side, previous_side, open_side = side(close), side(previous), side(o)
    level = "PDH" if above else "PDL" if below else None
    if above and below:
        kind, level = "both", None
    elif open_side and open_side != previous_side:
        kind, level = "gap", open_side
    elif close_side:
        if close_side == previous_side:
            return None
        kind, level = "break", close_side
    elif pdl < close < pdh and previous_side:
        kind, level = "late_return", previous_side
    elif level:
        kind = "sweep" if pdl < close < pdh else "boundary_close"
    elif h == pdh or low == pdl:
        kind, level = "touch", "PDH" if h == pdh else "PDL"
    else:
        return None
    return {"kind": kind, "level": level, "high": h, "low": low,
            "close": close, "close_side": close_side}


def daily_liquidity(daily_rows, m15, cutoff, *, digits=EURUSD_DIGITS):
    """Book 22. Use the previous broker D1 and classify closed M15 candles."""
    sessions = previous_daily(daily_rows, cutoff)
    if sessions is None:
        return None
    source, current = sessions
    opened, _, high, low, prior_close = source
    session = current[0]
    pdh, pdl, previous = (round(value, digits) for value in (high, low, prior_close))
    if pdh <= pdl:
        return None

    source_m15 = m15.loc[(m15["opened"] >= opened) & (m15["closed"] <= session)]
    highs = source_m15.loc[source_m15["high"].round(digits) == pdh, "opened"]
    lows = source_m15.loc[source_m15["low"].round(digits) == pdl, "opened"]
    events = []
    candles = m15.loc[(m15["opened"] >= session) & (m15["closed"] <= cutoff)]
    for bar in candles.itertuples(index=False):
        event = classify_range_bar(bar.open, bar.high, bar.low, bar.close, previous, pdh, pdl, digits=digits)
        previous = bar.close
        if event:
            events.append({**event, "time": int(bar.closed)})
    return {
        "pdh": pdh, "pdl": pdl, "source_open": opened, "session_open": session,
        "pdh_m15_open": int(highs.iloc[0]) if not highs.empty else None,
        "pdl_m15_open": int(lows.iloc[0]) if not lows.empty else None,
        "m15_count": len(candles), "events": events,
    }


def last_friday_reference(daily_rows, cutoff, *, digits=EURUSD_DIGITS):
    """Return the newest Friday D1 that was fully closed at the cutoff."""
    found = None
    for index, row in enumerate(daily_rows):
        opened, _, high, low, _ = row
        successor = daily_rows[index + 1][0] if index + 1 < len(daily_rows) else None
        closed = min(opened + SECONDS["D1"], successor) if successor is not None else opened + SECONDS["D1"]
        if closed > cutoff or datetime.fromtimestamp(opened, timezone.utc).weekday() != 4:
            continue
        high, low = round(high, digits), round(low, digits)
        if high <= low:
            continue
        found = {"high": high, "low": low, "source_open": opened, "source_close": closed}
    return found


def break_event_id(symbol, session_open, level_name, level, direction,
                   signal_open, signal_close, digits):
    """Deterministic id: stable for the same symbol, D1 session, level, side and signal bar."""
    identity = "|".join((
        str(symbol), str(int(session_open)), str(level_name),
        f"{float(level):.{int(digits)}f}", str(int(direction)),
        str(int(signal_open)), str(int(signal_close)),
    ))
    return "evt_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def daily_break_studies(daily_rows, m15, cutoff, *, symbol=SYMBOL, digits=EURUSD_DIGITS,
                        force_body_ratio=0.70, force_body_multiple=1.5,
                        force_close_extension=0.50):
    """Causal ICT 3.0 observations for PDH/PDL breaks.

    This is deliberately an observation layer: it never creates an order,
    position, size, or fill. It preserves strong accepted breaks even when no
    structural stop or retest exists yet.
    """
    if m15 is None or m15.empty or len(daily_rows) < 2:
        return []
    studies = []
    rows = list(m15.itertuples(index=False))
    row_cursor = 0
    for day_index in range(1, len(daily_rows)):
        day = daily_rows[day_index]
        if day[0] > cutoff:
            break
        source = daily_rows[day_index - 1]
        next_open = daily_rows[day_index + 1][0] if day_index + 1 < len(daily_rows) else None
        session_end = min(next_open, cutoff) if next_open is not None else cutoff
        while row_cursor < len(rows) and rows[row_cursor].opened < day[0]:
            row_cursor += 1
        session_end_index = row_cursor
        while session_end_index < len(rows) and rows[session_end_index].closed <= session_end:
            session_end_index += 1
        session = rows[row_cursor:session_end_index]
        row_cursor = session_end_index
        if not session:
            continue
        for direction, level_name, level in ((1, "PDH", round(source[2], digits)),
                                             (-1, "PDL", round(source[3], digits))):
            previous_side = 0
            candidate = None
            accepted = None
            for index, bar in enumerate(session):
                side = 1 if bar.close > level else -1 if bar.close < level else 0
                outside = side == direction
                prior = session[max(0, index - 14):index]
                ranges = [float(item.high - item.low) for item in prior if item.high >= item.low]
                average_range = sum(ranges) / len(ranges) if ranges else None
                candle_range = max(float(bar.high - bar.low), 0.0)
                body = abs(float(bar.close - bar.open))
                body_ratio = body / candle_range if candle_range else 0.0
                body_multiple = body / average_range if average_range else None
                close_extension = direction * (float(bar.close) - level) / average_range \
                    if average_range else None
                close_location = (direction * (float(bar.close) - float(bar.low if direction == 1 else bar.high))
                                  / candle_range if candle_range else 0.0)
                if outside and previous_side != direction and candidate is None:
                    candidate = {
                        "session_open": int(day[0]), "source_open": int(source[0]),
                        "level_name": level_name, "level": level, "direction": direction,
                        "signal_open": int(bar.opened), "signal_close": int(bar.closed),
                        "body_ratio": round(body_ratio, 4),
                        "body_multiple": round(body_multiple, 4) if body_multiple is not None else None,
                        "close_extension": round(close_extension, 4) if close_extension is not None else None,
                        "close_location": round(close_location, 4),
                        "strong_body": body_ratio >= force_body_ratio,
                        "strong_range": body_multiple is not None and body_multiple >= force_body_multiple,
                        "strong_extension": close_extension is not None and close_extension >= force_close_extension,
                        "strong": body_ratio >= force_body_ratio and body_multiple is not None
                                  and body_multiple >= force_body_multiple and close_extension is not None
                                  and close_extension >= force_close_extension,
                    }
                    candidate["state"] = "BREAK_CANDIDATE"
                    candidate["event_id"] = break_event_id(
                        symbol, candidate["session_open"], level_name, level,
                        direction, candidate["signal_open"], candidate["signal_close"], digits)
                    candidate["observed_at"] = int(bar.closed)
                    candidate["state_time"] = int(bar.closed)
                if candidate is not None and accepted is None:
                    if not outside:
                        candidate["state"] = "FAILED_BREAK"
                        candidate["failure_time"] = int(bar.closed)
                        candidate["state_time"] = int(bar.closed)
                        studies.append(candidate)
                        candidate = None
                    elif candidate["signal_open"] != bar.opened and index > 0:
                        previous = session[index - 1]
                        previous_side = 1 if previous.close > level else -1 if previous.close < level else 0
                        if previous_side == direction:
                            candidate["state"] = "ACCEPTED_BREAK_WAIT_RETEST"
                            candidate["accept_time"] = int(bar.closed)
                            candidate["accept_open"] = int(bar.opened)
                            candidate["state_time"] = int(bar.closed)
                            accepted = candidate
                            studies.append(candidate)
                            candidate = None
                previous_side = side
            if candidate is not None:
                # No M15 bar closed back inside the level, so this is still an
                # open candidate. FAILED_BREAK is only set above, together with
                # a real failure_time from the bar that closed back inside.
                candidate["state"] = "BREAK_CANDIDATE"
                candidate["state_time"] = candidate["signal_close"]
                studies.append(candidate)
    return studies


def zone_payload(obj, frame, relationships):
    return {
        "id": f"{obj.origin_tf}-{timestamp(obj.confirmation_time)}-{obj.type.value}-{obj.direction}",
        "tf": obj.origin_tf, "kind": "FVG" if obj.type.value == "FVG" else "OB",
        "direction": obj.direction, "low": obj.zone_low, "high": obj.zone_high,
        "open": int(frame.iloc[obj.confirmation_bar]["opened"]),
        "confirmed": timestamp(obj.confirmation_time), "touch": timestamp(obj.first_touch_time),
        "related": obj.id in relationships,
    }


def parent_event(frame, direction):
    # The engine annotates using only the truncated frame for this decision.
    # A BOS must meet the engine's real-BOS gate. A CHOCH is read from the
    # canonical active state, never from an unconfirmed event flag.
    bos = (frame["bos_dir"] == direction) & frame["bos_real"] & (frame["bos_status"] == "active")
    choch = (frame["choch_dir"] == direction) & (frame["choch_status"] == "active")
    events = frame.loc[bos | choch]
    if events.empty:
        return None
    event = events.iloc[-1]
    return {"kind": "CHOCH" if choch.loc[event.name] else "BOS", "time": timestamp(event["time"])}


def candidate_pois(objects, frames, annotated, snapshot, dealing_range, displacement):
    """Compose the thesis criteria from canonical outputs; keep them candidates."""
    direction = snapshot["direction"]
    if not direction or not snapshot["context"]["allowed"]:
        return []
    t = frames["M15"]["time"].iloc[-1]
    area = dealing_range(frames["D1"], t)
    if not math.isfinite(area["eq"]):
        return []
    found = []
    for tf, parent in (("H4", "D1"), ("H1", "H4")):
        anchor = parent_event(annotated[parent], direction)
        if not anchor:
            continue
        frame = frames[tf]
        movement = displacement(frame)
        field = "displacement_bullish" if direction > 0 else "displacement_bearish"
        for obj in objects[tf]:
            if obj.direction != direction or obj.first_touch_time is not None:
                continue
            # Require the whole zone on the favorable side of the D1 midpoint.
            inside = (area["range_low"] <= obj.zone_low < obj.zone_high <= area["eq"]
                      if direction > 0 else area["eq"] <= obj.zone_low < obj.zone_high <= area["range_high"])
            impulse_bar = obj.meta.get("middle_bar", obj.confirmation_bar)
            if not inside or not bool(movement.iloc[impulse_bar][field]):
                continue
            payload = zone_payload(obj, frame, set())
            payload.update(kind="POI", base="FVG" if obj.type.value == "FVG" else "OB",
                           parent=parent, anchor=anchor, evaluated=timestamp(t))
            found.append(payload)
    return sorted(found, key=lambda row: row["confirmed"], reverse=True)[:3]


def ict3_payload(breaks, zones, m15, cutoff, *, symbol=""):
    """Versioned observation-only ICT 3.0 view built from causal links."""
    accepted = [event for event in breaks if event.get("state") == "ACCEPTED_BREAK_WAIT_RETEST"]
    links = link_breaks(accepted, zones, m15, cutoff)
    events = []
    for event, link in zip(accepted, links):
        state = link.get("current_state")
        primary = link.get("primary_poi")
        pending = []
        if not primary:
            pending.append("CAUSAL_POI_NOT_CONFIRMED")
        if state == "ACCEPTED_BREAK_WAIT_RETEST" and primary:
            pending.append("RETEST_NOT_OBSERVED")
        if state == "RETESTING_POI":
            pending.extend(["M5_M1_CONFIRMATION_NOT_LOADED", "STRUCTURAL_STOP_NOT_DEFINED"])
        if state == "EXPANSION_NO_ENTRY":
            pending.append("NO_RETEST_WITHIN_COMPARABLE_WINDOWS")
        if state in ("ACCEPTANCE_LOST", "POI_INVALID"):
            pending.append("BREAK_INVALIDATED")
        events.append({
            "event_id": event.get("event_id"),
            "symbol": symbol,
            "session_open": event.get("session_open"),
            "observed_at": event.get("observed_at"),
            "state_time": event.get("state_time"),
            "accept_time": event.get("accept_time"),
            "level_name": event.get("level_name"),
            "level": event.get("level"),
            "direction": event.get("direction"),
            "force": {
                "body_ratio": event.get("body_ratio"),
                "body_multiple": event.get("body_multiple"),
                "close_extension": event.get("close_extension"),
                "close_location": event.get("close_location"),
                "strong": event.get("strong"),
            },
            "link_state": link.get("link_state"),
            "current_state": state,
            "retest_at": link.get("retest_at"),
            "poi_candidates": link.get("poi_candidates", []),
            "primary_poi": primary,
            "transition_history": link.get("transition_history", []),
            "window_results": link.get("window_results", {}),
            "observation_windows": link.get("observation_windows", []),
            "pending_evidence": pending,
            "wait_reason": "; ".join(pending) if pending else "OBSERVATION_ONLY",
            "entry_authorized": False,
        })
    return {
        "schema_version": "0.2-research",
        "mode": "OBSERVE_ONLY_NO_ORDER",
        "events": events,
    }


@lru_cache(maxsize=20)
def analyze_cached(history, selected, cutoff=None, include_sequence=False, *, symbol=SYMBOL,
                   digits=EURUSD_DIGITS, tick=None, spreads=()):
    detect_structure, daily, feed, dealing_range, displacement = engine()
    frames = {tf: closed_frame(rows, tf, cutoff) for tf, rows in history}
    if any(len(frames[tf]) < MIN_HISTORY for tf in PROFILE):
        raise RuntimeError(f"Historial cerrado insuficiente para el perfil ICT de {symbol}.")
    # The current daily snapshot is anchored to the latest closed M15 bar
    # unless reviewing a historical order at its own (server-clock) timestamp.
    decision = frames["M15"]["time"].iloc[-1] if cutoff is None else pd.Timestamp(cutoff, unit="s", tz="UTC")
    decision_epoch = timestamp(decision)
    # Context and POI use the same as-of instant; M1/M5 may show later closed
    # formations without altering the daily snapshot.
    context_frames = {tf: frames[tf].loc[frames[tf]["closed"] <= decision_epoch].reset_index(drop=True)
                      for tf in PROFILE}
    annotated = {tf: detect_structure(frame).frame for tf, frame in context_frames.items()}
    output = {
        tf: feed(context_frames, decision, exec_tf=tf,
                 include_sequence=include_sequence and tf == "M15", symbol=symbol)
        for tf in ("H4", "H1", "M15")
    }
    objects = {tf: result["zones"][tf] for tf, result in output.items()}
    snapshot = daily(annotated, decision_time=decision, canonical_zones=objects,
                     sequence_snapshot=output["M15"]["sequence"])
    if snapshot["entry_authorized"] or snapshot["policy"] != "OBSERVE_ONLY_NO_ORDER":
        raise RuntimeError("El motor de observación devolvió una política inesperada.")

    if selected in output and len(frames[selected]) == len(context_frames[selected]):
        selected_feed = output[selected]
        selected_frame = context_frames[selected]
    else:
        selected_frame = frames[selected]
        selected_feed = feed(frames, selected_frame["time"].iloc[-1] if len(selected_frame) else decision,
                             exec_tf=selected, include_sequence=False, symbol=symbol)
    relations = {object_id for rel in selected_feed.get("relations", [])
                 for object_id in (rel["fvg_id"], rel["ob_id"])}
    marks = [zone_payload(obj, selected_frame, relations)
             for obj in selected_feed["zones"][selected]]
    pois = candidate_pois(objects, context_frames, annotated, snapshot, dealing_range, displacement)
    daily_rows = dict(history)["D1"]
    level_cutoff = max(decision_epoch, daily_rows[-1][0]) if cutoff is None else decision_epoch
    setups = []
    if selected == "M15":
        from engine.plan import _bias_from_frame

        h4 = annotated["H4"]
        closed_h4 = h4["time"].tolist()

        @lru_cache(maxsize=None)
        def trend_at(index):
            return _bias_from_frame(h4, closed_h4[index]) if index >= 0 else "RANGING"

        setups = book22_setups(
            daily_rows, context_frames["M15"], level_cutoff, objects["M15"],
            classify=classify_range_bar, displacement=displacement,
            h4_bias=lambda time: trend_at(bisect_right(closed_h4, time) - 1),
            digits=digits, tick=tick or 10 ** -digits, spreads=dict(spreads),
        )
    breaks = daily_break_studies(daily_rows, context_frames["M15"], level_cutoff,
                                 symbol=symbol, digits=digits)
    return {
        "enabled": True, "source": REVISION, "symbol": symbol, "frame": selected,
        "time_basis": "Reloj MT5", "asof": decision_epoch,
        "latest_closed": int(selected_frame["closed"].iloc[-1]) if len(selected_frame) else None,
        "bias": snapshot["direction_label"], "status": snapshot["status"],
        "context_reason": snapshot["context"]["reason"],
        "regime": snapshot["context"]["regime_stack"],
        "structure": snapshot["ltf"]["structure"],
        "retest": snapshot["ltf"]["retest_state"],
        "sequence": snapshot["sequence"],
        "last_closed_by_tf": {tf: int(frame["closed"].iloc[-1]) for tf, frame in context_frames.items()},
        "ltf_zones": [zone_payload(obj, context_frames["M15"], set()) for obj in objects["M15"]],
        "marks": marks, "pois": pois,
        "daily_liquidity": daily_liquidity(daily_rows, context_frames["M15"], level_cutoff, digits=digits),
        "ict3_breaks": breaks,
        "ict3": ict3_payload(breaks, objects["M15"], context_frames["M15"], level_cutoff,
                             symbol=symbol),
        "book22": setups,
    }


def ict_chart(settings, symbol, frame, cutoff=None):
    workspace_key(symbol, frame)
    if symbol not in MT5_SYMBOLS:
        return {"enabled": False, "reason": "ICT automático se aplica al universo confirmado de MT5."}
    source = read_bars(settings, symbol, tuple(dict.fromkeys((*PROFILE, frame))))
    result = analyze_bars(symbol, frame, source, cutoff)
    needs_lower = any(event.get("current_state") == "RETESTING_POI"
                      for event in result.get("ict3", {}).get("events", []))
    as_of = cutoff if cutoff is not None else int(time.time())
    if needs_lower:
        try:
            lower, loader_error = read_bars(settings, symbol, ("M5", "M1")), None
        except Exception as error:
            lower, loader_error = None, f"MT5 M5/M1: {error}"
    else:
        lower, loader_error = None, "NOT_REQUESTED_NO_M15_RETEST"
    return attach_confirmations(result, lower, as_of, loader_error=loader_error)


def analyze_bars(symbol, frame, source, cutoff=None):
    digits, tick, bars, spreads = source
    # Exclude the evolving OHLC of position zero from the cache and analysis.
    history = tuple((tf, (*rows[:-1], (rows[-1][0], 0, 0, 0, 0)) if rows else ())
                    for tf, rows in bars.items())
    result = analyze_cached(history, frame, cutoff, symbol=symbol, digits=digits, tick=tick, spreads=spreads)
    reference_cutoff = cutoff if cutoff is not None else int(time.time())
    result["friday_reference"] = last_friday_reference(
        bars["D1"], reference_cutoff, digits=digits)
    return {k: v for k, v in result.items() if k not in {"ltf_zones", "sequence"}}


def replay(settings, deal_rows):
    digits, tick, bars, spreads = read_bars(settings, SYMBOL, PROFILE)
    history = tuple(bars.items())
    report = []
    for moment in sorted({row["time"] for row in deal_rows}):
        result = analyze_cached(history, "M15", moment, include_sequence=True, digits=digits,
                                tick=tick, spreads=spreads)
        events = []
        for deal in (row for row in deal_rows if row["time"] == moment):
            side = 1 if deal["type"] == mt5.DEAL_TYPE_BUY else -1
            covering = []
            for zone in result["ltf_zones"]:
                if zone["direction"] == side and zone["low"] <= deal["price"] <= zone["high"]:
                    covering.append(zone)
            events.append({"position": deal["position_id"], "price": deal["price"],
                           "volume": deal["volume"], "m15_compatible_zone_at_price": covering})
        report.append({key: result[key] for key in (
            "bias", "status", "context_reason", "regime", "structure", "retest",
            "sequence", "last_closed_by_tf", "pois")} |
            {"time": mt5_time(moment), "events": events})
    return report
