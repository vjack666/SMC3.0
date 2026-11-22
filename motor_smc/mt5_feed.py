"""Lecturas pequeñas para detectar velas cerradas nuevas."""

import MetaTrader5 as mt5

from diario import FRAMES, checked, connection
from ict import PROFILE


def read_daily_close(settings, symbol):
    with connection(settings):
        rows = checked(mt5.copy_rates_from_pos(symbol, FRAMES["D1"], 0, 2), f"últimas D1 de {symbol}")
        if len(rows) != 2:
            raise RuntimeError(f"MT5 no confirmó la última D1 de {symbol}.")
        return min(int(rows[0]["time"]) + 86400, int(rows[1]["time"]))


def read_market_head(settings, symbol, frame):
    timeframes = tuple(dict.fromkeys((*PROFILE, frame)))
    bars = {}
    with connection(settings):
        for tf in timeframes:
            bars[tf] = read_head_bars(symbol, tf)
        tick = mt5.symbol_info_tick(symbol)
        clock = mt5.symbol_info_tick("EURUSD") if symbol != "EURUSD" else tick
    return bars, int(tick.time) if tick else None, int(clock.time) if clock else None


def read_head_bars(symbol, frame):
    rates = checked(mt5.copy_rates_from_pos(symbol, FRAMES[frame], 0, 2), f"últimas velas {symbol} {frame}")
    if len(rates) != 2:
        raise RuntimeError(f"MT5 no confirmó la última vela cerrada de {symbol} en {frame}.")
    return tuple((int(row["time"]), *(float(row[k]) for k in ("open", "high", "low", "close")))
                 for row in rates)


def read_watch_heads(settings, symbols):
    observed = {}
    with connection(settings):
        clock = mt5.symbol_info_tick("EURUSD")
        for symbol in symbols:
            try:
                bars = read_head_bars(symbol, "M15")
                tick = mt5.symbol_info_tick(symbol)
                observed[symbol] = ({"M15": bars}, int(tick.time) if tick else None,
                                    int(clock.time) if clock else None)
            except (RuntimeError, OSError, ValueError) as exc:
                observed[symbol] = exc
    return observed


def closed_signature(bars):
    """The live candle contributes its opening time only."""
    return tuple((tf, rows[-2], rows[-1][0]) for tf, rows in bars.items())
