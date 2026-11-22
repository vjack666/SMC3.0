"""Universo confirmado y nombres del terminal FundedNext."""

import json
from pathlib import Path
import re


def read_instrument_catalog():
    # This resource is also served by older SMC servers that lack /api/poi-universe.
    page = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="mt5Catalog" type="application/json">\s*(.*?)\s*</script>', page, re.S)
    if match is None:
        raise RuntimeError("Falta el catálogo confirmado de MT5 en index.html.")
    return json.loads(match[1])


CATALOG = read_instrument_catalog()
FOREX_SYMBOLS = tuple(CATALOG["forex"])
INDEX_SYMBOLS = CATALOG["indices"]
COMMODITY_SYMBOLS = CATALOG["commodities"]
SYMBOL_GROUPS = {"forex": FOREX_SYMBOLS, "indices": tuple(INDEX_SYMBOLS.values()),
                 "commodities": tuple(COMMODITY_SYMBOLS.values())}
MT5_SYMBOLS = FOREX_SYMBOLS + SYMBOL_GROUPS["indices"] + SYMBOL_GROUPS["commodities"]
ALERT_SYMBOLS = ("EURUSD", "GBPJPY", "US30")
WATCH_SYMBOLS = (*FOREX_SYMBOLS, "US30")
