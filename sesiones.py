"""First-M15 ranges for the London and New York FX opens."""
from datetime import datetime, time, timedelta, timezone
import logging
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5

from diario import DATA, FRAMES, checked, config, connection, mt5_time, read_json, save_json
from ict import EURUSD_DIGITS, SYMBOL, classify_range_bar, previous_daily
from motor_smc.instrumentos import ALERT_SYMBOLS, MT5_SYMBOLS

LONDON = ZoneInfo("Europe/London")
NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")
BAR = 15 * 60
POLL_SECONDS = 8
ALERT_WINDOW = 240
ALERT_EVENTS = {"sweep": "Barrido", "break": "Ruptura"}

LOG = logging.getLogger(__name__)


def opening_schedule(day):
    london = datetime.combine(day, time(8), LONDON).astimezone(timezone.utc)
    new_york = datetime.combine(day, time(8), NEW_YORK).astimezone(timezone.utc)
    asia = datetime.combine(day, time(9), TOKYO).astimezone(timezone.utc)
    return (
        ("Londres", "Asia", asia, london),
        ("Nueva York", "Londres", london, new_york),
    )


def matches_season(day, today):
    return all(datetime.combine(day, time(12), zone).utcoffset()
               == datetime.combine(today, time(12), zone).utcoffset()
               for zone in (LONDON, NEW_YORK))


def utc_seconds(dt):
    return int(dt.timestamp())


def mt5_offset(tick_time, now):
    seconds = tick_time - utc_seconds(now)
    offset = round(seconds / 3600) * 3600
    return offset if offset in (0, 7200, 10800) and abs(seconds - offset) <= 120 else None


def candle_rows(settings, symbol):
    with connection(settings):
        info = checked(mt5.symbol_info(symbol), f"símbolo {symbol}")
        frames = {
            tf: [(int(row["time"]), *[float(row[k]) for k in ("open", "high", "low", "close")])
                 for row in checked(mt5.copy_rates_from_pos(symbol, FRAMES[tf], 0, count), f"velas {symbol} {tf}")]
            for tf, count in (("D1", 12), ("M15", 550))
        }
        frames["digits"] = info.digits
        # All symbols use the same verified broker clock.
        tick = mt5.symbol_info_tick(SYMBOL)
    return frames, int(tick.time) if tick else None


def classify(candle, previous_close, high, low, label, upper, lower, *, digits):
    if high <= low:
        return {"name": label, "high": high, "low": low, "event": None, "available": False}
    event = classify_range_bar(*candle[1:], previous_close, high, low, digits=digits)
    if event:
        event = {**event, "level": {"PDH": upper, "PDL": lower}.get(event["level"]),
                 "close_side": {"PDH": upper, "PDL": lower}.get(event["close_side"])}
    return {"name": label, "high": round(high, digits), "low": round(low, digits),
            "event": event, "available": True}


def range_events(by_time, opening, now, offset, digits):
    """Check each later close against the frozen opening range."""
    events = []
    for opened in range(opening["open"] + BAR, opening["session_end"], BAR):
        close_utc = opened + BAR - offset
        if close_utc > utc_seconds(now):
            break
        candle, previous = by_time.get(opened), by_time.get(opened - BAR)
        if candle is None or previous is None or opening["high"] <= opening["low"]:
            continue
        event = classify_range_bar(*candle[1:], previous[4], opening["high"],
                                   opening["low"], digits=digits)
        if event and event["kind"] in ALERT_EVENTS:
            side = "high" if event["level"] == "PDH" else "low"
            events.append({"open": opened, "close_utc": close_utc, "kind": event["kind"],
                           "side": side, "level": opening[side], "wick": event[side],
                           "close": event["close"]})
    return events


def assess_openings(day, now, offset, frames):
    """Read the exact opening candle plus its successor; ignore position zero."""
    m15 = frames["M15"]
    digits = frames.get("digits", EURUSD_DIGITS)
    by_time = {row[0]: row for row in m15[:-1]}
    results = []
    for name, ref_name, range_from, utc_open in opening_schedule(day):
        close_utc = utc_seconds(utc_open) + BAR
        opened = utc_seconds(utc_open) + offset
        result = {
            "id": f"{day.isoformat()}/{name}",
            "name": name, "session_date": day.isoformat(), "open": opened,
            "session_end": (opened // 86400 + 1) * 86400,
            "close_utc": close_utc, "status": "upcoming", "references": [], "events": [],
        }
        results.append(result)
        if utc_seconds(now) < utc_seconds(utc_open):
            continue
        if utc_seconds(now) < close_utc or not m15 or m15[-1][0] < opened + BAR:
            result["status"] = "waiting_close"
            continue
        candle = by_time.get(opened)
        if candle is None:
            result["status"] = "missing"
            continue
        result.update(status="closed", high=candle[2], low=candle[3], close=candle[4])
        result["events"] = range_events(by_time, result, now, offset, digits)
        prior_bar = by_time.get(opened - BAR)
        if prior_bar is None:
            result["status"] = "missing_context"
            continue
        previous_close = prior_bar[4]
        dates = previous_daily(frames["D1"], opened)
        if dates:
            prior_day = dates[0]
            result["references"].append(classify(candle, previous_close, prior_day[2],
                                                  prior_day[3], "D1 previa", "PDH", "PDL", digits=digits))
        expected = range(utc_seconds(range_from) + offset, opened, BAR)
        context = [by_time.get(at) for at in expected]
        if context and all(row is not None for row in context):
            high, low = max(row[2] for row in context), min(row[3] for row in context)
            result["references"].append(classify(candle, previous_close, high, low,
                                                  ref_name, f"máximo de {ref_name}", f"mínimo de {ref_name}",
                                                  digits=digits))
        # The signal can span both reference ranges. The notification is still unique.
        result["alerts"] = [
            f"{ALERT_EVENTS[ref['event']['kind']]} de {ref['event']['level']}"
            for ref in result["references"]
            if ref["event"] and ref["event"]["kind"] in ALERT_EVENTS
        ]
    return results


def notify_windows(title, message):
    # Pass content through environment variables, not through command interpolation.
    script = """
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$icon = [System.Windows.Forms.NotifyIcon]::new()
try {
  $icon.Icon = [System.Drawing.SystemIcons]::Information
  $icon.Text = 'SMC 3.0'
  $icon.Visible = $true
  $icon.ShowBalloonTip(8000, $env:SMC_NOTICE_TITLE, $env:SMC_NOTICE_TEXT, [System.Windows.Forms.ToolTipIcon]::Info)
  $timer = [System.Diagnostics.Stopwatch]::StartNew()
  while ($timer.ElapsedMilliseconds -lt 9000) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 125
  }
} finally {
  $icon.Dispose()
}
"""
    shell = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.Popen([str(shell), "-NoProfile", "-STA", "-NonInteractive", "-Command", script],
                     env={**os.environ, "SMC_NOTICE_TITLE": title, "SMC_NOTICE_TEXT": message},
                     creationflags=subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class OpeningMonitor:
    def __init__(self, data_reader=candle_rows, notifier=notify_windows, path=None):
        self.data_reader = data_reader
        self.notifier = notifier
        self.path = path or DATA / "avisos-apertura.json"
        self.completed = set()
        self.snapshots = {}
        self.last_attempt = None
        self.processed_ranges = {}
        self.verified_offset = None

    def read(self, now, symbol=SYMBOL):
        if symbol not in MT5_SYMBOLS:
            raise ValueError("Símbolo fuera del universo MT5 de rangos de apertura.")
        cached = self.snapshots.get(symbol)
        if cached and cached[0].date() == now.date() and 0 <= (now - cached[0]).total_seconds() < POLL_SECONDS:
            return cached[1]
        frames, tick = self.data_reader(config(), symbol)
        observed = mt5_offset(tick, now) if tick is not None else None
        if observed is not None:
            self.verified_offset = (now.date(), observed)
        if not self.verified_offset or self.verified_offset[0] != now.date():
            raise RuntimeError("Esperando una cotización reciente de EURUSD para comprobar la hora de MT5.")
        offset = self.verified_offset[1]
        latest = []
        for days_ago in range(3, -1, -1):
            day = now.date() - timedelta(days=days_ago)
            if day.weekday() < 5 and matches_season(day, now.date()):
                latest.extend(assess_openings(day, now, offset, frames))
        m15 = frames["M15"]
        last_closed = m15[-2][0] + BAR - offset if len(m15) > 1 else None
        snapshot = {"symbol": symbol, "today": now.date().isoformat(), "checks": latest,
                    "last_closed_utc": last_closed}
        self.snapshots[symbol] = (now, snapshot)
        return snapshot

    def poll(self, now):
        if now.weekday() >= 5:
            return
        cutoffs = [(f"{now.date().isoformat()}/{name}", opening + timedelta(seconds=BAR))
                   for name, _, _, opening in opening_schedule(now.date())]
        due = {key for key, close in cutoffs
               if key not in self.completed and 0 <= (now - close).total_seconds() <= ALERT_WINDOW}
        current = utc_seconds(now)
        last_close = current - current % BAR
        first_open = utc_seconds(cutoffs[0][1]) - BAR
        range_due = last_close >= first_open + 2 * BAR and current - last_close <= ALERT_WINDOW
        if (not due and not range_due) or (self.last_attempt is not None and
                       (now - self.last_attempt).total_seconds() < POLL_SECONDS):
            return
        self.last_attempt = now
        try:
            sent = read_json(self.path, {})
        except (OSError, ValueError) as error:
            LOG.warning("No se pudo leer el historial de avisos: %s", error)
            return
        if due:
            try:
                self.poll_first_candle(now, due, sent)
            except (RuntimeError, OSError, ValueError) as error:
                LOG.warning("Aperturas EURUSD: %s", error)
        if range_due:
            for symbol in ALERT_SYMBOLS:
                if self.processed_ranges.get(symbol) == last_close:
                    continue
                try:
                    self.poll_range(now, last_close, symbol, sent)
                except (RuntimeError, OSError, ValueError) as error:
                    LOG.warning("Rangos de apertura %s: %s", symbol, error)

    def send_once(self, sent, key, closed, now, title, message):
        if key in sent:
            return
        self.notifier(title, message)
        sent[key] = closed
        try:
            save_json(self.path, {k: v for k, v in sent.items() if v >= utc_seconds(now) - 14 * 86400})
        except (RuntimeError, OSError, ValueError) as error:
            LOG.warning("No se guardó el aviso %s: %s", key, error)

    def poll_first_candle(self, now, due, sent):
        for result in self.read(now)["checks"]:
            key = result["id"]
            if key not in due or result["status"] != "closed":
                continue
            if result["alerts"]:
                self.send_once(sent, key, result["close_utc"], now,
                               f"SMC 3.0 · EURUSD · {result['name']}", " · ".join(result["alerts"]))
            self.completed.add(key)

    def poll_range(self, now, closed, symbol, sent):
        snapshot = self.read(now, symbol)
        if snapshot["last_closed_utc"] is None or snapshot["last_closed_utc"] < closed:
            return
        details = [f"{ALERT_EVENTS[event['kind']]} del {'alto' if event['side'] == 'high' else 'bajo'} de {check['name']}"
                   f" ({event['level']})"
                   for check in snapshot["checks"] for event in check["events"]
                   if event["close_utc"] == closed]
        if details:
            broker_close = mt5_time(closed + self.verified_offset[1])[11:16]
            self.send_once(sent, f"range/{symbol}/{closed}", closed, now,
                           f"SMC 3.0 · {symbol} · M15 {broker_close} MT5", " · ".join(details))
        self.processed_ranges[symbol] = closed
