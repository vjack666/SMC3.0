"""Historical D1 POI candidates, using the pinned ICT 2.0 detectors."""

import argparse
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import MetaTrader5 as mt5

from diario import checked, config, connection, mt5_time, workspace_key
from ict import REVISION, closed_frame, engine
from motor_smc.instrumentos import SYMBOL_GROUPS

HISTORY_CACHE = OrderedDict()
HISTORY_CACHE_SIZE = 48


def window_start(cutoff):
    end = datetime.fromtimestamp(cutoff, timezone.utc)
    try:
        return end.replace(year=end.year - 2)
    except ValueError:  # February 29 has no counterpart two years earlier.
        return end.replace(year=end.year - 2, day=28)


def date_cutoff(value):
    """Include the full date according to the broker's D1 calendar."""
    next_day = date.fromisoformat(value) + timedelta(days=1)
    return int(datetime.combine(next_day, datetime.min.time(), timezone.utc).timestamp())


def candle(row):
    return {
        "opened": mt5_time(row.opened), "closed": mt5_time(row.closed),
        "open": row.open, "high": row.high, "low": row.low, "close": row.close,
    }


def zone_lifecycle(frame, after_index, low, high, direction, digits):
    """Count contacts through the first strict close beyond the distal edge."""
    low, high = round(low, digits), round(high, digits)
    touch_dates = []
    episodes = 0
    touching = False
    first_wick = first_close = None
    for row in frame.iloc[after_index + 1:].itertuples(index=False):
        bar_low, bar_high, close = (round(value, digits) for value in (row.low, row.high, row.close))
        overlaps = bar_high >= low and bar_low <= high
        if overlaps:
            touch_dates.append(mt5_time(row.opened))
            episodes += int(not touching)
        touching = overlaps
        beyond_close = close < low if direction > 0 else close > high
        if beyond_close:
            first_close = candle(row)
            break
        beyond_wick = bar_low < low if direction > 0 else bar_high > high
        if overlaps and beyond_wick and first_wick is None:
            first_wick = candle(row)
    state = ("invalidated_by_close" if first_close else "wick_breach" if first_wick else
             "retested" if touch_dates else "untouched")
    return {"state": state, "contact_bars": len(touch_dates), "contact_episodes": episodes,
            "contact_dates": touch_dates, "first_wick_breach": first_wick,
            "first_close_invalidation": first_close}


def analyze_poi_history(symbol, rows, digits, cutoff):
    detect_structure, _, _, _, detect_displacement = engine()
    from engine.detectors.fvg import detect_fvg
    from engine.detectors.ob import detect_order_blocks

    start = int(window_start(cutoff).timestamp())
    frame = closed_frame(rows, "D1", cutoff)
    window = frame.loc[frame["opened"] >= start]
    if window.empty:
        raise RuntimeError(f"MT5 no entregó velas D1 cerradas dentro del periodo para {symbol}.")

    annotated = detect_structure(frame).frame
    displacement = detect_displacement(frame)
    records = frame.to_dict("records")
    objects = [(kind, obj) for kind, detector in (("FVG", detect_fvg), ("OB", detect_order_blocks))
               for obj in detector(records, timeframe="D1", symbol=symbol)]
    zones = []
    for kind, obj in objects:
        confirmed = obj.confirmation_bar
        origin = obj.meta.get("middle_bar", obj.candidate_bar)
        if frame.at[origin, "opened"] < start:
            continue
        impulse = origin if kind == "FVG" else confirmed
        direction = obj.direction
        field = "displacement_bullish" if direction > 0 else "displacement_bearish"
        has_displacement = bool(displacement.at[impulse, field])
        leg = annotated.iloc[obj.candidate_bar:confirmed + 1]
        bos = (leg["bos_dir"] == direction) & leg["bos_real"] & (leg["bos_status"] == "active")
        choch = (leg["choch_dir"] == direction) & (leg["choch_status"] == "active")
        events = leg.loc[bos | choch]
        anchor = None
        if not events.empty:
            index = events.index[-1]
            anchor = {"kind": "CHOCH" if choch.at[index] else "BOS",
                      "closed": mt5_time(frame.at[index, "closed"])}
        zones.append({
            "kind": kind, "timeframe": "D1", "direction": "bullish" if direction > 0 else "bearish",
            "low": round(obj.zone_low, digits), "high": round(obj.zone_high, digits),
            "origin": candle(frame.iloc[origin]), "first_pattern_bar": candle(frame.iloc[obj.candidate_bar]),
            "confirmation": candle(frame.iloc[confirmed]), "displacement": has_displacement,
            "structure": anchor, "classification": "poi_candidate" if anchor and has_displacement else "geometry",
            **zone_lifecycle(frame, confirmed, obj.zone_low, obj.zone_high, direction, digits),
        })

    return {
        "symbol": symbol, "engine_revision": REVISION, "clock": "MT5",
        "requested_start": mt5_time(start), "cutoff": mt5_time(cutoff),
        "first_closed_d1": mt5_time(window["opened"].iloc[0]),
        "last_closed_d1": mt5_time(window["closed"].iloc[-1]),
        "has_history_before_window": bool(frame["opened"].iloc[0] < start),
        "closed_bars": len(window),
        "zones": sorted(zones, key=lambda zone: zone["confirmation"]["closed"], reverse=True),
    }


def scan_poi_history(settings, symbols, cutoff=None, *, summary=False):
    symbols = list(dict.fromkeys(symbols))
    if not 1 <= len(symbols) <= 26:
        raise ValueError("Indica entre 1 y 26 símbolos explícitos.")
    for symbol in symbols:
        workspace_key(symbol, "D1")

    results, errors = [], {}
    account = (settings["terminal"], settings["server"], settings["login"])
    for symbol in symbols:
        try:
            with connection(settings):
                info = checked(mt5.symbol_info(symbol), f"símbolo {symbol}")
                latest = checked(mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1),
                                 f"última vela D1 de {symbol}")
                if len(latest) == 0:
                    raise RuntimeError("No hay referencia D1 vigente en MT5.")
                latest_open = int(latest[0]["time"])
                at = latest_open if cutoff is None else cutoff
                if not 0 < at <= latest_open + 86400:
                    raise ValueError("El corte debe estar dentro del calendario disponible de MT5.")
                key = (account, symbol, at, latest_open, info.digits)
                result = HISTORY_CACHE.get(key)
                if result is None:
                    # A successor confirms closure without contributing OHLC.
                    lower = window_start(at) - timedelta(days=120)
                    upper = datetime.fromtimestamp(min(at + 8 * 86400, latest_open), timezone.utc)
                    rates = checked(mt5.copy_rates_range(symbol, mt5.TIMEFRAME_D1, lower, upper),
                                    f"historial D1 de {symbol}")
            if result is None:
                rows = [(int(row["time"]), *(float(row[k]) for k in ("open", "high", "low", "close")))
                        for row in rates]
                result = analyze_poi_history(symbol, rows, info.digits, at)
                zones = result["zones"]
                result["zone_count"] = len(zones)
                result["candidate_count"] = sum(zone["classification"] == "poi_candidate" for zone in zones)
                if result["has_history_before_window"]:
                    HISTORY_CACHE[key] = result
                    if len(HISTORY_CACHE) > HISTORY_CACHE_SIZE:
                        HISTORY_CACHE.popitem(last=False)
            else:
                HISTORY_CACHE.move_to_end(key)
            results.append({k: v for k, v in result.items() if k != "zones"} if summary else result)
        except (RuntimeError, ValueError) as exc:
            errors[symbol] = str(exc)
    return {"results": results, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbols", nargs="*", help="Símbolos exactos de MT5")
    parser.add_argument("--symbols-file", type=Path, help="Archivo de símbolos separados por espacios o líneas")
    parser.add_argument("--group", choices=SYMBOL_GROUPS, help="Lista de Forex o de índices de MT5")
    parser.add_argument("--summary", action="store_true", help="Totales de zonas sin devolver cada zona")
    parser.add_argument("--date", type=date_cutoff, help="Fecha final inclusiva de MT5 (AAAA-MM-DD)")
    args = parser.parse_args()
    symbols = args.symbols
    try:
        if args.symbols_file:
            symbols += args.symbols_file.read_text(encoding="utf-8-sig").split()
        if args.group and (args.symbols_file or symbols):
            parser.error("Usa --group o indica símbolos explícitos.")
        if not symbols and not args.symbols_file:
            symbols = SYMBOL_GROUPS[args.group or "forex"]
        result = scan_poi_history(config(), symbols, args.date, summary=args.summary)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
