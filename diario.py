from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from threading import Lock

import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FRAMES = {name: getattr(mt5, "TIMEFRAME_" + name)
          for name in ("M1", "M5", "M15", "H1", "H4", "D1")}
EXECUTIONS = {mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL}
OUT = {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY}
MONEY = ("profit", "commission", "swap", "fee")
DEAL_FIELDS = ("ticket", "order", "time", "time_msc", "type", "entry", "position_id",
               "reason", "volume", "price", "symbol", "comment", *MONEY)
MT5_LOCK = Lock()


class MT5ConnectionError(RuntimeError):
    """Explicitly unavailable terminal, distinct from missing market history."""


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        staging = Path(file.name)
        try:
            json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
        except Exception:
            file.close()
            staging.unlink(missing_ok=True)
            raise
    try:
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)


def checked(result, operation):
    if result is None:
        raise RuntimeError(f"MT5 · {operation} · {mt5.last_error()}")
    return result


def config():
    settings = read_json(DATA / "cuenta.json")
    if not settings or not settings.get("login"):
        raise RuntimeError("Falta configurar data/cuenta.json.")
    return settings


def journal_path(settings):
    server = re.sub(r"[^a-zA-Z0-9_-]", "_", settings["server"])
    return DATA / f"diario-{server}-{int(settings['login'])}.json"


def verify_account(settings):
    terminal = mt5.terminal_info()
    if terminal is None or not terminal.connected:
        raise MT5ConnectionError("MT5 está desconectado.")
    account = checked(mt5.account_info(), "cuenta")
    if (account.login, account.server) != (settings["login"], settings["server"]):
        raise RuntimeError("La cuenta activa de MT5 no coincide con la del diario.")
    return account


@contextmanager
def connection(settings):
    with MT5_LOCK:
        if not mt5.initialize(settings["terminal"], timeout=5000):
            raise MT5ConnectionError(f"Abre MetaTrader 5 en la cuenta del diario. {mt5.last_error()}")
        try:
            verify_account(settings)
            yield
        finally:
            mt5.shutdown()


def dec(value):
    return Decimal(str(value))


def net(row):
    return sum(dec(row[key]) for key in MONEY)


def mt5_time(timestamp):
    # Se preserva el reloj reportado por el terminal, sin inferir su zona.
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def closed_positions(deals, active_ids, digits):
    groups = defaultdict(list)
    for row in deals:
        if row["position_id"] and row["type"] in EXECUTIONS:
            groups[row["position_id"]].append(row)
    closed, incomplete = [], []
    for position, rows in groups.items():
        if position in active_ids:
            continue
        opening = [row for row in rows if row["entry"] == mt5.DEAL_ENTRY_IN]
        exits = [row for row in rows if row["entry"] in OUT]
        if not opening or not exits or len(opening) + len(exits) != len(rows):
            incomplete.append(position)
            continue
        opened_volume = sum(dec(row["volume"]) for row in opening)
        closed_volume = sum(dec(row["volume"]) for row in exits)
        if abs(opened_volume - closed_volume) > Decimal("0.00000001"):
            incomplete.append(position)
            continue
        first, last = opening[0], exits[-1]

        def average_price(executions, volume):
            return float(sum(dec(row["price"]) * dec(row["volume"])
                             for row in executions) / volume)

        closed.append({
            "position": position, "symbol": first["symbol"],
            "side": "Compra" if first["type"] == mt5.DEAL_TYPE_BUY else "Venta",
            "opened": mt5_time(first["time"]), "closed": mt5_time(last["time"]),
            "open_time": first["time"],
            "volume": float(opened_volume),
            "entry_price": average_price(opening, opened_volume),
            "exit_price": average_price(exits, closed_volume),
            "net": float(round(sum(map(net, rows)), digits)),
            "reason": {mt5.DEAL_REASON_SL: "SL", mt5.DEAL_REASON_TP: "TP"}.get(last["reason"], "Otro"),
            "exit_count": len(exits),
        })
    return sorted(closed, key=lambda row: (row["closed"], row["position"])), incomplete


def build_journal(account, deals, positions, orders):
    def money(value):
        return float(round(value, account.currency_digits))

    closed, incomplete = closed_positions(
        deals, {row.identifier for row in positions}, account.currency_digits)
    funding_types = {mt5.DEAL_TYPE_BALANCE, mt5.DEAL_TYPE_CREDIT}
    def is_initial_deposit(row):
        broker_label = re.sub(r"[^a-z]", "", row["comment"].lower())
        return (not row["position_id"] and not row["symbol"] and row["profit"] > 0
                and broker_label == "initialdeposit")

    funding = [row for row in deals if row["type"] in funding_types or is_initial_deposit(row)]
    executions = [row for row in deals if row["type"] in EXECUTIONS]
    adjustments = [row for row in deals if row["type"] not in EXECUTIONS | funding_types
                   and not is_initial_deposit(row)]
    deposit = next((row for row in funding if is_initial_deposit(row)
                    or (row["type"] == mt5.DEAL_TYPE_BALANCE and row["profit"] > 0)), None)
    peak = running = drawdown = Decimal(0)
    for row in deals:
        if row["type"] != mt5.DEAL_TYPE_CREDIT:
            running += net(row)
            peak = max(running, peak)
            drawdown = max(drawdown, peak - running)

    def grouped(key):
        groups = defaultdict(list)
        for row in closed:
            groups[key(row)].append(dec(row["net"]))
        return {name: {"positions": len(values), "net": money(sum(values))}
                for name, values in sorted(groups.items())}

    wins = [dec(row["net"]) for row in closed if row["net"] > 0]
    losses = [dec(row["net"]) for row in closed if row["net"] < 0]
    return {
        "account": {key: getattr(account, key) for key in
                    ("login", "server", "currency", "trade_mode", "balance", "equity", "profit", "credit")},
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "initial_deposit": money(net(deposit)) if deposit else None,
        "initial_deposit_time": mt5_time(deposit["time"]) if deposit else None,
        "funding_movements": len(funding),
        "other_cash_movements": len(adjustments),
        "execution_net": money(sum(map(net, executions))),
        "execution_costs": money(sum(sum(dec(row[k]) for k in ("commission", "swap", "fee"))
                                     for row in executions)),
        "balance_difference": money(dec(account.balance) - running),
        "max_balance_drawdown": money(drawdown),
        "winners": len(wins), "losers": len(losses),
        "flat": len(closed) - len(wins) - len(losses),
        "profit_factor": round(float(sum(wins) / -sum(losses)), 3) if losses else None,
        "open_positions": [{key: getattr(row, key) for key in
                            ("identifier", "symbol", "type", "volume", "price_open", "sl", "tp", "profit", "swap")}
                           for row in positions],
        "pending_orders": len(orders),
        "incomplete_positions": incomplete,
        "daily": grouped(lambda row: row["closed"][:10]),
        "symbols": grouped(lambda row: row["symbol"]),
        "closed": closed,
        "deals": deals,
    }


def sync(settings):
    with connection(settings):
        # Incluye las marcas del servidor si su reloj va adelantado.
        end = int(datetime.now(timezone.utc).timestamp()) + 172800
        history = checked(mt5.history_deals_get(946684800, end), "historial")
        positions = checked(mt5.positions_get(), "posiciones")
        orders = checked(mt5.orders_get(), "órdenes pendientes")
        account = verify_account(settings)
    deals = sorted(
        {row.ticket: {key: getattr(row, key) for key in DEAL_FIELDS} for row in history}.values(),
        key=lambda row: (row["time_msc"], row["ticket"])
    )
    path = journal_path(settings)
    if {row["ticket"] for row in read_json(path, {}).get("deals", [])}.difference(
            row["ticket"] for row in deals):
        raise RuntimeError("MT5 omitió tickets ya guardados. Se conserva el diario anterior.")
    report = build_journal(account, deals, positions, orders)
    save_json(path, report)
    return report


def workspace_key(symbol, frame):
    if not re.fullmatch(r"[a-zA-Z0-9._#-]{1,32}", symbol) or frame not in FRAMES:
        raise ValueError("Símbolo o temporalidad inválidos.")
    return f"{symbol}/{frame}"


def chart(settings, symbol, frame):
    workspace_key(symbol, frame)
    with connection(settings):
        info = checked(mt5.symbol_info(symbol), f"símbolo {symbol}")
        rows = checked(mt5.copy_rates_from_pos(symbol, FRAMES[frame], 0, 550), "velas")
    return {"digits": info.digits, "rows": [
        [int(row["time"]), *[float(row[key]) for key in ("open", "high", "low", "close")]]
        for row in rows
    ]}
