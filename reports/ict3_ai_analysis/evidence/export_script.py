"""Exportación forense de ICT 3.0.

Lee ÚNICAMENTE la salida real del motor (ict.ict_chart) y la escribe en
reports/ict3_ai_analysis. No crea un segundo motor y no modifica envíos.
Uso:
  python export.py [SYMBOL ...]     # sin argumentos = todos los disponibles
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path("C:/Users/v_jac/Desktop/MT5-POI-Compartido/SMC3.0")
OUT = ROOT / "reports" / "ict3_ai_analysis"
sys.path.insert(0, str(ROOT))

from diario import config  # noqa: E402
from ict import BAR_COUNT, PROFILE, REVISION, ict_chart  # noqa: E402
from motor_smc.instrumentos import CATALOG, MT5_SYMBOLS, SYMBOL_GROUPS  # noqa: E402

GENERATED_AT = int(datetime.now(timezone.utc).timestamp())
FRAMES = ("M15", "H4", "H1", "D1")


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


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(jsonable(data), fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def key_tree(obj, depth=0, maxdepth=6):
    if depth >= maxdepth:
        return type(obj).__name__
    if isinstance(obj, dict):
        return {str(k): key_tree(v, depth + 1, maxdepth) for k, v in obj.items()}
    if isinstance(obj, list):
        if not obj:
            return "[]"
        return [key_tree(obj[0], depth + 1, maxdepth)] if depth < maxdepth - 1 else "[...]"
    return type(obj).__name__


def collect_instrument(symbol, settings):
    results = {}
    for frame in FRAMES:
        results[frame] = jsonable(ict_chart(settings, symbol, frame, None))
    primary = results["M15"]
    return results, primary


def build_poi(symbol, results, primary):
    rows = {}
    for frame, result in results.items():
        for mark in result.get("marks", []):
            try:
                rows[mark["id"]] = {
                    "id": mark["id"],
                    "instrument": symbol,
                    "kind": mark.get("kind"),
                    "origin_tf": mark.get("tf"),
                    "direction": mark.get("direction"),
                    "low": mark.get("low"),
                    "high": mark.get("high"),
                    "opened_at": mark.get("open"),
                    "opened_at_utc": iso(mark.get("open")),
                    "confirmed_at": mark.get("confirmed"),
                    "confirmed_at_utc": iso(mark.get("confirmed")),
                    "first_touch_at": mark.get("touch"),
                    "first_touch_at_utc": iso(mark.get("touch")),
                    "related_to_ict3_event": mark.get("related", False),
                    "source": "engine.marks",
                }
            except (KeyError, TypeError):
                continue
    for poi in primary.get("pois", []):
        pid = poi.get("id") or poi.get("zone_id")
        if pid and pid not in rows:
            rows[pid] = dict(poi, instrument=symbol, source="engine.pois")
    events = primary.get("ict3", {}).get("events", [])
    for event in events:
        for candidate in event.get("poi_candidates", []):
            pid = candidate.get("zone_id")
            if not pid:
                continue
            row = rows.setdefault(pid, {
                "id": pid, "instrument": symbol, "kind": candidate.get("kind"),
                "origin_tf": None, "direction": candidate.get("direction"),
                "low": candidate.get("low"), "high": candidate.get("high"),
                "confirmed_at": candidate.get("confirmed_at"),
                "confirmed_at_utc": iso(candidate.get("confirmed_at")),
                "first_touch_at": candidate.get("first_touch_at"),
                "first_touch_at_utc": iso(candidate.get("first_touch_at")),
                "source": "engine.ict3.poi_candidates",
            })
            row.setdefault("linked_event_ids", []).append(event.get("event_id"))
            if event.get("primary_poi") == pid:
                row["primary_for_event"] = event.get("event_id")
    return {
        "instrument": symbol,
        "asof": primary.get("asof"),
        "asof_utc": iso(primary.get("asof")),
        "engine_source": primary.get("source"),
        "schema_version": primary.get("ict3", {}).get("schema_version"),
        "count": len(rows),
        "note": ("POI = zonas devueltas por el motor (marks/pois/candidatos de eventos). "
                 "Los estados de mitigate/invalidación se conservan en events.json; "
                 "el motor no expone un campo lifecycle independiente para cada zona."),
        "pois": [rows[k] for k in sorted(rows)],
    }


def build_liquidity(primary):
    liq = primary.get("daily_liquidity", {}) or {}
    levels = []
    for name in ("pdh", "pdl"):
        if name in liq and liq[name] is not None:
            levels.append({
                "name": name.upper(), "price": liq[name],
                "source_open": liq.get("source_open"),
                "source_open_utc": iso(liq.get("source_open")),
                "session_open": liq.get("session_open"),
                "first_m15_open": liq.get(f"{name}_m15_open"),
                "first_m15_open_utc": iso(liq.get(f"{name}_m15_open")),
                "origin_tf": "D1", "source": "engine.daily_liquidity",
            })
    friday = primary.get("friday_reference", {}) or {}
    for name in ("high", "low"):
        if name in friday and friday[name] is not None:
            levels.append({
                "name": f"LAST_FRIDAY_{name.upper()}", "price": friday[name],
                "source_open": friday.get("source_open"),
                "source_open_utc": iso(friday.get("source_open")),
                "source_close": friday.get("source_close"),
                "source_close_utc": iso(friday.get("source_close")),
                "origin_tf": "D1", "source": "engine.friday_reference",
            })
    for br in primary.get("ict3_breaks", []) or []:
        if br.get("level") is not None:
            levels.append({
                "name": br.get("level_name"), "price": br.get("level"),
                "direction": br.get("direction"),
                "source_open": br.get("source_open"),
                "source_open_utc": iso(br.get("source_open")),
                "session_open": br.get("session_open"),
                "session_open_utc": iso(br.get("session_open")),
                "signal_open": br.get("signal_open"),
                "signal_open_utc": iso(br.get("signal_open")),
                "signal_close": br.get("signal_close"),
                "signal_close_utc": iso(br.get("signal_close")),
                "state": br.get("state"),
                "event_id": br.get("event_id"),
                "strong": br.get("strong"),
                "origin_tf": "D1/M15", "source": "engine.ict3_breaks",
            })
    return {
        "instrument": primary.get("symbol"),
        "asof": primary.get("asof"),
        "asof_utc": iso(primary.get("asof")),
        "daily": liq,
        "levels": levels,
        "daily_events": liq.get("events", []),
        "note": ("Solo se publican niveles que el motor expone realmente. "
                 "No hay objetos semanales (PWH/PWL) ni mensuales (PMH/PML) en la salida; "
                 "BSL/SSL, equal highs/lows y rangos de sesión Tampoco están expuestos "
                 "como campos dedicados. No se inventan."),
    }


def build_events(primary):
    ict3 = primary.get("ict3", {}) or {}
    events = ict3.get("events", []) or []
    breaks = primary.get("ict3_breaks", []) or []
    timeline = []
    for event in events:
        transitions = []
        for tr in event.get("transition_history", []) or []:
            transitions.append({
                "from": tr.get("from"), "to": tr.get("to"),
                "at": tr.get("at"), "at_utc": iso(tr.get("at")),
                "reason": tr.get("reason"),
            })
        timeline.append({
            "event_id": event.get("event_id"),
            "level_name": event.get("level_name"),
            "level": event.get("level"),
            "direction": event.get("direction"),
            "observed_at": event.get("observed_at"),
            "observed_at_utc": iso(event.get("observed_at")),
            "accept_time": event.get("accept_time"),
            "accept_time_utc": iso(event.get("accept_time")),
            "retest_at": event.get("retest_at"),
            "retest_at_utc": iso(event.get("retest_at")),
            "link_state": event.get("link_state"),
            "current_state": event.get("current_state"),
            "primary_poi": event.get("primary_poi"),
            "poi_candidate_ids": [c.get("zone_id") for c in event.get("poi_candidates", [])],
            "transitions": transitions,
            "wait_reason": event.get("wait_reason"),
            "pending_evidence": event.get("pending_evidence"),
            "entry_authorized": event.get("entry_authorized"),
            "mode": event.get("mode"),
        })
    return {
        "instrument": primary.get("symbol"),
        "asof": primary.get("asof"),
        "asof_utc": iso(primary.get("asof")),
        "schema_version": ict3.get("schema_version"),
        "mode": ict3.get("mode"),
        "count": len(events),
        "events": events,
        "event_timeline": sorted(timeline, key=lambda x: x.get("observed_at") or 0),
        "break_studies": breaks,
        "load": ict3.get("load"),
        "note": ("Secuencia causal generada por el motor: Liquidity → Sweep → Displacement "
                 "→ aceptación → retest → POI state. Cada transición conserva su timestamp. "
                 "entry_authorized/mode se publican tal cual; no se alteran."),
    }


def build_chart_objects(results, primary):
    zones = []
    for frame, result in results.items():
        for mark in result.get("marks", []):
            zones.append({
                "object_id": mark.get("id"), "type": "zone", "tf": mark.get("tf"),
                "kind": mark.get("kind"), "direction": mark.get("direction"),
                "price_low": mark.get("low"), "price_high": mark.get("high"),
                "opened": mark.get("open"), "opened_utc": iso(mark.get("open")),
                "confirmed": mark.get("confirmed"), "confirmed_utc": iso(mark.get("confirmed")),
                "touch": mark.get("touch"), "touch_utc": iso(mark.get("touch")),
                "related_to_event": mark.get("related", False),
            })
    lines = []
    liq = build_liquidity(primary)
    for level in liq["levels"]:
        lines.append({
            "object_id": f"line:{level['name']}:{level.get('price')}",
            "type": "horizontal_line", "name": level["name"],
            "price": level.get("price"), "origin_tf": level.get("origin_tf"),
            "source": level.get("source"), "time": level.get("source_open"),
            "time_utc": level.get("source_open_utc"),
        })
    markers = []
    for event in build_events(primary)["event_timeline"]:
        for label, key in (("observed", "observed_at"), ("accept", "accept_time"), ("retest", "retest_at")):
            if event.get(key):
                markers.append({
                    "object_id": f"event:{event['event_id']}:{label}",
                    "type": "event_marker", "event_id": event["event_id"],
                    "label": label, "time": event[key], "time_utc": event.get(key + "_utc"),
                    "price": event.get("level"), "state": event.get("current_state"),
                })
    return {
        "instrument": primary.get("symbol"),
        "asof": primary.get("asof"),
        "asof_utc": iso(primary.get("asof")),
        "time_basis": primary.get("time_basis"),
        "last_closed_by_tf": primary.get("last_closed_by_tf"),
        "zones": zones, "horizontal_lines": lines, "event_markers": markers,
        "counts": {"zones": len(zones), "horizontal_lines": len(lines), "event_markers": len(markers)},
        "note": ("Representación reconstruible: zonas rectangulares, líneas horizontales y "
                 "marcadores de evento con coordenadas de precio/tiempo e IDs que enlazan "
                 "con events.json y poi.json. No se incluyen velas OHLC completas: el motor "
                 "no las expone en su salida; se entregan como evidencia los metadatos de cierre."),
    }


def md_instrument(symbol, primary, poi, liquidity, events, chart):
    ict3 = primary.get("ict3", {}) or {}
    regime = primary.get("regime", {}) or {}
    lines = []
    add = lines.append
    add(f"# {symbol} — radiografía técnica ICT 3.0\n")
    add(f"> Generado desde la salida real de `ict.ict_chart` (revisión `{primary.get('source')}`). "
        f"Modo del motor: **{ict3.get('mode')}**. `entry_authorized` se conserva sin modificar.\n")
    add("## 1. Identificación y snapshot\n")
    add(f"- Instrumento: `{primary.get('symbol')}`")
    add(f"- Marco solicitado: `{primary.get('frame')}`; base temporal: `{primary.get('time_basis')}`")
    add(f"- `asof`: {primary.get('asof')} ({iso(primary.get('asof'))})")
    add(f"- Última vela cerrada: {primary.get('latest_closed')} ({iso(primary.get('latest_closed'))})")
    add(f"- Cierre por temporalidad: " + ", ".join(
        f"{k}={v} ({iso(v)})" for k, v in (primary.get("last_closed_by_tf") or {}).items()))
    add(f"- Sesgo: **{primary.get('bias')}** · estado: **{primary.get('status')}** · "
        f"motivo: `{primary.get('context_reason')}`\n")
    add("## 2. Procedencia y cobertura de datos\n")
    add("- Fuente: terminal MetaTrader5 conectada; el motor lee velas con "
        f"`BAR_COUNT={BAR_COUNT}` por temporalidad y excluye la vela posición 0.")
    add(f"- Perfil calculado: `{', '.join(PROFILE)}`. M5/M1 solo se cargan si hay retest M15: "
        f"`load.load_reason={ict3.get('load', {}).get('load_reason')}`.")
    add("- No se usa el dataset Dukascopy de 20 años en la ejecución en vivo; se documenta aparte "
        "en `data_quality.md`. No existe base SQL en esta copia.\n")
    add("## 3. Estructura por temporalidad\n")
    add("| TF | Régimen (salida real) | Zonas (marks) |")
    add("|---|---|---|")
    for frame in ("D1", "H4", "H1", "M15"):
        regime_val = regime.get(frame, "no expuesto")
        n_marks = primary.get("marks") if frame == "M15" else None
        add(f"| {frame} | {regime_val} | {('ver chart_objects.json por TF' if n_marks is None else len(primary.get('marks', [])))} |")
    add("")
    add(f"- Estructura LTF: `{json.dumps(primary.get('structure'), ensure_ascii=False)}`")
    add(f"- Retest: `{json.dumps(primary.get('retest'), ensure_ascii=False)}`\n")
    add("## 4. Mapa de liquidez\n")
    add(f"- PDH/PDL y eventos diarios: `{json.dumps(liquidity['daily'], ensure_ascii=False)}`")
    add(f"- Niveles reconstruidos: **{len(liquidity['levels'])}** (ver `liquidity.json`).")
    add("- El motor no expone PWH/PWL, PMH/PML, BSL/SSL, equal highs/lows ni rangos de sesión "
        "como campos dedicados; no se inventan.\n")
    add("## 5. Catálogo de POI\n")
    add(f"- Zonas/POI reconstruidas: **{poi['count']}** (ver `poi.json` con IDs, TF de origen, "
        "precios y timestamps).")
    add(f"- `pois` del motor (candidatos cross-TF): **{len(primary.get('pois', []))}**.")
    add(f"- `marks` del marco M15: **{len(primary.get('marks', []))}**. "
        f"Tipos presentes: {', '.join(sorted({m.get('kind') for m in primary.get('marks', [])})) or 'ninguno'}.\n")
    add("## 6. Secuencia de eventos ICT\n")
    add(f"- Eventos: **{events['count']}** · estado(s): "
        f"{', '.join(sorted({e.get('current_state') for e in events['events']})) or 'ninguno'}")
    add(f"- Esquema: `{events['schema_version']}` · modo: `{events['mode']}`")
    add("- Cada evento conserva `observed_at`, `accept_time`, `retest_at`, "
        "`transition_history`, POI candidatos y `wait_reason` (ver `events.json`).\n")
    add("## 7. Mitigación / validez\n")
    add("- El motor no publica un campo `lifecycle` independiente por POI; la validez se "
        "observa en `link_state`, `current_state` y `transition_history` de cada evento.")
    add("- No se han reconstruido eventos con velas no cerradas: el motor usa `closed_frame` "
        "y `at` para cortes causales.\n")
    add("## 8-9. Confluencias y representación del gráfico\n")
    add(f"- Objetos: {json.dumps(chart['counts'], ensure_ascii=False)} "
        "(ver `chart_objects.json` con coordenadas e IDs).")
    add(f"- Book 22 (modelos del libro): **{len(primary.get('book22', []))}** registros reales "
        "en `analysis.json`.\n")
    add("## 10. Escenarios observados y niveles\n")
    add(f"- Escenario observado por el motor: sesgo `{primary.get('bias')}`, estado "
        f"`{primary.get('status')}`, motivo `{primary.get('context_reason')}`.")
    add(f"- Niveles de referencia: " + ", ".join(
        f"{l['name']}={l.get('price')}" for l in liquidity["levels"][:8]) + ".")
    add("- No se emite recomendación BUY/SELL: el modo del motor es "
        f"`{ict3.get('mode')}` y `entry_authorized` es false en los eventos.\n")
    add("## 11. Contradicciones y datos faltantes\n")
    add(f"- `h1_opposes_short` aparece como motivo: H1={regime.get('H1')} frente a "
        f"D1={regime.get('D1')}/H4={regime.get('H4')}; es una contradicción **real del motor**.")
    add(f"- M5/M1: {ict3.get('load', {}).get('load_reason')}; cobertura "
        f"{json.dumps(ict3.get('load', {}).get('coverage', {}), ensure_ascii=False)}.")
    add("- `pois`/`marks` son recuentos de la salida; una zona tocada no implica validación operativa.\n")
    add("## 12. Evidencia verificable\n")
    add(f"- `analysis.json` (salida completa), `poi.json`, `liquidity.json`, `events.json`, "
        f"`chart_objects.json`; copia sin procesar en `../evidence/raw/{symbol}_*.json`.")
    add(f"- `engine_source`={primary.get('source')}, `schema_version`={events['schema_version']}.")
    return "\n".join(lines) + "\n"


def main():
    args = sys.argv[1:]
    wanted = set(args) if args else None
    settings = config()
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("instruments", "evidence", "evidence/raw", "database"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    summary = []
    symbols = [s for s in MT5_SYMBOLS if wanted is None or s in wanted]
    for symbol in symbols:
        try:
            results, primary = collect_instrument(symbol, settings)
            if not primary.get("enabled", True):
                summary.append({"symbol": symbol, "status": "NOT_ENABLED", "reason": primary.get("reason")})
                continue
        except Exception as error:
            summary.append({"symbol": symbol, "status": "UNAVAILABLE", "reason": f"{type(error).__name__}: {error}"})
            print("SKIP", symbol, type(error).__name__, str(error)[:120], flush=True)
            continue
        folder = OUT / "instruments" / symbol
        folder.mkdir(parents=True, exist_ok=True)
        for frame, result in results.items():
            dump(OUT / "evidence" / "raw" / f"{symbol}_{frame}.json", result)
        poi = build_poi(symbol, results, primary)
        liquidity = build_liquidity(primary)
        events = build_events(primary)
        chart = build_chart_objects(results, primary)
        analysis = dict(primary)
        analysis["exported_frames"] = {
            frame: {"latest_closed": res.get("latest_closed"),
                    "marks": len(res.get("marks", [])),
                    "keys": list(res.keys())} for frame, res in results.items()
        }
        analysis["export_note"] = "Salida real del motor; no se han alterado campos de política ni autorización."
        dump(folder / "analysis.json", analysis)
        dump(folder / "poi.json", poi)
        dump(folder / "liquidity.json", liquidity)
        dump(folder / "events.json", events)
        dump(folder / "chart_objects.json", chart)
        (folder / "analysis.md").write_text(
            md_instrument(symbol, primary, poi, liquidity, events, chart), encoding="utf-8")
        ict3 = primary.get("ict3", {}) or {}
        summary.append({
            "symbol": symbol, "status": "EXPORTED",
            "asof": primary.get("asof"), "asof_utc": iso(primary.get("asof")),
            "bias": primary.get("bias"), "state": primary.get("status"),
            "regime": primary.get("regime"),
            "marks_m15": len(primary.get("marks", [])),
            "pois": poi["count"], "events": events["count"],
            "states": sorted({e.get("current_state") for e in events["events"]}),
            "mode": ict3.get("mode"), "schema_version": ict3.get("schema_version"),
        })
        print("OK", symbol, "events", events["count"], "pois", poi["count"], flush=True)

    dump(OUT / "evidence" / "instrument_summary.json", summary)
    print("SUMMARY", json.dumps({"exported": sum(s["status"] == "EXPORTED" for s in summary),
                                 "skipped": sum(s["status"] != "EXPORTED" for s in summary)}), flush=True)


if __name__ == "__main__":
    main()
