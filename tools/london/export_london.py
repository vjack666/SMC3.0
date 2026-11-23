#!/usr/bin/env python3
"""Compact, path-independent, idempotent London 08:15 ICT 3.0 snapshot exporter.

Reads ONLY the real output of ``ict.ict_chart`` (with an explicit causal
``cutoff``) and writes a compact, reproducible bundle.  No second engine, no
raw 80 MB OHLC dumps, no credentials, no wall-clock bytes.

CLI
---
    python export_london.py --root <PROJECT> --cutoff <UTC_EPOCH> \
        --date YYYY-MM-DD --out <SNAPSHOT_FOLDER> [--symbols EURUSD GBPJPY ...]

``--root`` may be supplied with the ``ICT3_ROOT`` environment variable.  The
module contains no hard-coded local user path.

Reproducibility
---------------
Every written byte is a pure function of (cutoff, London date, requested
symbols, engine output).  ``generated_at_utc`` defaults to ``cutoff``
(reproducible-builds ``SOURCE_DATE_EPOCH`` style) and can be overridden with
``--generated-at`` / ``ICT3_GENERATED_AT`` when a real export stamp is wanted.
Re-running with the same cutoff and data overwrites the same bytes.

``write_latest_json`` is deliberately a standalone function; it is NEVER
called by ``main()``.  It updates ``latest.json`` only after an explicit
validation result with ``ok is True`` is handed to it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

# --------------------------------------------------------------------------
# Deterministic constants (no local filesystem paths)
# --------------------------------------------------------------------------
BUNDLE_SCHEMA_VERSION = "ict3-london-snapshot/1.0"
DEFAULT_FRAME = "M15"
PROFILE = ("M15", "H4", "H1", "D1")
TF_SECONDS = {"D1": 86400, "H4": 14400, "H1": 3600, "M15": 900, "M5": 300, "M1": 60}
STALE_TOLERANCE_SECONDS = 900          # one M15 bar of grace
CUTOFF_LOCAL_TIME = (8, 15)            # 08:15 Europe/London
SOURCE_REPOSITORY = "https://github.com/vjack666/SMC3.0"
PROVIDER = "MetaTrader5"
HASH_BASIS = (
    "SHA-256 computed over UTF-8 bytes with line endings normalized to LF; "
    "byte counts are the actual file sizes; the manifest excludes itself."
)
EXPECTED_MODE = "OBSERVE_ONLY_NO_ORDER"


# --------------------------------------------------------------------------
# Small, dependency-free helpers
# --------------------------------------------------------------------------
def _zone(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return None


def _last_sunday(year, month):
    if month == 12:
        last = date_cls(year, 12, 31)
    else:
        last = date_cls(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def _london_offset(utc_naive):
    """Britain offset in seconds at a UTC instant (BST last Sun Mar..Oct)."""
    year = utc_naive.year
    start = datetime(year, 3, _last_sunday(year, 3).day, 1, 0)
    end = datetime(year, 10, _last_sunday(year, 10).day, 1, 0)
    return 3600 if start <= utc_naive < end else 0


def _zoned_datetime(epoch, tzname):
    epoch = int(epoch)
    zone = _zone(tzname)
    if zone is not None:
        return datetime.fromtimestamp(epoch, zone)
    # Offline fallback for hosts without an IANA database.
    utc_naive = datetime.fromtimestamp(epoch, timezone.utc).replace(tzinfo=None)
    if tzname == "America/Guayaquil":
        fixed = timezone(timedelta(hours=-5), "GMT-05")
        return datetime.fromtimestamp(epoch, fixed)
    offset = _london_offset(utc_naive)
    fixed = timezone(timedelta(seconds=offset), "BST" if offset else "GMT")
    return datetime.fromtimestamp(epoch, fixed)


def zoned_iso(epoch, tzname):
    return _zoned_datetime(epoch, tzname).isoformat()


def iso_utc(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def real_utc(epoch, broker_offset):
    """MT5 epoch -> real UTC epoch. MT5 encodes broker-local time as epoch."""
    if epoch is None:
        return None
    return int(epoch) - int(broker_offset)


def expected_cutoff(london_date, tzname="Europe/London"):
    """UTC epoch for 08:15 on ``london_date`` in ``tzname`` (BST/GMT aware)."""
    y, m, d = (int(part) for part in london_date.split("-"))
    local = datetime(y, m, d, CUTOFF_LOCAL_TIME[0], CUTOFF_LOCAL_TIME[1])
    zone = _zone(tzname)
    if zone is not None:
        return int(local.replace(tzinfo=zone).timestamp())
    # Fallback: first guess UTC, then correct by the offset at that instant.
    guess = int(local.replace(tzinfo=timezone.utc).timestamp())
    return guess - _london_offset(datetime.fromtimestamp(guess, timezone.utc).replace(tzinfo=None))


def jsonable(obj):
    """Convert engine objects to JSON-safe values without changing semantics."""
    if isinstance(obj, (datetime, date_cls)):
        return obj.isoformat()
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes, dict, list, tuple, set)):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted((jsonable(v) for v in obj), key=lambda x: repr(x))
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def json_bytes(data):
    # Compact JSON: same fields, ~32% smaller than indent=2. Deterministic.
    text = json.dumps(jsonable(data), ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True) + "\n"
    return text.encode("utf-8")


def lf_normalize(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_lf(data: bytes) -> str:
    return hashlib.sha256(lf_normalize(data)).hexdigest()


def safe_symbol(symbol):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(symbol))


def sanitize_reason(exc):
    """Deterministic, path/credential-free description of a failure."""
    text = str(exc).strip().splitlines()[0] if str(exc) else ""
    text = re.sub(r"[A-Za-z]:[\\/][^\s]+", "<path>", text)
    text = re.sub(r"\d+\.\d+\.\d+\.\d+", "<host>", text)
    text = re.sub(r"\b\d{6,}\b", "<num>", text)
    return (type(exc).__name__ + ": " + text)[:240] if text else type(exc).__name__


# --------------------------------------------------------------------------
# Engine loading (real) -- no hard-coded local path
# --------------------------------------------------------------------------
def load_engine(root):
    """Import ``ict.ict_chart`` from ``root`` and return a uniform adapter."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise RuntimeError("ICT3 root is not a directory: %s" % root_path)
    sys.path.insert(0, str(root_path))
    import importlib
    ict = importlib.import_module("ict")
    instrumentos = importlib.import_module("motor_smc.instrumentos")
    diario = importlib.import_module("diario")
    return SimpleNamespace(
        ict_chart=ict.ict_chart,
        REVISION=getattr(ict, "REVISION", "unknown"),
        PROFILE=tuple(getattr(ict, "PROFILE", PROFILE)),
        BAR_COUNT=getattr(ict, "BAR_COUNT", None),
        MT5_SYMBOLS=tuple(instrumentos.MT5_SYMBOLS),
        CATALOG=jsonable(getattr(instrumentos, "CATALOG", {})),
        config=getattr(diario, "config", lambda: {}),
        module=ict,
    )


# --------------------------------------------------------------------------
# Per-instrument document builders (all fields derived from engine output)
# --------------------------------------------------------------------------
def build_poi(symbol, results, primary):
    rows = {}
    for frame, result in results.items():
        for mark in result.get("marks", []) or []:
            try:
                rows[mark["id"]] = {
                    "id": mark["id"], "instrument": symbol,
                    "kind": mark.get("kind"), "origin_tf": mark.get("tf"),
                    "direction": mark.get("direction"),
                    "low": mark.get("low"), "high": mark.get("high"),
                    "opened_at": mark.get("open"), "opened_at_utc": iso_utc(mark.get("open")),
                    "confirmed_at": mark.get("confirmed"), "confirmed_at_utc": iso_utc(mark.get("confirmed")),
                    "first_touch_at": mark.get("touch"), "first_touch_at_utc": iso_utc(mark.get("touch")),
                    "related_to_ict3_event": mark.get("related", False),
                    "source": "engine.marks", "origin_frame_calls": frame,
                }
            except (KeyError, TypeError):
                continue
    for poi in primary.get("pois", []) or []:
        pid = poi.get("id") or poi.get("zone_id")
        if pid and pid not in rows:
            rows[pid] = dict(poi, instrument=symbol, source="engine.pois")
    events = (primary.get("ict3", {}) or {}).get("events", []) or []
    for event in events:
        for candidate in event.get("poi_candidates", []) or []:
            pid = candidate.get("zone_id")
            if not pid:
                continue
            row = rows.setdefault(pid, {
                "id": pid, "instrument": symbol, "kind": candidate.get("kind"),
                "origin_tf": None, "direction": candidate.get("direction"),
                "low": candidate.get("low"), "high": candidate.get("high"),
                "confirmed_at": candidate.get("confirmed_at"),
                "confirmed_at_utc": iso_utc(candidate.get("confirmed_at")),
                "first_touch_at": candidate.get("first_touch_at"),
                "first_touch_at_utc": iso_utc(candidate.get("first_touch_at")),
                "source": "engine.ict3.poi_candidates",
            })
            row.setdefault("linked_event_ids", []).append(event.get("event_id"))
            if event.get("primary_poi") == pid:
                row["primary_for_event"] = event.get("event_id")
    return {
        "instrument": symbol, "asof": primary.get("asof"), "asof_utc": iso_utc(primary.get("asof")),
        "engine_source": primary.get("source"),
        "engine_schema_version": (primary.get("ict3", {}) or {}).get("schema_version"),
        "count": len(rows),
        "note": ("POI are zones actually returned by the engine (marks/pois/event candidates). "
                 "The engine does not expose an independent per-zone lifecycle field; "
                 "no lifecycle flag is invented here. State transitions live in events.json."),
        "pois": [rows[k] for k in sorted(rows)],
    }


def build_liquidity(primary):
    liq = primary.get("daily_liquidity", {}) or {}
    levels = []
    for name in ("pdh", "pdl"):
        if name in liq and liq[name] is not None:
            levels.append({
                "name": name.upper(), "price": liq[name],
                "source_open": liq.get("source_open"), "source_open_utc": iso_utc(liq.get("source_open")),
                "session_open": liq.get("session_open"),
                "first_m15_open": liq.get(f"{name}_m15_open"),
                "first_m15_open_utc": iso_utc(liq.get(f"{name}_m15_open")),
                "origin_tf": "D1", "source": "engine.daily_liquidity",
            })
    friday = primary.get("friday_reference", {}) or {}
    for name in ("high", "low"):
        if name in friday and friday[name] is not None:
            levels.append({
                "name": f"LAST_FRIDAY_{name.upper()}", "price": friday[name],
                "source_open": friday.get("source_open"), "source_open_utc": iso_utc(friday.get("source_open")),
                "source_close": friday.get("source_close"), "source_close_utc": iso_utc(friday.get("source_close")),
                "origin_tf": "D1", "source": "engine.friday_reference",
            })
    for br in primary.get("ict3_breaks", []) or []:
        if br.get("level") is not None:
            levels.append({
                "name": br.get("level_name"), "price": br.get("level"),
                "direction": br.get("direction"),
                "source_open": br.get("source_open"), "source_open_utc": iso_utc(br.get("source_open")),
                "session_open": br.get("session_open"), "session_open_utc": iso_utc(br.get("session_open")),
                "signal_open": br.get("signal_open"), "signal_open_utc": iso_utc(br.get("signal_open")),
                "signal_close": br.get("signal_close"), "signal_close_utc": iso_utc(br.get("signal_close")),
                "state": br.get("state"), "event_id": br.get("event_id"), "strong": br.get("strong"),
                "origin_tf": "D1/M15", "source": "engine.ict3_breaks",
            })
    return {
        "instrument": primary.get("symbol"), "asof": primary.get("asof"),
        "asof_utc": iso_utc(primary.get("asof")), "daily": liq, "levels": levels,
        "daily_events": liq.get("events", []),
        "note": ("Only levels the engine actually exposes are published. PWH/PWL, PMH/PML, "
                 "BSL/SSL, equal highs/lows and session ranges are not native outputs; "
                 "they are not invented."),
    }


def build_events(primary):
    ict3 = primary.get("ict3", {}) or {}
    events = ict3.get("events", []) or []
    breaks = primary.get("ict3_breaks", []) or []
    timeline = []
    for event in events:
        transitions = [{
            "from": tr.get("from"), "to": tr.get("to"), "at": tr.get("at"),
            "at_utc": iso_utc(tr.get("at")), "reason": tr.get("reason"),
        } for tr in (event.get("transition_history", []) or [])]
        timeline.append({
            "event_id": event.get("event_id"), "level_name": event.get("level_name"),
            "level": event.get("level"), "direction": event.get("direction"),
            "observed_at": event.get("observed_at"), "observed_at_utc": iso_utc(event.get("observed_at")),
            "accept_time": event.get("accept_time"), "accept_time_utc": iso_utc(event.get("accept_time")),
            "retest_at": event.get("retest_at"), "retest_at_utc": iso_utc(event.get("retest_at")),
            "link_state": event.get("link_state"), "current_state": event.get("current_state"),
            "primary_poi": event.get("primary_poi"),
            "poi_candidate_ids": [c.get("zone_id") for c in (event.get("poi_candidates", []) or [])],
            "transitions": transitions, "wait_reason": event.get("wait_reason"),
            "pending_evidence": event.get("pending_evidence"),
            "entry_authorized": event.get("entry_authorized"),
            "mode": event.get("mode"),
        })
    return {
        "instrument": primary.get("symbol"), "asof": primary.get("asof"),
        "asof_utc": iso_utc(primary.get("asof")),
        "schema_version": ict3.get("schema_version"), "mode": ict3.get("mode"),
        "count": len(events), "events": events,
        "event_timeline": sorted(timeline, key=lambda x: x.get("observed_at") or 0),
        "break_studies": breaks, "load": ict3.get("load"),
        "note": ("Causal sequence produced by the engine. entry_authorized and mode "
                 "are copied verbatim from the engine and never altered."),
    }


def build_chart_objects(results, primary):
    zones = []
    for frame, result in results.items():
        for mark in result.get("marks", []) or []:
            zones.append({
                "object_id": mark.get("id"), "type": "zone", "tf": mark.get("tf"),
                "kind": mark.get("kind"), "direction": mark.get("direction"),
                "price_low": mark.get("low"), "price_high": mark.get("high"),
                "opened": mark.get("open"), "opened_utc": iso_utc(mark.get("open")),
                "confirmed": mark.get("confirmed"), "confirmed_utc": iso_utc(mark.get("confirmed")),
                "touch": mark.get("touch"), "touch_utc": iso_utc(mark.get("touch")),
                "related_to_event": mark.get("related", False), "source_frame": frame,
            })
    levels = build_liquidity(primary)["levels"]
    lines = [{
        "object_id": f"line:{lv['name']}:{lv.get('price')}", "type": "horizontal_line",
        "name": lv["name"], "price": lv.get("price"), "origin_tf": lv.get("origin_tf"),
        "source": lv.get("source"), "time": lv.get("source_open"), "time_utc": lv.get("source_open_utc"),
    } for lv in levels]
    markers = []
    for event in build_events(primary)["event_timeline"]:
        for label, key in (("observed", "observed_at"), ("accept", "accept_time"), ("retest", "retest_at")):
            if event.get(key):
                markers.append({
                    "object_id": f"event:{event['event_id']}:{label}", "type": "event_marker",
                    "event_id": event["event_id"], "label": label, "time": event[key],
                    "time_utc": event.get(key + "_utc"), "price": event.get("level"),
                    "state": event.get("current_state"),
                })
    return {
        "instrument": primary.get("symbol"), "asof": primary.get("asof"),
        "asof_utc": iso_utc(primary.get("asof")), "time_basis": primary.get("time_basis"),
        "last_closed_by_tf": primary.get("last_closed_by_tf"),
        "zones": zones, "horizontal_lines": lines, "event_markers": markers,
        "counts": {"zones": len(zones), "horizontal_lines": len(lines), "event_markers": len(markers)},
        "note": ("Reconstructible objects with price/time coordinates and stable IDs linking "
                 "events.json and poi.json. No full OHLC bars: the engine does not expose them."),
    }


def build_analysis(primary, results, cutoff, broker_offset=0):
    analysis = dict(primary)
    analysis["snapshot_cutoff_utc"] = int(cutoff)
    analysis["snapshot_cutoff_utc_iso"] = iso_utc(cutoff)
    analysis["broker_clock_offset_seconds"] = int(broker_offset)
    analysis["asof_real_utc"] = iso_utc(real_utc(primary.get("asof"), broker_offset))
    analysis["latest_closed_real_utc"] = iso_utc(real_utc(primary.get("latest_closed"), broker_offset))
    analysis["time_basis_note"] = (
        "asof/latest_closed/last_closed_by_tf are MT5 encoded-clock epochs. "
        "Real UTC = value - broker_clock_offset_seconds."
    )
    analysis["exported_frames"] = {
        frame: {
            "latest_closed": res.get("latest_closed"),
            "marks": len(res.get("marks", []) or []),
            "enabled": res.get("enabled", True),
        } for frame, res in results.items()
    }
    analysis["export_note"] = "Verbatim engine output; policy and authorization fields are not modified."
    return analysis


def md_instrument(symbol, primary, poi, liquidity, events, chart, broker_offset=0):
    ict3 = primary.get("ict3", {}) or {}
    regime = primary.get("regime", {}) or {}
    lines = []
    add = lines.append
    add(f"# {symbol} - ICT 3.0 London 08:15 snapshot\n")
    add(f"> Built from the real output of `ict.ict_chart` (revision `{primary.get('source')}`). "
        f"Engine mode: **{ict3.get('mode')}**. `entry_authorized` is preserved verbatim.\n")
    add("## 1. Identification\n")
    add(f"- Instrument: `{primary.get('symbol')}`; frame: `{primary.get('frame')}`; "
        f"time basis: `{primary.get('time_basis')}`")
    add(f"- `asof`: {primary.get('asof')} (MT5 clock) = "
        f"{iso_utc(real_utc(primary.get('asof'), broker_offset))} real UTC")
    add(f"- Last closed bar: {primary.get('latest_closed')} (MT5 clock) = "
        f"{iso_utc(real_utc(primary.get('latest_closed'), broker_offset))} real UTC")
    add(f"- Broker clock offset: `{broker_offset}` s. `asof` and all last-closed epochs below "
        f"are MT5 encoded-clock values; subtract the offset to obtain real UTC.")
    add(f"- Last close by TF: " + ", ".join(
        f"{k}={v} ({iso_utc(v)} MT5 clock)" for k, v in (primary.get("last_closed_by_tf") or {}).items()))
    add(f"- Bias: **{primary.get('bias')}**; status: **{primary.get('status')}**; "
        f"reason: `{primary.get('context_reason')}`\n")
    add("## 2. Structure / liquidity / POI / events\n")
    add("| TF | Regime (engine) |")
    add("|---|---|")
    for frame in PROFILE:
        add(f"| {frame} | {regime.get(frame, 'not exposed')} |")
    add("")
    add(f"- LTF structure: `{json.dumps(primary.get('structure'), ensure_ascii=False, sort_keys=True)}`")
    add(f"- Retest: `{json.dumps(primary.get('retest'), ensure_ascii=False, sort_keys=True)}`")
    add(f"- Liquidity levels: **{len(liquidity['levels'])}**; POI: **{poi['count']}**; "
        f"ICT events: **{events['count']}**.")
    add(f"- Event states: {', '.join(sorted({e.get('current_state') for e in events['events']})) or 'none'}")
    add(f"- Chart objects: `{json.dumps(chart['counts'], sort_keys=True)}`.")
    add("- No per-zone lifecycle flag is invented; the engine does not expose one. "
        "No full OHLC bars are stored.\n")
    add(f"- Source files: `analysis.json`, `poi.json`, `liquidity.json`, `events.json`, "
        f"`chart_objects.json`.")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Coverage / freshness derived from engine output
# --------------------------------------------------------------------------
def symbol_freshness(primary, cutoff):
    """M15 freshness only; higher TFs obey their own close calendar (not stale)."""
    last = primary.get("latest_closed")
    if last is None:
        return "UNAVAILABLE"
    diff = int(cutoff) - int(last)
    return "FRESH" if diff <= STALE_TOLERANCE_SECONDS else "STALE_FEED"


def tf_freshness(tf, last_closed, cutoff):
    if last_closed is None:
        return "NOT_EXPOSED"
    if tf == "M15":
        diff = int(cutoff) - int(last_closed)
        return "FRESH" if diff <= STALE_TOLERANCE_SECONDS else "STALE_FEED"
    return "SCHEDULE_DEPENDENT"


# --------------------------------------------------------------------------
# Validation (everything checked against the generated documents)
# --------------------------------------------------------------------------
def build_validation(*, london_date, cutoff, expected, symbols, exported, stale, unavailable,
                     files, records, coverage, freshness):
    checks = []

    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("cutoff_matches_london_date", cutoff == expected,
          f"cutoff={cutoff}, expected(08:15 {london_date} Europe/London)={expected}")
    check("all_requested_symbols_accounted", len(exported) + len(stale) + len(unavailable) == len(symbols),
          f"requested={len(symbols)} exported={len(exported)} stale={len(stale)} "
          f"unavailable={len(unavailable)}")
    check("no_raw_dump_paths", not any("/raw/" in p or p.endswith(".csv") for p in files),
          "compact bundle must not carry raw OHLC dumps")

    all_auth = [e.get("entry_authorized") for r in records for e in r.get("events", [])]
    check("entry_authorized_preserved_false", all(v is False for v in all_auth),
          f"values={sorted({repr(v) for v in all_auth})}")

    modes = sorted({m for r in records for m in r.get("modes", [])})
    check("mode_observe_only", all(m == EXPECTED_MODE for m in modes) and bool(modes),
          f"modes={modes}")

    poi_docs = [json.loads(files[k].decode("utf-8")) for k in files if k.endswith("/poi.json")]
    lifecycle = [key for doc in poi_docs for row in doc.get("pois", [])
                 for key in row if "lifecycle" in str(key).lower()]
    check("no_lifecycle_invented", not lifecycle, f"unexpected lifecycle keys: {sorted(set(lifecycle))}")

    total = sum(len(lf_normalize(v)) for k, v in files.items() if k != "manifest.json")
    # 25 MB: 33 instruments x 6 compact files, no raw OHLC dumps.
    # The prior forensic bundle was 80 MB with raw dumps; this stays well below
    # GitHub's 100 MB per-file / 5 GB repo limits while preserving every field.
    check("compact_size", total < 25_000_000, f"payload bytes={total}")

    check("coverage_hook_present", isinstance(coverage, dict) and "coverage_by_symbol_tf" in coverage,
          "coverage hooks present")
    check("freshness_hook_present", isinstance(freshness, dict) and "freshness_by_symbol_tf" in freshness,
          "freshness hooks present")

    ok = all(c["passed"] for c in checks)
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "snapshot_id": coverage.get("snapshot_id"),
        "cutoff": int(cutoff), "cutoff_utc": iso_utc(cutoff), "london_date": london_date,
        "checks": checks, "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "note": "latest.json may be updated only when ok is true; main() never updates it automatically.",
    }


# --------------------------------------------------------------------------
# Core export: pure function of inputs -> relpath/bytes map
# --------------------------------------------------------------------------
def build_bundle(engine, *, cutoff, london_date=None, out_dir, symbols=None,
                 generated_at=None, source_repository=SOURCE_REPOSITORY, provider=PROVIDER,
                 broker_offset=0, extra_files=None):
    cutoff = int(cutoff)                      # real UTC cutoff (London 08:15)
    broker_offset = int(broker_offset or 0)
    engine_cutoff = cutoff + broker_offset    # cutoff in MT5 encoded-clock space
    generated_at = int(generated_at) if generated_at is not None else cutoff
    if london_date is None:
        london_date = zoned_iso(cutoff, "Europe/London")[:10]
    expected = expected_cutoff(london_date)
    wanted = list(symbols) if symbols else list(engine.MT5_SYMBOLS)
    # de-duplicate deterministically, preserve first-seen order
    seen, ordered = set(), []
    for s in wanted:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    wanted = ordered

    try:
        settings = engine.config()
    except Exception as exc:
        raise RuntimeError("Cannot load engine settings (no credentials are written): " + sanitize_reason(exc))

    files = dict(extra_files or {})   # e.g. freshness_report.json, hashed with the bundle
    records = []
    coverage_tf = {}
    freshness_tf = {}
    exported, stale, unavailable = [], [], []

    for symbol in wanted:
        results = {}
        try:
            for frame in PROFILE:
                results[frame] = jsonable(engine.ict_chart(settings, symbol, frame, engine_cutoff))
            primary = results[DEFAULT_FRAME]
            if not primary.get("enabled", True):
                unavailable.append({"symbol": symbol, "reason": primary.get("reason") or "ENGINE_DISABLED"})
                continue
        except Exception as exc:
            unavailable.append({"symbol": symbol, "reason": sanitize_reason(exc)})
            continue

        status = symbol_freshness(primary, engine_cutoff)
        folder = "instruments/" + safe_symbol(symbol)

        poi = build_poi(symbol, results, primary)
        liquidity = build_liquidity(primary)
        events = build_events(primary)
        chart = build_chart_objects(results, primary)
        analysis = build_analysis(primary, results, cutoff, broker_offset)

        files[folder + "/analysis.json"] = json_bytes(analysis)
        files[folder + "/analysis.md"] = (
            md_instrument(symbol, primary, poi, liquidity, events, chart, broker_offset)
        ).encode("utf-8")
        files[folder + "/poi.json"] = json_bytes(poi)
        files[folder + "/liquidity.json"] = json_bytes(liquidity)
        files[folder + "/events.json"] = json_bytes(events)
        files[folder + "/chart_objects.json"] = json_bytes(chart)

        last_by_tf = primary.get("last_closed_by_tf", {}) or {}
        coverage_tf[symbol] = {
            tf: {"last_closed": last_by_tf.get(tf),
                 "last_closed_utc": iso_utc(real_utc(last_by_tf.get(tf), broker_offset)),
                 "last_closed_engine_utc": iso_utc(last_by_tf.get(tf)),
                 "present": tf in last_by_tf and last_by_tf.get(tf) is not None}
            for tf in PROFILE
        }
        freshness_tf[symbol] = {
            tf: {"last_closed": last_by_tf.get(tf),
                 "freshness_status": tf_freshness(tf, last_by_tf.get(tf), engine_cutoff)}
            for tf in PROFILE
        }

        modes = set()
        if isinstance((primary.get("ict3", {}) or {}).get("mode"), str):
            modes.add(primary["ict3"]["mode"])
        records.append({
            "symbol": symbol, "status": status, "asof": primary.get("asof"),
            "asof_real_utc": iso_utc(real_utc(primary.get("asof"), broker_offset)),
            "latest_closed": primary.get("latest_closed"),
            "latest_closed_real_utc": iso_utc(real_utc(primary.get("latest_closed"), broker_offset)),
            "last_closed_by_tf": last_by_tf,
            "engine_source": primary.get("source"), "load": (primary.get("ict3", {}) or {}).get("load"),
            "events": events["events"], "modes": sorted(modes),
        })

        if status == "STALE_FEED":
            stale.append({"symbol": symbol, "latest_closed": primary.get("latest_closed"),
                          "latest_closed_utc": iso_utc(primary.get("latest_closed")),
                          "freshness_status": status})
        else:
            exported.append(symbol)

    exported = sorted(exported)
    stale = sorted(stale, key=lambda x: x["symbol"])
    unavailable = sorted(unavailable, key=lambda x: x["symbol"])
    exported_syms = [r["symbol"] for r in records if r["status"] != "STALE_FEED"]

    coverage = {
        "snapshot_id": None, "coverage_by_symbol_tf": coverage_tf,
        "symbols_expected": len(wanted), "symbols_with_engine_data": len(records),
        "profile": list(PROFILE),
        "hook": "coverage_by_symbol_tf[symbol][tf] = {last_closed, last_closed_utc, present}",
    }
    freshness = {
        "snapshot_id": None, "freshness_by_symbol_tf": freshness_tf,
        "cutoff": cutoff, "engine_cutoff": engine_cutoff,
        "broker_clock_offset_seconds": broker_offset,
        "tolerance_seconds": STALE_TOLERANCE_SECONDS,
        "rule": ("M15 freshness compares the engine latest_closed to the engine cutoff "
                 "(real UTC cutoff + broker clock offset). D1/H4/H1 are "
                 "SCHEDULE_DEPENDENT and are never called stale merely for closing before 08:15."),
        "hook": "freshness_by_symbol_tf[symbol][tf] = {last_closed, freshness_status}",
    }

    # Deterministic snapshot id from config only (not wall clock).
    config_identity = json.dumps(
        {"cutoff": cutoff, "date": london_date, "symbols": wanted,
         "broker_offset": broker_offset}, sort_keys=True).encode("utf-8")
    snapshot_id = "london0815_{}_{}_{}".format(
        london_date.replace("-", ""), cutoff, hashlib.sha256(config_identity).hexdigest()[:10])
    coverage["snapshot_id"] = snapshot_id
    freshness["snapshot_id"] = snapshot_id

    validation = build_validation(
        london_date=london_date, cutoff=cutoff, expected=expected, symbols=wanted,
        exported=exported, stale=stale, unavailable=unavailable, files=files,
        records=records, coverage=coverage, freshness=freshness)

    schema_versions = sorted({str((json.loads(files[k + "/events.json"].decode("utf-8"))).get("schema_version"))
                              for k in ["instruments/" + safe_symbol(s) for s in exported_syms]
                              if k + "/events.json" in files})
    modes_all = sorted({m for r in records for m in r["modes"]})

    # data_quality.json: strictly derived from engine output.
    data_quality = {
        "schema_version": BUNDLE_SCHEMA_VERSION, "snapshot_id": snapshot_id,
        "cutoff": cutoff, "cutoff_utc": iso_utc(cutoff),
        "broker_clock_offset_seconds": broker_offset,
        "engine_cutoff": engine_cutoff,
        "engine_cutoff_clock": "MT5 encoded clock (UTC plus broker offset)",
        "bar_count": getattr(engine, "BAR_COUNT", None),
        "profile": list(PROFILE), "stale_tolerance_seconds": STALE_TOLERANCE_SECONDS,
        "per_symbol": {
            r["symbol"]: {
                "status": r["status"], "asof": r["asof"],
                "asof_utc": r.get("asof_real_utc") or iso_utc(r["asof"]),
                "asof_engine_utc": iso_utc(r["asof"]),
                "latest_closed": r["latest_closed"],
                "latest_closed_utc": r.get("latest_closed_real_utc") or iso_utc(r["latest_closed"]),
                "last_closed_by_tf": r["last_closed_by_tf"], "engine_source": r["engine_source"],
                "load": r["load"],
            } for r in sorted(records, key=lambda x: x["symbol"])
        },
        "unavailable": unavailable,
        "note": ("The engine exposes last-closed timestamps, not full OHLC arrays; no raw bar "
                 "dumps are produced. Higher timeframes close on their own calendar."),
    }
    files["data_quality.json"] = json_bytes(data_quality)
    files["validation.json"] = json_bytes(validation)

    # Uniform clock annotation: every derived JSON that carries `asof` gets its
    # real-UTC equivalent, so no reader mistakes MT5 encoded epochs for UTC.
    for rel, raw in list(files.items()):
        if not rel.endswith(".json"):
            continue
        try:
            doc = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        if isinstance(doc, dict) and "asof" in doc:
            doc["broker_clock_offset_seconds"] = broker_offset
            doc["asof_real_utc"] = iso_utc(real_utc(doc.get("asof"), broker_offset))
            files[rel] = json_bytes(doc)

    hashed = {p: v for p, v in files.items() if p != "manifest.json"}
    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "engine_schema_version": schema_versions,
        "snapshot_id": snapshot_id,
        "london_date": london_date,
        "snapshot_cutoff_utc": cutoff,
        "snapshot_cutoff_utc_iso": iso_utc(cutoff),
        "snapshot_cutoff_london": zoned_iso(cutoff, "Europe/London"),
        "snapshot_cutoff_guayaquil": zoned_iso(cutoff, "America/Guayaquil"),
        "broker_clock_offset_seconds": broker_offset,
        "engine_cutoff": engine_cutoff,
        "engine_cutoff_clock": "MT5 encoded clock; real UTC = engine_cutoff - broker_clock_offset_seconds",
        "generated_at_utc": generated_at,
        "generated_at_utc_iso": iso_utc(generated_at),
        "generated_at_basis": "SOURCE_DATE_EPOCH (defaults to cutoff)" if generated_at == cutoff
                              else "explicit --generated-at / ICT3_GENERATED_AT",
        "expected_cutoff_from_date": expected,
        "cutoff_matches_date": cutoff == expected,
        "engine_revision": str(engine.REVISION),
        "engine_mode": modes_all[0] if len(modes_all) == 1 else modes_all,
        "source_repository": source_repository,
        "provider": provider,
        "profile": list(PROFILE),
        "bar_count": getattr(engine, "BAR_COUNT", None),
        "symbols_requested": wanted,
        "symbols_exported": exported,
        "symbols_stale": stale,
        "symbols_unavailable": unavailable,
        "coverage": coverage,
        "freshness": freshness,
        "validation_status": validation["status"],
        "validation_ok": validation["ok"],
        "hash_basis": HASH_BASIS,
        "file_count": len(hashed),
        "total_bytes": sum(len(lf_normalize(v)) for v in hashed.values()),
        "files": [{"path": p, "bytes": len(lf_normalize(hashed[p])), "sha256": sha256_lf(hashed[p])}
                  for p in sorted(hashed)],
    }

    files["snapshot_global.md"] = (
        "# ICT 3.0 London 08:15 snapshot\n\n"
        f"- snapshot_id: `{snapshot_id}`\n"
        f"- London date: `{london_date}`\n"
        f"- cutoff (UTC): `{cutoff}` ({iso_utc(cutoff)})\n"
        f"- cutoff (Europe/London): `{manifest['snapshot_cutoff_london']}`\n"
        f"- cutoff (America/Guayaquil): `{manifest['snapshot_cutoff_guayaquil']}`\n"
        f"- broker clock offset: `{broker_offset}` s; engine cutoff: `{engine_cutoff}` "
        f"({iso_utc(engine_cutoff)} in MT5 encoded clock)\n"
        f"- generated_at (UTC): `{generated_at}` ({iso_utc(generated_at)})\n"
        f"- engine revision: `{manifest['engine_revision']}`; mode: `{manifest['engine_mode']}`\n"
        f"- schema: `{BUNDLE_SCHEMA_VERSION}`; engine schema: `{schema_versions}`\n"
        f"- symbols: requested={len(wanted)}, exported={len(exported)}, "
        f"stale={len(stale)}, unavailable={len(unavailable)}\n"
        f"- validation: **{validation['status']}**\n"
        f"- hashes: SHA-256 over LF-normalized bytes; {manifest['file_count']} files, "
        f"{manifest['total_bytes']} bytes (see `manifest.json`).\n\n"
        "Read `manifest.json` for `coverage_by_symbol_tf` and `freshness_by_symbol_tf`; "
        "per-symbol detail is under `instruments/<SYM>/`. `entry_authorized` and `mode` "
        "are engine values copied verbatim. No lifecycle flags are invented.\n"
    ).encode("utf-8")
    # snapshot_global.md is itself part of the hashed set; recompute manifest hashes.
    hashed["snapshot_global.md"] = files["snapshot_global.md"]
    manifest["file_count"] = len(hashed)
    manifest["total_bytes"] = sum(len(lf_normalize(v)) for v in hashed.values())
    manifest["files"] = [{"path": p, "bytes": len(lf_normalize(hashed[p])), "sha256": sha256_lf(hashed[p])}
                         for p in sorted(hashed)]

    return {"out_dir": Path(out_dir), "files": files, "manifest": manifest,
            "validation": validation, "snapshot_id": snapshot_id}


def write_bundle(bundle):
    """Materialize the bundle; manifest is written last from exact file bytes."""
    out_dir = bundle["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in bundle["files"].items():
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    (out_dir / "manifest.json").write_bytes(json_bytes(bundle["manifest"]))
    return out_dir


def export_snapshot(engine, *, cutoff, london_date=None, out_dir, symbols=None,
                    generated_at=None, source_repository=SOURCE_REPOSITORY, provider=PROVIDER,
                    broker_offset=0, extra_files=None):
    bundle = build_bundle(engine, cutoff=cutoff, london_date=london_date, out_dir=out_dir,
                          symbols=symbols, generated_at=generated_at,
                          source_repository=source_repository, provider=provider,
                          broker_offset=broker_offset, extra_files=extra_files)
    return write_bundle(bundle), bundle


# --------------------------------------------------------------------------
# Explicit latest.json writer -- gated on explicit validation success
# --------------------------------------------------------------------------
def write_latest_json(latest_path, snapshot_rel_path, validation, *, snapshot_id=None,
                      generated_at=None):
    """Update ``latest.json`` ONLY when an explicit validation dict says ok.

    This function is intentionally NOT invoked by ``main()`` or ``export_snapshot``.
    """
    if not isinstance(validation, dict) or validation.get("ok") is not True:
        raise ValueError("refusing to update latest.json: explicit validation success required")
    latest_path = Path(latest_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "status": "VALIDATED",
        "snapshot_id": snapshot_id or validation.get("snapshot_id"),
        "snapshot_rel_path": str(snapshot_rel_path).replace("\\", "/"),
        "generated_at_utc": int(generated_at) if generated_at is not None else None,
        "validation_status": validation.get("status"),
        "note": "Written explicitly after validation; never by the export path itself.",
    }
    latest_path.write_bytes(json_bytes(payload))
    return latest_path


# --------------------------------------------------------------------------
# Offline self-test with synthetic engine output (monkeypatched ict_chart)
# --------------------------------------------------------------------------
def synthetic_engine():
    """Deterministic stand-in engine; no MT5, no credentials, no real repo."""
    def ict_chart(settings, symbol, frame, cutoff=None):
        cutoff = int(cutoff)
        if symbol == "US30":
            return {"enabled": False, "reason": "ICT automático se aplica al universo confirmado de MT5."}
        last = cutoff if symbol != "USDJPY" else cutoff - 3 * 900
        by_tf = {"D1": (cutoff // 86400) * 86400, "H4": (cutoff // 14400) * 14400,
                 "H1": (cutoff // 3600) * 3600, "M15": last}
        mark_id = f"{frame}-{last}-{symbol}-FVG-1"
        event = {
            "event_id": "evt_" + hashlib.sha256((symbol + str(cutoff)).encode()).hexdigest()[:16],
            "symbol": symbol, "session_open": by_tf["D1"], "observed_at": last,
            "state_time": last, "level_name": "PDH", "level": 1.23450, "direction": 1,
            "current_state": "ACCEPTED_BREAK_WAIT_RETEST", "wait_reason": "RETEST_NOT_OBSERVED",
            "pending_evidence": ["RETEST_NOT_OBSERVED"], "entry_authorized": False,
        }
        return {
            "enabled": True, "source": "synthetic-revision", "symbol": symbol, "frame": frame,
            "time_basis": "Reloj MT5 (synthetic)", "asof": cutoff, "latest_closed": last,
            "bias": "BULLISH" if symbol == "EURUSD" else "BEARISH", "status": "OBSERVE",
            "context_reason": "SYNTHETIC", "regime": {"D1": "BULL", "H4": "BULL", "H1": "RANGE", "M15": "BULL"},
            "structure": {"BOS": True}, "retest": {"state": "NONE"},
            "last_closed_by_tf": by_tf,
            "marks": [{"id": mark_id, "tf": frame, "kind": "FVG", "direction": 1,
                       "low": 1.23400, "high": 1.23500, "open": last - 900,
                       "confirmed": last, "touch": None, "related": False}],
            "pois": [],
            "daily_liquidity": {"pdh": 1.23500, "pdl": 1.23000, "source_open": by_tf["D1"],
                                "session_open": by_tf["D1"], "events": []},
            "ict3_breaks": [],
            "ict3": {"schema_version": "0.2-research", "mode": EXPECTED_MODE, "events": [event],
                     "load": {"load_reason": "NOT_REQUESTED_NO_M15_RETEST",
                              "coverage": {"m5_bars_closed": 0, "m1_bars_closed": 0}}},
            "book22": [], "friday_reference": None,
        }

    return SimpleNamespace(
        ict_chart=ict_chart, REVISION="synthetic-revision", PROFILE=PROFILE, BAR_COUNT=550,
        MT5_SYMBOLS=("EURUSD", "GBPJPY", "USDJPY", "US30"),
        CATALOG={"forex": ["EURUSD", "GBPJPY", "USDJPY"], "indices": {"US30": "US30"}},
        config=lambda: {"offline": True}, module=None,
    )


def self_test(verbose=True):
    import tempfile
    cutoff = expected_cutoff("2026-11-23")
    engine = synthetic_engine()
    # Keep all transient writes beside this module (isolated workspace).
    tmp_root = str(Path(__file__).resolve().parent)
    with tempfile.TemporaryDirectory(prefix="ict3_london_selftest_", dir=tmp_root) as tmp:
        a, b = Path(tmp) / "a", Path(tmp) / "b"
        _, bundle_a = export_snapshot(engine, cutoff=cutoff, london_date="2026-11-23", out_dir=a)
        _, bundle_b = export_snapshot(engine, cutoff=cutoff, london_date="2026-11-23", out_dir=b)
        names_a = sorted(str(p.relative_to(a)).replace("\\", "/") for p in a.rglob("*") if p.is_file())
        names_b = sorted(str(p.relative_to(b)).replace("\\", "/") for p in b.rglob("*") if p.is_file())
        assert names_a == names_b, "different file sets"
        for rel in names_a:
            da, db = (a / rel).read_bytes(), (b / rel).read_bytes()
            assert da == db, f"non-idempotent file: {rel}"
        m = bundle_a["manifest"]
        assert m["validation_ok"] is True
        assert m["snapshot_cutoff_london"].startswith("2026-11-23T08:15:00")
        assert m["snapshot_cutoff_guayaquil"].startswith("2026-11-23T03:15:00")
        assert m["engine_mode"] == EXPECTED_MODE
        assert [s["symbol"] for s in m["symbols_stale"]] == ["USDJPY"]
        assert [s["symbol"] for s in m["symbols_unavailable"]] == ["US30"]
        assert set(m["symbols_exported"]) == {"EURUSD", "GBPJPY"}
        # latest.json gating
        try:
            write_latest_json(Path(tmp) / "latest.json", "a", {"ok": False})
        except ValueError:
            pass
        else:
            raise AssertionError("write_latest_json accepted failed validation")
        write_latest_json(Path(tmp) / "latest.json", "snapshots/x", bundle_a["validation"],
                          snapshot_id=m["snapshot_id"])
        if verbose:
            print(f"SELF-TEST PASS: {len(names_a)} files byte-identical across two runs; "
                  f"snapshot_id={m['snapshot_id']}")
    return True


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=os.environ.get("ICT3_ROOT"),
                        help="ICT 3.0 project root (env ICT3_ROOT allowed)")
    parser.add_argument("--cutoff", type=int, default=None, help="causal cutoff, UTC epoch seconds")
    parser.add_argument("--date", dest="london_date", default=None, help="London date YYYY-MM-DD")
    parser.add_argument("--out", default=None, help="snapshot output folder")
    parser.add_argument("--symbols", nargs="*", default=None, help="optional catalog symbols")
    parser.add_argument("--broker-offset-seconds", type=int,
                        default=int(os.environ.get("ICT3_BROKER_OFFSET", "0")),
                        help="MT5 encoded-clock offset versus real UTC, measured at capture time")
    parser.add_argument("--generated-at", type=int,
                        default=(int(os.environ["ICT3_GENERATED_AT"])
                                 if os.environ.get("ICT3_GENERATED_AT") else None),
                        help="override generated_at_utc (defaults to cutoff for reproducibility)")
    parser.add_argument("--self-test", action="store_true", help="offline synthetic self-test")
    args = parser.parse_args(argv)

    if args.symbols:
        flat = []
        for token in args.symbols:
            flat.extend(p.strip() for p in token.split(",") if p.strip())
        args.symbols = flat

    if args.self_test:
        ok = self_test(verbose=True)
        return 0 if ok else 1

    if not args.root:
        parser.error("--root or ICT3_ROOT is required")
    if not args.out:
        parser.error("--out is required")
    if args.cutoff is None and not args.london_date:
        parser.error("provide --cutoff or --date")
    cutoff = args.cutoff if args.cutoff is not None else expected_cutoff(args.london_date)

    engine = load_engine(args.root)
    out_dir, bundle = export_snapshot(
        engine, cutoff=cutoff, london_date=args.london_date, out_dir=args.out,
        symbols=args.symbols, generated_at=args.generated_at,
        broker_offset=args.broker_offset_seconds)
    m = bundle["manifest"]
    print("WROTE", out_dir, flush=True)
    print("BROKER_OFFSET", args.broker_offset_seconds, "engine_cutoff", m["engine_cutoff"], flush=True)
    print("SNAPSHOT", m["snapshot_id"], "cutoff", m["snapshot_cutoff_utc_iso"],
          "london", m["snapshot_cutoff_london"], "guayaquil", m["snapshot_cutoff_guayaquil"], flush=True)
    print("COUNTS", "exported", len(m["symbols_exported"]), "stale", len(m["symbols_stale"]),
          "unavailable", len(m["symbols_unavailable"]), "files", m["file_count"],
          "bytes", m["total_bytes"], "validation", m["validation_status"], flush=True)
    print("NOTE", "latest.json was NOT updated; call write_latest_json explicitly after validation.",
          flush=True)
    return 0 if bundle["validation"]["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
