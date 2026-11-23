#!/usr/bin/env python3
"""Deterministic MT5 bar freshness / coverage collector.

Pure classifier + MT5 adapter + CLI.  See README.md for the JSON schema and
the documented freshness rules.  No account data is read or emitted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time as _time
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

UTC = dt.timezone.utc

SCHEMA_VERSION = "1.0"

# MT5 bar durations in seconds (MT5 timestamp space).
TIMEFRAME_SECONDS = {
    "D1": 86400,
    "H4": 14400,
    "H1": 3600,
    "M15": 900,
    "M5": 300,
    "M1": 60,
}
TIMEFRAME_ORDER = ("D1", "H4", "H1", "M15", "M5", "M1")

STATUSES = (
    "FRESH",
    "STALE_FEED",
    "MARKET_CLOSED",
    "PARTIAL_FEED",
    "ERROR",
    "SYMBOL_MISSING",
)

INTERPRETATIONS = ("compensate", "raw")
WEEKEND_DAYS = (5, 6)  # Monday=0 .. Sunday=6


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def iso_utc(epoch: Optional[int]) -> Optional[str]:
    """Render an epoch as a deterministic ISO-8601 UTC string."""
    if epoch is None:
        return None
    return dt.datetime.fromtimestamp(int(epoch), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_cutoff(value: str) -> int:
    """Accept an integer/float epoch or an ISO-8601 timestamp (real UTC)."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        pass
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp())


@dataclass(frozen=True)
class Bar:
    """One MT5 bar.  ``time`` is the bar OPEN in MT5 timestamp space."""

    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0
    spread: int = 0
    real_volume: int = 0


def _as_bar(row: Any) -> Bar:
    """Convert a mapping / Bar / structured row into a plain Bar."""
    if isinstance(row, Bar):
        return row
    if isinstance(row, Mapping):
        get = row.__getitem__
    else:
        get = row.__getitem__
    return Bar(
        time=int(get("time")),
        open=float(get("open")),
        high=float(get("high")),
        low=float(get("low")),
        close=float(get("close")),
        tick_volume=int(get("tick_volume")),
        spread=int(get("spread")),
        real_volume=int(get("real_volume")),
    )


def closed_frame(opened: int, period_seconds: int,
                 successor_open: Optional[int] = None) -> int:
    """Documented close rule (same as ict.closed_frame).

    ``closed = min(opened + period, successor_open)``.  With no successor the
    bar is assumed to have run its full period.
    """
    nominal = opened + period_seconds
    if successor_open is None:
        return nominal
    return min(nominal, int(successor_open))


def _weekday(epoch: int, weekend_days: Sequence[int]) -> bool:
    return dt.datetime.fromtimestamp(int(epoch), UTC).weekday() in set(weekend_days)


def _weekend_block_start(epoch: int, weekend_days: Sequence[int]) -> Optional[int]:
    """First 00:00 epoch of the contiguous weekend block containing ``epoch``."""
    days = set(weekend_days)
    day = dt.datetime.fromtimestamp(int(epoch), UTC).date()
    for back in range(7):
        candidate = day - dt.timedelta(days=back)
        if candidate.weekday() not in days:
            continue
        prev = candidate - dt.timedelta(days=1)
        if prev.weekday() in days:
            continue  # not the first day of the block
        midnight = dt.datetime(candidate.year, candidate.month, candidate.day,
                               tzinfo=UTC)
        return int(midnight.timestamp())
    return None


def _count_market_slots(lo: int, hi: int, period: int,
                        weekend_days: Sequence[int]) -> int:
    """Count period slot starts in [lo, hi] that fall on open-market days.

    Weekend days are excluded (a documented, configurable simplification: no
    public-holiday calendar is modelled).  ``period`` must divide 86400, which
    holds for every timeframe this module supports.
    """
    if hi < lo:
        return 0
    days = set(weekend_days)
    day_lo = lo // 86400
    day_hi = hi // 86400
    total = 0
    for day in range(day_lo, day_hi + 1):
        if dt.datetime.fromtimestamp(day * 86400, UTC).weekday() in days:
            continue
        day_start = day * 86400
        if period >= 86400:
            a, b = max(lo, day_start), min(hi, day_start + 86399)
            if a <= b:
                total += 1
            continue
        slots_per_day = 86400 // period
        first = max(0, -(-(max(lo, day_start) - day_start) // period))  # ceil
        last = min(slots_per_day - 1,
                   (min(hi, day_start + 86399) - day_start) // period)
        if last >= first:
            total += last - first + 1
    return total


def _empty_cell(symbol: str, timeframe: str, status: str, reason: str,
                *, period_seconds: Optional[int] = None,
                cutoff_epoch: Optional[int] = None,
                engine_cutoff_epoch: Optional[int] = None,
                offset_seconds: int = 0,
                interpretation: str = "compensate") -> dict:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "period_seconds": period_seconds,
        "bars_count": 0,
        "expected_bars_count": None,
        "missing_bars": None,
        "oldest_bar_open_utc": None,
        "oldest_bar_open_epoch": None,
        "last_bar_open_utc": None,
        "last_bar_open_epoch": None,
        "last_bar_close_utc": None,
        "last_bar_close_epoch": None,
        "expected_close_utc": None,
        "expected_close_epoch": None,
        "lag_periods": None,
        "freshness_status": status,
        "cutoff_epoch": cutoff_epoch,
        "engine_cutoff_epoch": engine_cutoff_epoch,
        "broker_clock_offset_seconds": offset_seconds,
        "clock_interpretation": interpretation,
        "reasons": [reason],
    }


# ---------------------------------------------------------------------------
# PURE CLASSIFIER (no MT5, no clock reads -- fully synthetic-testable)
# ---------------------------------------------------------------------------
def classify_series(
    bars: Sequence[Any],
    *,
    period_seconds: int,
    cutoff_epoch: int,
    broker_clock_offset_seconds: int = 0,
    interpretation: str = "compensate",
    weekend_days: Sequence[int] = WEEKEND_DAYS,
    symbol: str = "",
    timeframe: str = "",
    symbol_present: bool = True,
) -> dict:
    """Classify one (symbol, timeframe) bar series.

    ``cutoff_epoch`` is a REAL-UTC instant supplied by the caller.  Bars are
    MT5-timestamp-space opens.  In the default ``compensate`` interpretation
    the engine cutoff is ``cutoff_epoch + offset`` (MT5 space) and every
    ``*_utc`` output is ``mt5_epoch - offset`` (real UTC).  The ``raw``
    interpretation applies no offset; its ``*_utc`` values are MT5 clock
    values and are *not* real UTC (diagnostic mode only).
    """
    offset = int(broker_clock_offset_seconds)
    if interpretation not in INTERPRETATIONS:
        return _empty_cell(symbol, timeframe, "ERROR", "INVALID_INTERPRETATION",
                           period_seconds=period_seconds,
                           cutoff_epoch=cutoff_epoch,
                           engine_cutoff_epoch=None, offset_seconds=offset,
                           interpretation=interpretation)
    if not symbol_present:
        return _empty_cell(symbol, timeframe, "SYMBOL_MISSING", "SYMBOL_NOT_FOUND",
                           period_seconds=period_seconds,
                           cutoff_epoch=cutoff_epoch, offset_seconds=offset,
                           interpretation=interpretation)

    effective_offset = offset if interpretation == "compensate" else 0
    engine_cutoff = int(cutoff_epoch) + effective_offset

    def to_utc(mt5_epoch: int) -> int:
        return int(mt5_epoch) - effective_offset

    if period_seconds <= 0 or period_seconds > 86400 or 86400 % period_seconds != 0:
        return _empty_cell(symbol, timeframe, "ERROR", "INVALID_PERIOD",
                           period_seconds=period_seconds, cutoff_epoch=cutoff_epoch,
                           engine_cutoff_epoch=engine_cutoff,
                           offset_seconds=offset, interpretation=interpretation)

    reasons: list[str] = []
    try:
        parsed = [_as_bar(row) for row in bars]
    except Exception:
        return _empty_cell(symbol, timeframe, "ERROR", "INVALID_BAR_ROW",
                           period_seconds=period_seconds, cutoff_epoch=cutoff_epoch,
                           engine_cutoff_epoch=engine_cutoff,
                           offset_seconds=offset, interpretation=interpretation)

    if not parsed:
        return _empty_cell(symbol, timeframe, "ERROR", "NO_BARS_RETURNED",
                           period_seconds=period_seconds, cutoff_epoch=cutoff_epoch,
                           engine_cutoff_epoch=engine_cutoff,
                           offset_seconds=offset, interpretation=interpretation)

    # Detect ordering anomalies on the ORIGINAL feed order before sorting.
    if any(parsed[i].time > parsed[i + 1].time for i in range(len(parsed) - 1)):
        reasons.append("NON_MONOTONIC_ROWS_SORTED")
    ordered = sorted(parsed, key=lambda bar: bar.time)
    deduped: list[Bar] = []
    duplicate_found = False
    for bar in ordered:
        if deduped and deduped[-1].time == bar.time:
            duplicate_found = True
            continue
        deduped.append(bar)
    if duplicate_found:
        reasons.append("DUPLICATE_BAR_TIMES")
    opens = [bar.time for bar in deduped]

    frames: list[tuple[int, int]] = []
    for idx, bar in enumerate(deduped):
        successor = opens[idx + 1] if idx + 1 < len(opens) else None
        frames.append((bar.time, closed_frame(bar.time, period_seconds, successor)))

    selected = [(op, cl) for op, cl in frames if cl <= engine_cutoff]
    if len(selected) != len(frames):
        reasons.append("UNFORMED_BARS_EXCLUDED")
    if not selected:
        cell = _empty_cell(symbol, timeframe, "ERROR",
                           "NO_CLOSED_BARS_AT_OR_BEFORE_CUTOFF",
                           period_seconds=period_seconds, cutoff_epoch=cutoff_epoch,
                           engine_cutoff_epoch=engine_cutoff,
                           offset_seconds=offset, interpretation=interpretation)
        cell["reasons"] = reasons + cell["reasons"]
        cell["bars_count"] = len(selected)
        return cell

    oldest_open_mt5 = selected[0][0]
    last_open_mt5, last_close_mt5 = selected[-1]
    expected_close_mt5 = (engine_cutoff // period_seconds) * period_seconds

    expected_count = _count_market_slots(oldest_open_mt5, last_open_mt5,
                                         period_seconds, weekend_days)
    missing = max(0, expected_count - len(selected))
    if missing:
        reasons.append("MISSING_BARS:%d" % missing)

    if expected_close_mt5 > last_close_mt5:
        lag = _count_market_slots(last_close_mt5,
                                  expected_close_mt5 - period_seconds,
                                  period_seconds, weekend_days)
    else:
        lag = 0

    weekend_closed = False
    if _weekday(engine_cutoff, weekend_days):
        weekend_start = _weekend_block_start(engine_cutoff, weekend_days)
        if weekend_start is not None and last_close_mt5 == weekend_start:
            weekend_closed = True
            reasons.append("WEEKEND_NO_NEW_CLOSED_BARS")
        elif weekend_start is not None and last_close_mt5 < weekend_start:
            reasons.append("WEEKEND_BUT_FEED_STALE_BEFORE_WEEKEND")
        else:
            reasons.append("WEEKEND_BARS_PRESENT")

    if missing or "NON_MONOTONIC_ROWS_SORTED" in reasons or "DUPLICATE_BAR_TIMES" in reasons:
        status = "PARTIAL_FEED"
    elif weekend_closed:
        status = "MARKET_CLOSED"
    elif lag > 0:
        reasons.append("STALE_BY_%d_PERIODS" % lag)
        status = "STALE_FEED"
    else:
        status = "FRESH"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "period_seconds": int(period_seconds),
        "bars_count": len(selected),
        "expected_bars_count": expected_count,
        "missing_bars": missing,
        "oldest_bar_open_utc": iso_utc(to_utc(oldest_open_mt5)),
        "oldest_bar_open_epoch": to_utc(oldest_open_mt5),
        "last_bar_open_utc": iso_utc(to_utc(last_open_mt5)),
        "last_bar_open_epoch": to_utc(last_open_mt5),
        "last_bar_close_utc": iso_utc(to_utc(last_close_mt5)),
        "last_bar_close_epoch": to_utc(last_close_mt5),
        "expected_close_utc": iso_utc(to_utc(expected_close_mt5)),
        "expected_close_epoch": to_utc(expected_close_mt5),
        "lag_periods": lag,
        "freshness_status": status,
        "cutoff_epoch": int(cutoff_epoch),
        "engine_cutoff_epoch": engine_cutoff,
        "broker_clock_offset_seconds": offset,
        "clock_interpretation": interpretation,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# MT5 adapter
# ---------------------------------------------------------------------------
def connect_mt5():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("mt5.initialize failed: %r" % (mt5.last_error(),))
    return mt5


def mt5_timeframe(mt5, name: str):
    return getattr(mt5, "TIMEFRAME_" + name)


def measure_broker_clock(mt5, symbols: Sequence[str],
                         snap_seconds: int = 3600) -> dict:
    """Broker clock offset = MT5 last-tick time - system UTC, in seconds.

    The largest last-tick time among the requested symbols is used as the best
    available estimate of the broker's current clock.  A last tick is a quote
    from slightly in the past, so the raw estimate is a few seconds low.
    ``snap_seconds`` (default 3600 = whole hours, the usual MT5 broker grid)
    rounds it to the nearest documented grid point.  Both values are returned;
    nothing is hidden.  No account data is used.
    """
    system_now = int(round(_time.time()))
    best: Optional[int] = None
    reference = None
    usable = 0
    for symbol in symbols:
        try:
            tick = mt5.symbol_info_tick(symbol)
        except Exception:
            tick = None
        if tick is None or not getattr(tick, "time", 0):
            continue
        usable += 1
        stamp = int(tick.time)
        if best is None or stamp > best:
            best, reference = stamp, symbol
    if best is None:
        return {
            "source": "unavailable",
            "system_utc_epoch": system_now,
            "broker_clock_epoch": None,
            "offset_seconds_raw": 0,
            "offset_seconds": 0,
            "snap_seconds": int(snap_seconds),
            "symbols_used": 0,
            "reference_symbol": None,
            "override_applied": False,
        }
    raw_offset = best - system_now
    snapped = (int(round(raw_offset / snap_seconds) * snap_seconds)
               if snap_seconds and snap_seconds > 0 else int(raw_offset))
    return {
        "source": "max_last_tick_time",
        "system_utc_epoch": system_now,
        "broker_clock_epoch": best,
        "offset_seconds_raw": int(raw_offset),
        "offset_seconds": snapped,
        "snap_seconds": int(snap_seconds),
        "symbols_used": usable,
        "reference_symbol": reference,
        "override_applied": False,
    }


def _rows_from_rates(raw) -> list[dict]:
    keys = ("time", "open", "high", "low", "close",
            "tick_volume", "spread", "real_volume")
    return [{key: row[key] for key in keys} for row in raw]


def build_report(mt5, cutoff_epoch: int, symbols: Sequence[str], *,
                 max_bars: int = 10000,
                 interpretation: str = "compensate",
                 clock_offset_override: Optional[int] = None,
                 clock_source: str = "ticks",
                 clock_snap_seconds: int = 3600,
                 weekend_days: Sequence[int] = WEEKEND_DAYS) -> dict:
    symbols = sorted(set(symbols))
    if clock_source == "ticks":
        clock = measure_broker_clock(mt5, symbols, clock_snap_seconds)
    else:
        clock = {
            "source": "disabled",
            "system_utc_epoch": int(round(_time.time())),
            "broker_clock_epoch": None,
            "offset_seconds_raw": 0,
            "offset_seconds": 0,
            "snap_seconds": int(clock_snap_seconds),
            "symbols_used": 0,
            "reference_symbol": None,
            "override_applied": False,
        }
    if clock_offset_override is not None:
        clock = dict(clock)
        clock["offset_seconds"] = int(clock_offset_override)
        clock["override_applied"] = True
    offset = int(clock_offset_override) if clock_offset_override is not None \
        else int(clock["offset_seconds"])
    effective_offset = offset if interpretation == "compensate" else 0
    engine_cutoff = int(cutoff_epoch) + effective_offset

    results: dict[str, dict] = {}
    for symbol in symbols:
        info = mt5.symbol_info(symbol)
        present = info is not None
        if present:
            mt5.symbol_select(symbol, True)
        cells: dict[str, dict] = {}
        for timeframe in TIMEFRAME_ORDER:
            if not present:
                cells[timeframe] = _empty_cell(
                    symbol, timeframe, "SYMBOL_MISSING", "SYMBOL_NOT_FOUND",
                    period_seconds=TIMEFRAME_SECONDS[timeframe],
                    cutoff_epoch=cutoff_epoch, engine_cutoff_epoch=engine_cutoff,
                    offset_seconds=offset, interpretation=interpretation)
                continue
            try:
                raw = mt5.copy_rates_from_pos(symbol, mt5_timeframe(mt5, timeframe),
                                              0, int(max_bars))
                if raw is None:
                    cell = _empty_cell(
                        symbol, timeframe, "ERROR", "MT5_COPY_RATES_FAILED",
                        period_seconds=TIMEFRAME_SECONDS[timeframe],
                        cutoff_epoch=cutoff_epoch,
                        engine_cutoff_epoch=engine_cutoff,
                        offset_seconds=offset, interpretation=interpretation)
                else:
                    cell = classify_series(
                        _rows_from_rates(raw),
                        period_seconds=TIMEFRAME_SECONDS[timeframe],
                        cutoff_epoch=cutoff_epoch,
                        broker_clock_offset_seconds=offset,
                        interpretation=interpretation,
                        weekend_days=weekend_days,
                        symbol=symbol, timeframe=timeframe,
                        symbol_present=True)
            except Exception as exc:
                cell = _empty_cell(
                    symbol, timeframe, "ERROR",
                    "MT5_EXCEPTION:%s" % type(exc).__name__,
                    period_seconds=TIMEFRAME_SECONDS[timeframe],
                    cutoff_epoch=cutoff_epoch, engine_cutoff_epoch=engine_cutoff,
                    offset_seconds=offset, interpretation=interpretation)
            cells[timeframe] = cell
        results[symbol] = cells

    summary = {status: 0 for status in STATUSES}
    for cells in results.values():
        for cell in cells.values():
            summary[cell["freshness_status"]] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "cutoff_epoch": int(cutoff_epoch),
        "cutoff_utc": iso_utc(cutoff_epoch),
        "engine_cutoff_epoch": engine_cutoff,
        "engine_cutoff_utc": iso_utc(engine_cutoff),
        "broker_clock_offset_seconds": offset,
        "broker_clock": clock,
        "clock_interpretation": interpretation,
        "weekend_days": list(weekend_days),
        "timeframes": list(TIMEFRAME_ORDER),
        "max_bars": int(max_bars),
        "summary": summary,
        "results": results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect MT5 bar freshness/coverage as deterministic JSON.")
    parser.add_argument("--cutoff", required=True,
                        help="real-UTC evaluation instant: epoch seconds or ISO-8601")
    parser.add_argument("--symbols", default="",
                        help="comma-separated symbols; empty = all terminal symbols")
    parser.add_argument("--max-bars", type=int, default=10000,
                        help="bars requested per timeframe (default 10000)")
    parser.add_argument("--clock-offset-seconds", type=int, default=None,
                        help="override measured broker clock offset (seconds)")
    parser.add_argument("--interpretation", choices=INTERPRETATIONS,
                        default="compensate",
                        help="compensate (default, *_utc = real UTC) or raw")
    parser.add_argument("--clock-source", choices=("ticks", "none"), default="ticks",
                        help="measure offset from last tick times, or disable")
    parser.add_argument("--clock-snap-seconds", type=int, default=3600,
                        help="snap tick-derived offset to nearest N seconds "
                             "(default 3600 = whole hours; 0 disables)")
    parser.add_argument("--weekend-days", default="5,6",
                        help="closed-market weekdays, Monday=0 (default 5,6)")
    parser.add_argument("--output", default="",
                        help="write JSON here instead of stdout")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cutoff_epoch = parse_cutoff(args.cutoff)
    weekend_days = tuple(int(x) for x in args.weekend_days.split(",") if x.strip())

    mt5 = connect_mt5()
    try:
        if args.symbols.strip():
            symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        else:
            found = mt5.symbols_get()
            symbols = [s.name for s in (found or [])]
        report = build_report(
            mt5, cutoff_epoch, symbols,
            max_bars=args.max_bars,
            interpretation=args.interpretation,
            clock_offset_override=args.clock_offset_seconds,
            clock_source=args.clock_source,
            clock_snap_seconds=args.clock_snap_seconds,
            weekend_days=weekend_days)
    finally:
        mt5.shutdown()

    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
