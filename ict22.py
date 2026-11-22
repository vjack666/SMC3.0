"""Closed-M15 observations for Book 22. Produces chart annotations only."""
from bisect import bisect_left
from collections import defaultdict
from math import ceil, floor


M15 = 900
WINDOW = 8


def pivots(bars, field, direction):
    values = [getattr(bar, field) for bar in bars]
    return [i for i in range(2, len(bars) - 2)
            if all(direction * (values[i] - values[j]) > 0
                   for j in (i - 2, i - 1, i + 1, i + 2))]


def atr_before(bars, i):
    return sum(max(bar.high - bar.low, abs(bar.high - bars[j - 1].close),
                   abs(bar.low - bars[j - 1].close))
               for j, bar in enumerate(bars[i - 14:i], start=i - 14)) / 14


class Session:
    def __init__(self, source, opened, start, end, complete):
        self.source_open = source[0]
        self.pdh, self.pdl, self.previous_close = source[2:5]
        self.opened, self.start, self.end, self.complete = opened, start, end, complete

    def triggers(self, bars, classify, digits):
        previous = self.previous_close
        outside = 0
        streak = 0
        for i in range(self.start, self.end):
            bar = bars[i]
            event = classify(bar.open, bar.high, bar.low, bar.close, previous,
                             self.pdh, self.pdl, digits=digits)
            if event and event["kind"] == "sweep":
                yield i, i, "sweep", 1 if event["level"] == "PDH" else -1
            side = 1 if bar.close > self.pdh else -1 if bar.close < self.pdl else 0
            adjacent = i > self.start and bar.opened == bars[i - 1].opened + M15
            streak = 0 if not side else streak + 1 if side == outside and adjacent else 1
            if streak == 2:
                yield i, i - 1, "continuation", side
            outside, previous = side, bar.close


class Observer:
    def __init__(self, m15, objects, displacement, digits, tick, spreads):
        self.bars = list(m15.itertuples(index=False))
        self.digits, self.tick, self.spreads = digits, tick, spreads
        self.swings = {1: pivots(self.bars, "high", 1), -1: pivots(self.bars, "low", -1)}
        flags = displacement(m15)
        self.zones = defaultdict(list)
        for zone in objects:
            leg = zone.meta.get("middle_bar", zone.confirmation_bar)
            field = "displacement_bullish" if zone.direction == 1 else "displacement_bearish"
            if flags[field].iat[leg]:
                self.zones[zone.confirmation_bar, zone.direction].append((zone, leg))

    def broken(self, direction, price, level):
        return direction * (price - level) > self.tick / 2

    def extreme(self, i, direction):
        bar = self.bars[i]
        return bar.high if direction == 1 else bar.low

    def target(self, session, retest, direction, entry):
        bars = self.bars
        field = "high" if direction == 1 else "low"
        candidates = [(self.extreme(i, direction), i + 1, "Swing M15")
                      for i in self.swings[direction] if retest - 96 <= i <= retest - 2]
        daily_level, name = (session.pdh, "PDH") if direction == 1 else (session.pdl, "PDL")
        candidates.append((daily_level, session.start, name))
        ahead = [(level, name) for level, start, name in candidates
                 if self.broken(direction, level, entry)
                 and all(self.broken(direction, level, getattr(bar, field))
                         for bar in bars[start:retest + 1])]
        return min(ahead, key=lambda item: direction * item[0], default=(None, None))

    def monitor(self, session, signal, first, model, side, bias):
        bars = self.bars
        bar = bars[signal]
        sweep = model == "sweep"
        direction = -side if sweep else side
        level_name, level = ("PDH", session.pdh) if side == 1 else ("PDL", session.pdl)
        h4_side = {"BULLISH": 1, "BEARISH": -1}.get(bias, 0)
        alignment = "counter" if h4_side == -direction else "aligned" if h4_side == direction else "range"
        if sweep:
            model = "turtle_soup" if alignment == "counter" else "reversal"
        setup = {"id": f"{bar.opened}-{model}-{level_name}", "model": model, "side": level_name,
                 "direction": direction, "alignment": alignment, "level": level,
                 "h4_bias": bias, "source_d1": session.source_open, "tick_size": self.tick,
                 "first_open": bars[first].opened, "signal_open": bar.opened, "signal_close": bar.closed}

        def finish(reason, i, status="discarded"):
            return setup | {"status": status, "reason": reason, "evaluated": bars[i].closed}

        swing_side = direction if sweep else -direction
        swings = [i for i in self.swings[swing_side] if first - 16 <= i and i + 2 < first]
        if not sweep and not swings:
            return finish("no_stop_structure", signal)
        pivot = self.extreme(swings[-1], swing_side) if swings else None
        anchor = self.extreme(first, side) if sweep else pivot
        setup.update(stop_anchor=anchor, stop_basis="sweep_wick" if sweep else "m15_swing")
        if not sweep and any(self.broken(-direction, self.extreme(i, -direction), anchor)
                             for i in range(swings[-1] + 1, signal + 1)):
            return finish("broken_stop_structure", signal)

        stop = None
        if first >= 15:
            raw = (anchor - direction * .3 * atr_before(bars, first)) / self.tick
            tick_index = min(floor(raw), ceil(anchor / self.tick) - 1) if direction == 1 else (
                max(ceil(raw), floor(anchor / self.tick) + 1))
            stop = round(tick_index * self.tick, self.digits)
            setup["sl"] = stop
        if sweep and pivot is None:
            return finish("no_mss_pivot", signal)
        if stop is None:
            return finish("insufficient_history", signal)

        def holds(price):
            return session.pdl < price < session.pdh if sweep else self.broken(side, price, level)

        def interrupted(i):
            candle = bars[i]
            if candle.opened != bars[i - 1].opened + M15:
                return "gap"
            stop_quote = candle.low if direction == 1 else candle.high + self.spreads.get(candle.opened, 0)
            if direction * (stop_quote - stop) <= 0:
                return "stop_hit"
            if not holds(candle.close):
                return "range_lost" if sweep else "break_lost"
            return None

        zone_seen = False
        active = []
        for i in range(signal, min(session.end, signal + 2 * WINDOW + 1)):
            if i > signal and (reason := interrupted(i)):
                return finish(reason, i)
            # Retests only begin after the zone's confirmation candle.
            active = [(zone, confirmation, leg) for zone, confirmation, leg in active if i - confirmation <= WINDOW]
            candle = bars[i]
            for zone, confirmation, leg in active:
                mid = (zone.zone_low + zone.zone_high) / 2
                if candle.low <= mid <= candle.high and self.broken(direction, candle.close, mid):
                    setup.update(zone=zone.type.value, zone_low=zone.zone_low, zone_high=zone.zone_high,
                                 confirmation=bars[confirmation].closed, displacement_close=bars[leg].closed,
                                 retest=candle.closed, retest_level=mid)
                    if i + 1 == session.end:
                        return finish("session_ended" if session.complete else "await_reference", i,
                                      "discarded" if session.complete else "waiting")
                    reference = bars[i + 1]
                    if reference.opened != candle.opened + M15 or not holds(reference.open):
                        return finish("reference_invalid", i + 1)
                    spread = self.spreads.get(candle.opened, 0)
                    entry = round(reference.open + (spread if direction == 1 else 0), self.digits)
                    risk = direction * (entry - stop)
                    setup.update(reference_open=reference.opened, entry=entry,
                                 reference_spread=self.spreads.get(candle.opened))
                    if risk <= 0:
                        return finish("invalid_risk", i + 1)
                    tp, target_name = self.target(session, i, direction, entry)
                    if tp is None:
                        return finish("no_target", i + 1)
                    ratio = direction * (tp - entry) / risk
                    setup.update(tp=tp, target=target_name, rr=ratio)
                    if ratio < 3 - 1e-9:
                        return finish("below_rr", i + 1)
                    if ratio > 5 + 1e-9:
                        return finish("above_rr", i + 1)
                    return finish("in_range", i + 1, "qualified")
            if i <= signal + WINDOW:
                for zone, leg in self.zones[i, direction]:
                    if sweep:
                        valid = (leg > signal and self.broken(direction, bars[leg].close, pivot)
                                 and not self.broken(direction, bars[leg - 1].close, pivot))
                    else:
                        valid = leg >= first and holds(bars[leg].close)
                    if valid:
                        active.append((zone, i, leg))
                        zone_seen = True
                        if "confirmation" not in setup:
                            setup.update(confirmation=bars[i].closed, displacement_close=bars[leg].closed,
                                         zone=zone.type.value,
                                         zone_low=zone.zone_low, zone_high=zone.zone_high)
            if i >= signal + WINDOW and not any(i < confirmation + WINDOW for _, confirmation, _ in active):
                break
        end = i
        if not zone_seen:
            reason = "no_mss_zone" if sweep else "no_displacement_zone"
            expiring = i >= signal + WINDOW or session.complete
        else:
            reason = "no_retest"
            expiring = session.complete or not active or i >= active[-1][1] + WINDOW
        return finish(reason, end, "discarded" if expiring else "waiting")


def book22_setups(daily_rows, m15, asof, objects, *, classify, displacement, h4_bias, digits, tick, spreads):
    observer = Observer(m15, objects, displacement, digits, tick, spreads)
    opens = [bar.opened for bar in observer.bars]
    setups = []
    for j, day in enumerate(daily_rows[1:], start=1):
        if day[0] < opens[0] or day[0] > asof:
            continue
        next_open = daily_rows[j + 1][0] if j + 1 < len(daily_rows) else None
        complete = next_open is not None and next_open <= asof
        left = bisect_left(opens, day[0])
        right = bisect_left(opens, next_open) if complete else len(opens)
        source = daily_rows[j - 1]
        if source[2] <= source[3]:
            continue
        session = Session(source, day[0], left, right, complete)
        for signal, first, model, side in session.triggers(observer.bars, classify, digits):
            bias = h4_bias(observer.bars[signal].time)
            result = observer.monitor(session, signal, first, model, side, bias)
            setups.append(result | {"session_open": session.opened})
    return setups
