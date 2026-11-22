"""Actualiza el panel por instrumento y marco mientras la vista está abierta."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from threading import Condition, Thread
from time import monotonic

from diario import MT5ConnectionError, config, workspace_key
from ict import BAR_COUNT, PROFILE, SECONDS, analyze_bars, read_bars
from sesiones import OpeningMonitor, mt5_offset
from motor_smc.instrumentos import ALERT_SYMBOLS, MT5_SYMBOLS, WATCH_SYMBOLS
from motor_smc.mt5_feed import closed_signature, read_daily_close, read_market_head, read_watch_heads

LOG = logging.getLogger(__name__)
POLL_SECONDS = 8
LEASE_SECONDS = 90
MAX_SCOPES = 6
DAILY_STEP_SECONDS = 25
WATCH_POLL_SECONDS = 35
WATCH_BATCH_SIZE = 5


@dataclass
class PanelScope:
    used_at: float
    due_at: float = 0
    signature: tuple = ()
    opening_signature: tuple = ()
    payload: dict = field(default_factory=dict)
    account: tuple = ()
    broker_clock: tuple = ()
    calendar_date: object = None


class MarketPanel:
    def __init__(self, settings=config, head=read_market_head, bars=read_bars, analysis=analyze_bars,
                 openings=None, clock=lambda: datetime.now(timezone.utc), daily=read_daily_close, notices=None,
                 watch_heads=read_watch_heads):
        self.settings = settings
        self.head = head
        self.bars = bars
        self.analysis = analysis
        self.openings = openings or OpeningMonitor().read
        self.clock = clock
        self.daily = daily
        self.notices = notices
        self.watch_heads = watch_heads
        self.watch_scopes = tuple((symbol, "M15") for symbol in WATCH_SYMBOLS) if notices is not None else ()
        self.scopes = {key: PanelScope(float("-inf")) for key in self.watch_scopes}
        self.universe_rows = {}
        self.universe_index = 0
        self.universe_account = ()
        self.next_daily_at = monotonic() + DAILY_STEP_SECONDS
        self.condition = Condition()
        self.stopping = False
        self.thread = Thread(target=self.run, name="smc-market-panel", daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        with self.condition:
            self.stopping = True
            self.condition.notify()
        self.thread.join(timeout=2)

    def read(self, symbol, frame):
        workspace_key(symbol, frame)
        if symbol not in MT5_SYMBOLS:
            raise ValueError("El motor admite únicamente los activos confirmados de MT5.")
        key = (symbol, frame)
        now = monotonic()
        with self.condition:
            scope = self.scopes.get(key)
            if scope is None:
                views = self.scopes.keys() - self.watch_scopes
                if len(views) >= MAX_SCOPES:
                    del self.scopes[min(views, key=lambda item: self.scopes[item].used_at)]
                scope = self.scopes[key] = PanelScope(now)
                self.condition.notify()
            elif now - scope.used_at >= LEASE_SECONDS:
                scope.due_at = now
                self.condition.notify()
            scope.used_at = now
            result = scope.payload.copy()
        if not result:
            return {"state": "loading", "symbol": symbol, "frame": frame}
        observation = result.get("last_success")
        interval = WATCH_POLL_SECONDS if key in self.watch_scopes else POLL_SECONDS
        if observation and (self.clock() - datetime.fromisoformat(observation)).total_seconds() > 3 * interval:
            result["state"] = "stale"
        return {"symbol": symbol, "frame": frame, **result}

    def universe(self):
        with self.condition:
            data = {"total": len(MT5_SYMBOLS), "assets": self.universe_rows.copy()}
            if self.watch_scopes:
                data["intraday"] = {symbol: self.watch_status(self.scopes[symbol, frame].payload)
                                    for symbol, frame in self.watch_scopes}
        return data

    def watch_status(self, payload):
        closed = payload.get("m15_closed")
        analyzed = payload.get("analysis", {}).get("asof")
        checked = payload.get("last_success")
        elapsed = (self.clock() - datetime.fromisoformat(checked)).total_seconds() if checked else None
        state = payload.get("state", "loading")
        if elapsed is not None and (elapsed > 3 * WATCH_POLL_SECONDS or closed != analyzed):
            state = "stale"
        return {"state": state, "closed": closed, "analyzed": analyzed, "checked_at": checked,
                "analysis_at": payload.get("analysis_at"), "errors": payload.get("errors", {})}

    def run(self):
        while True:
            with self.condition:
                if self.stopping:
                    return
                now = monotonic()
                self.scopes = {key: scope for key, scope in self.scopes.items()
                               if key in self.watch_scopes or now - scope.used_at < LEASE_SECONDS}
                queue = sorted(self.scopes.items(), key=lambda item: item[1].due_at)
                due = queue[0][1].due_at if queue else float("inf")
                scan_daily = self.next_daily_at <= now and (due > now or now - self.next_daily_at > 90)
                if not scan_daily and due > now:
                    self.condition.wait(timeout=min(due, self.next_daily_at) - now)
                    continue
                batch = []
                if not scan_daily:
                    key, scope = queue[0]
                    if key in self.watch_scopes and now - scope.used_at >= LEASE_SECONDS:
                        for candidate, pending in queue:
                            if (len(batch) >= WATCH_BATCH_SIZE or pending.due_at > now or
                                    candidate not in self.watch_scopes or now - pending.used_at < LEASE_SECONDS):
                                break
                            batch.append((candidate, pending))
            if scan_daily:
                self.refresh_universe()
                continue
            if batch:
                self.refresh_watch_batch(batch)
                continue
            payload = self.refresh(*key, scope)
            with self.condition:
                scope.payload = payload
                scope.due_at = monotonic() + POLL_SECONDS

    def refresh_watch_batch(self, batch):
        settings = None
        try:
            settings = self.settings()
            heads = self.watch_heads(settings, [key[0] for key, _ in batch])
        except (RuntimeError, ValueError, KeyError, OSError) as exc:
            heads = {key[0]: exc for key, _ in batch}
        for (symbol, frame), scope in batch:
            payload = self.refresh(symbol, frame, scope, probe=heads[symbol], settings=settings)
            with self.condition:
                scope.payload = payload
                scope.due_at = monotonic() + (POLL_SECONDS if monotonic() - scope.used_at < LEASE_SECONDS
                                              else WATCH_POLL_SECONDS)

    def refresh_universe(self):
        symbol = MT5_SYMBOLS[self.universe_index]
        with self.condition:
            result = self.universe_rows.get(symbol, {}).copy()
        try:
            settings = self.settings()
            identity = (settings["terminal"], settings["server"], settings["login"])
            if identity != self.universe_account:
                with self.condition:
                    self.universe_rows.clear()
                self.universe_account = identity
                result = {}
            result["last_closed"] = self.daily(settings, symbol)
            result["error"] = None
        except (RuntimeError, ValueError, KeyError, OSError) as exc:
            result["error"] = str(exc)
        with self.condition:
            self.universe_rows[symbol] = {**result, "checked_at": self.clock().isoformat()}
        self.universe_index = (self.universe_index + 1) % len(MT5_SYMBOLS)
        self.next_daily_at = monotonic() + DAILY_STEP_SECONDS

    def refresh(self, symbol, frame, scope, *, probe=None, settings=None):
        now = self.clock()
        result = {**scope.payload, "checked_at": now.isoformat()}
        errors = {}
        watch = (symbol, frame) in self.watch_scopes
        connection_probe = watch and symbol == "EURUSD"
        try:
            settings = self.settings() if settings is None else settings
            identity = (settings["terminal"], settings["server"], settings["login"])
            if identity != scope.account:
                scope.account = identity
                scope.signature = scope.opening_signature = ()
                scope.broker_clock = ()
                scope.calendar_date = None
                result = {"checked_at": now.isoformat()}
            if isinstance(probe, Exception):
                raise probe
            heads, last_tick, clock_tick = self.head(settings, symbol, frame) if probe is None else probe
        except Exception as exc:
            if isinstance(exc, MT5ConnectionError) and connection_probe and scope.account:
                self.notices.observe_connection(scope.account, False, now)
            if not isinstance(exc, (RuntimeError, OSError, ValueError)):
                LOG.exception("Error leyendo MT5 para %s/%s", symbol, frame)
            return {**result, "state": "stale" if result.get("chart") else "unavailable",
                    "errors": {"mt5": str(exc)}}
        if connection_probe:
            self.notices.observe_connection(scope.account, True, now)

        observed = mt5_offset(clock_tick, now) if clock_tick is not None else None
        if observed is not None:
            scope.broker_clock = (now.date(), observed)
        offset = scope.broker_clock[1] if scope.broker_clock and scope.broker_clock[0] == now.date() else None
        tick_age = int(now.timestamp()) + offset - last_tick if offset is not None and last_tick is not None else None
        result.update(last_success=now.isoformat(), last_tick_mt5=last_tick, quote_age=tick_age)
        previous, current = heads["M15"]
        result["m15_closed"] = min(previous[0] + SECONDS["M15"], current[0])
        signature = closed_signature(heads)
        daily_refresh = scope.calendar_date != now.date()
        if signature != tuple(item for item in scope.signature if item[0] in heads) or daily_refresh:
            try:
                source = self.bars(settings, symbol, tuple(dict.fromkeys((*PROFILE, frame))))
                digits, _, history, _ = source
                result["chart"] = {"digits": digits, "rows": history[frame][-BAR_COUNT:]}
                result["analysis"] = self.analysis(symbol, frame, source)
                completed = self.clock()
                result["analysis_at"] = completed.isoformat()
                scope.signature = closed_signature(history)
                scope.calendar_date = now.date()
                previous, current = history["M15"][-2:]
                result["m15_closed"] = min(previous[0] + SECONDS["M15"], current[0])
                if watch:
                    quote_age = tick_age + (completed - now).total_seconds() if tick_age is not None else None
                    self.notices.observe_analysis(scope.account, result["analysis"], completed, offset, quote_age)
            except Exception as exc:
                LOG.warning("Análisis de %s/%s pendiente: %s", symbol, frame, exc)
                errors["ict"] = str(exc)
        else:
            chart = result["chart"]
            # The closed signature matches, so only the forming candle changed.
            result["chart"] = {"digits": chart["digits"], "rows": (*chart["rows"][:-1], heads[frame][-1])}

        opening_key = (now.date(), heads["M15"][0], heads["M15"][1][0])
        if (probe is None or symbol in ALERT_SYMBOLS) and opening_key != scope.opening_signature:
            try:
                result["openings"] = self.openings(now, symbol)
                scope.opening_signature = opening_key
            except (RuntimeError, ValueError, OSError) as exc:
                errors["openings"] = str(exc)
        result["errors"] = errors
        quiet = last_tick is None or (tick_age if tick_age is not None else int(now.timestamp()) - last_tick) > 180
        result["state"] = "stale" if errors or quiet else "current"
        return result
