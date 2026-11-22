"""Avisos locales para cierres nuevos y cambios confirmados de conexión."""

from datetime import timedelta
from hashlib import sha256
import logging

from diario import DATA, read_json, save_json
from sesiones import notify_windows

LOG = logging.getLogger(__name__)
MAX_AGE = 180
MODELS = {"turtle_soup": "Turtle Soup", "reversal": "Giro por barrido", "continuation": "Continuación"}


class MarketNotices:
    def __init__(self, notifier=notify_windows, path=DATA / "avisos-motor.json"):
        self.notifier = notifier
        self.path = path
        self.watermarks = {}
        self.connection = {}

    def publish_once(self, key, now, title, message):
        try:
            sent = read_json(self.path, {})
            if key in sent:
                return
            cutoff = (now - timedelta(days=14)).timestamp()
            save_json(self.path, {k: v for k, v in sent.items() if v >= cutoff} | {key: now.timestamp()})
            self.notifier(title, message)
        except (OSError, RuntimeError, ValueError, AttributeError, TypeError):
            LOG.exception("No se pudo registrar o mostrar un aviso del motor")

    def observe_analysis(self, identity, analysis, now, offset, tick_age):
        symbol = analysis["symbol"]
        scope = (identity, symbol)
        closed = analysis["asof"]
        previous = self.watermarks.get(scope)
        self.watermarks[scope] = max(previous or closed, closed)
        if previous is None or closed <= previous or offset is None or tick_age is None:
            return
        age = now.timestamp() + offset - closed
        if not (0 <= age <= MAX_AGE and -2 <= tick_age <= MAX_AGE):
            return

        account_tag = sha256(repr(identity).encode()).hexdigest()[:16]
        for setup in analysis["book22"]:
            if setup["status"] != "qualified" or setup["evaluated"] != closed:
                continue
            model = MODELS[setup["model"]]
            side = "Compra" if setup["direction"] == 1 else "Venta"
            self.publish_once(
                f"{account_tag}/{symbol}/{setup['id']}/{closed}", now,
                f"SMC 3.0 · {symbol} M15",
                f"{side} · {model} · {setup['rr']:.2f}R · Escenario de observación",
            )

    def observe_connection(self, identity, connected, now):
        # The first successful read establishes the baseline without a notice.
        state = self.connection.get(identity)
        if state is None:
            if connected:
                self.connection[identity] = (True, None, 0)
            return
        stable, since, count = state
        if connected == stable:
            self.connection[identity] = (stable, None, 0)
            return
        since, count = since or now, count + 1
        seconds = (now - since).total_seconds()
        if count < 3 or seconds < (30 if connected else 90):
            self.connection[identity] = (stable, since, count)
            return

        self.connection[identity] = (connected, None, 0)
        try:
            self.notifier("SMC 3.0 · conexión MT5", "Conexión recuperada." if connected else
                          "MT5 sigue sin conexión. El panel conserva el último análisis disponible.")
        except (OSError, RuntimeError, ValueError):
            LOG.exception("No se pudo mostrar el aviso de conexión")
