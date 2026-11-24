"""Orquestador diario del snapshot ICT 3.0 de Londres +15m.

Secuencia estricta:
  1. resolve_cutoff (Europe/London, IANA, DST-safe)
  2. freshness real de MT5 + reloj del broker
  3. exportación compacta con offset del broker aplicado
  4. validación local (incluye invariantes y no look-ahead)
  5. commit + push SOLO del snapshot
  6. verificación remota por API
  7. latest.json SOLO tras verificación válida, con commit propio

Sin publicación si cualquier paso falla. Sin credenciales en logs.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import freshness           # noqa: E402
import london_window       # noqa: E402
import publish_london      # noqa: E402
import export_london       # noqa: E402

BASE = "reports/ict3_london"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_pytest_invariants():
    tests_dir = HERE / "tests"
    if not tests_dir.is_dir():
        return {"ok": False, "reason": "falta carpeta tests"}
    env = dict(os.environ)
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", str(tests_dir)],
                          capture_output=True, text=True, env=env, cwd=str(tests_dir))
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
    return {"ok": proc.returncode == 0, "tail": tail}


def build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default=os.environ.get("ICT3_ROOT"), help="raíz del repositorio")
    p.add_argument("--date", default=None, help="fecha London YYYY-MM-DD (default: hoy en London)")
    p.add_argument("--offset", type=int, default=None,
                   help="offset del reloj MT5 en segundos (default: medirlo en vivo)")
    p.add_argument("--symbols", default=None, help="lista separada por comas (default: catálogo)")
    p.add_argument("--no-publish", action="store_true", help="generar y validar sin push")
    p.add_argument("--force", action="store_true", help="permitir regenerar un snapshot existente")
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    if not args.repo:
        raise SystemExit("--repo o ICT3_ROOT es obligatorio")
    repo = Path(args.repo).resolve()
    if not (repo / ".git").is_dir():
        raise SystemExit("la ruta no es un repositorio git: " + str(repo))

    london_date = args.date or datetime.now(london_window._zone("Europe/London")).strftime("%Y-%m-%d")
    cutoff_info = london_window.resolve_cutoff(london_date)
    cutoff = int(cutoff_info["cutoff_utc_epoch"])
    if not cutoff_info["is_london_open_day"]:
        raise SystemExit("fecha no hábil en Londres: " + london_date)

    # DST-safe guard for the two scheduled triggers (07:20 and 08:20 UTC).
    # In BST the early trigger is already past 08:15 London; in GMT it is not.
    now_london = datetime.now(london_window._zone("Europe/London"))
    if (now_london.strftime("%Y-%m-%d") == london_date
            and (now_london.hour * 60 + now_london.minute) < 8 * 60 + 15):
        print("TOO_EARLY", now_london.isoformat(), "cutoff local 08:15 no alcanzado", flush=True)
        return 3

    snapshot_dir = repo / BASE / "snapshots" / london_date / "london_0815"
    if snapshot_dir.exists() and not args.force:
        raise SystemExit("el snapshot ya existe; usa --force para regenerar: " + str(snapshot_dir))

    log = {"started_at": now_iso(), "date": london_date, "cutoff": cutoff,
           "cutoff_london": cutoff_info["cutoff_london_iso"],
           "cutoff_guayaquil": cutoff_info["cutoff_guayaquil_iso"],
           "steps": []}

    def step(name, status, detail=None):
        record = {"step": name, "status": status, "at": now_iso()}
        if detail is not None:
            record["detail"] = detail
        log["steps"].append(record)
        print(name, status, json.dumps(detail, ensure_ascii=False)[:400] if detail else "", flush=True)

    # --- P1: frescura y reloj ---
    mt5 = freshness.connect_mt5()
    try:
        symbols = ([s.strip() for s in args.symbols.split(",") if s.strip()]
                   if args.symbols else None)
        if symbols is None:
            found = mt5.symbols_get()
            # catálogo real del motor, no todos los símbolos del terminal
            sys.path.insert(0, str(repo))
            from motor_smc.instrumentos import MT5_SYMBOLS
            symbols = list(MT5_SYMBOLS)
        fresh = freshness.build_report(
            mt5, cutoff, symbols, max_bars=5000, interpretation="compensate",
            clock_offset_override=args.offset,
            clock_source="ticks" if args.offset is None else "operator_override")
    finally:
        mt5.shutdown()
    offset = int(fresh["broker_clock_offset_seconds"])
    log["broker_clock_offset_seconds"] = offset
    step("freshness", "ok", {"offset": offset, "symbols": len(symbols),
                              "statuses": sorted({v.get("freshness_status")
                                                  for s in fresh["results"].values()
                                                  for v in s.values()
                                                  if isinstance(v, dict)})})
    if offset == 0 and args.offset is None:
        src = (fresh.get("broker_clock") or {}).get("source")
        raise SystemExit(
            "reloj del broker midido como 0 s (fuente=" + str(src) + "); "
            "esto produciria un snapshot dos horas atrasado. "
            "Verifica MT5 o pasa --offset 0 explicitamente si es correcto.")
    if offset < 0 or offset > 21600:
        raise SystemExit("offset del broker fuera de rango plausible: " + str(offset))

    # --- P2/P3: exportación ---
    engine = export_london.load_engine(str(repo))
    extra = {"freshness_report.json": export_london.json_bytes(fresh)}
    _, bundle = export_london.export_snapshot(
        engine, cutoff=cutoff, london_date=london_date, out_dir=str(snapshot_dir),
        symbols=symbols, broker_offset=offset, extra_files=extra)
    manifest = bundle["manifest"]
    validation = bundle["validation"]
    step("export", "ok" if validation["ok"] else "FAIL",
         {"snapshot_id": manifest["snapshot_id"], "files": manifest["file_count"],
          "validation": validation["status"]})
    if not validation["ok"]:
        raise SystemExit("validación del bundle fallida; no se publica")

    # --- P5: invariantes ---
    inv = run_pytest_invariants()
    step("invariants", "ok" if inv["ok"] else "FAIL", inv.get("tail"))
    if not inv["ok"]:
        raise SystemExit("tests de invariantes fallidos; no se publica")

    write_json(snapshot_dir / "run_log.json", log)
    # run_log.json se escribe después del manifest: se documenta como externo al hash.
    manifest["run_log_note"] = "run_log.json se genera tras el hash y no está incluido en files[]."
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")

    if args.no_publish:
        step("publish", "SKIPPED", {"reason": "--no-publish"})
        return 0

    # --- P3: publicación remota del snapshot únicamente ---
    rel_snapshot = snapshot_dir.relative_to(repo).as_posix()
    sha = publish_london.push_folder(
        str(repo), rel_snapshot,
        "docs(ict3): snapshot Londres +15m " + london_date + " (" + manifest["snapshot_id"] + ")")
    step("push", "ok", {"sha": sha})

    result = publish_london.verify(str(repo), rel_snapshot, sha)
    step("remote_verify", "ok" if result["ok"] else "FAIL",
         {"files_checked": result["files_checked"], "errors": result["errors"][:5],
          "sha": sha})
    if not result["ok"]:
        raise SystemExit("verificación remota fallida; latest.json no se actualiza")

    # --- latest.json: solo tras publicación válida ---
    latest_path = repo / BASE / "latest.json"
    if latest_path.exists() and read_json(latest_path).get("london_date", "") > london_date:
        step("latest", "SKIPPED", {"reason": "a newer validated snapshot is already indexed"})
        return 0
    latest = {
        "status": "VALIDATED",
        "validation_status": validation["status"],
        "files_verified": result["files_checked"],
        "snapshot_id": manifest["snapshot_id"],
        "london_date": london_date,
        "snapshot_cutoff_utc": cutoff,
        "snapshot_cutoff_utc_iso": manifest["snapshot_cutoff_utc_iso"],
        "snapshot_cutoff_london": manifest["snapshot_cutoff_london"],
        "snapshot_cutoff_guayaquil": manifest["snapshot_cutoff_guayaquil"],
        "path": rel_snapshot,
        "manifest": rel_snapshot + "/manifest.json",
        "verified_commit": sha,
        "verified_at_utc": now_iso(),
        "engine_mode": manifest["engine_mode"],
        "broker_clock_offset_seconds": offset,
    }
    write_json(latest_path, latest)
    publish_london.push_folder(
        str(repo), [BASE + "/latest.json", rel_snapshot + "/run_log.json"],
        "docs(ict3): actualiza latest.json al snapshot validado " + london_date)
    step("latest", "ok", {"path": BASE + "/latest.json", "snapshot_id": manifest["snapshot_id"]})

    print("RESULT", json.dumps({"ok": True, "sha": sha, "snapshot_id": manifest["snapshot_id"],
                                "cutoff": cutoff, "offset": offset}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
