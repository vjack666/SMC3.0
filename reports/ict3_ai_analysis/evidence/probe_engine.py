"""Sonda de lectura: vuelca la salida real de ict_chart a JSON."""
import json
import sys
from datetime import datetime

import pandas as pd

ROOT = "C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0"
sys.path.insert(0, ROOT)

from diario import config  # noqa: E402
from ict import ict_chart  # noqa: E402


def jsonable(obj):
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes, dict, list, tuple)):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    frame = sys.argv[2] if len(sys.argv) > 2 else "M15"
    cutoff = int(sys.argv[3]) if len(sys.argv) > 3 else None
    result = ict_chart(config(), symbol, frame, cutoff)
    out = f"C:/Users/v_jac/AppData/Local/hermes/cache/scratch/ict3_audit/api_samples/probe_{symbol}_{frame}_{cutoff or 'now'}.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(jsonable(result), fh, ensure_ascii=False, indent=2)
    print("OUT", out)
    print("TOP", list(result.keys()))
    ict3 = result.get("ict3", {})
    print("ICT3", list(ict3.keys()) if isinstance(ict3, dict) else type(ict3))


if __name__ == "__main__":
    main()
