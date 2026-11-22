import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from diario import DATA, ROOT, chart, config, journal_path, read_json, save_json, sync, workspace_key
from ict import SYMBOL, ict_chart
from poi_history import date_cutoff, scan_poi_history
from sesiones import OpeningMonitor
from motor_smc.instrumentos import CATALOG, SYMBOL_GROUPS
from motor_smc.servicio import MarketPanel
from motor_smc.avisos import MarketNotices

PORT = 8766
LOCAL = f"127.0.0.1:{PORT}"
MARKS = DATA / "marcajes.json"
OPENINGS = OpeningMonitor()
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8")}


def update_notes(request):
    key = workspace_key(request["symbol"], request["tf"])
    store = read_json(MARKS, {})
    marks = store.setdefault(key, [])
    action = request["action"]
    if action == "add":
        if len(marks) >= 500:
            raise ValueError("Límite de 500 marcajes para este gráfico.")
        kind, first, second = request["kind"], request["first"], request.get("second")
        if kind not in {"POI", "Nivel", "Tendencia", "Idea"}:
            raise ValueError("Herramienta desconocida.")
        if first is None or (second is not None) != (kind in {"POI", "Tendencia"}):
            raise ValueError("Cantidad de puntos inválida.")
        for point in (first, second) if second is not None else (first,):
            if (not isinstance(point["t"], int) or not 0 < point["t"] < 4102444800
                    or not isinstance(point["p"], (float, int)) or not -1e8 < point["p"] < 1e8):
                raise ValueError("Punto de marcaje inválido.")
        marks.append({"id": uuid4().hex, "kind": kind, "first": first, "second": second,
                      "label": str(request.get("label", ""))[:500]})
    elif action == "delete":
        store[key] = [mark for mark in marks if mark["id"] != request["id"]]
        if not store[key]:
            del store[key]
    elif action == "update":
        for mark in marks:
            if mark["id"] == request["id"]:
                mark["label"] = str(request["label"])[:500]
                break
    else:
        raise ValueError("Acción desconocida.")
    save_json(MARKS, store)
    return store


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, content, mime="application/json"):
        encoded = (json.dumps(content, ensure_ascii=False).encode()
                   if mime == "application/json" else content)
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def route(self):
        if self.headers.get("Host") != LOCAL:
            return self.reply(403, {"error": "Usa la dirección local del proyecto."})
        url = urlsplit(self.path)
        if self.command == "GET":
            if url.path in ASSETS:
                file, mime = ASSETS[url.path]
                return self.reply(200, (ROOT / file).read_bytes(), mime)
            if url.path == "/api/market":
                query = parse_qs(url.query)
                symbol = query.get("symbol", [""])[0]
                frame = query.get("tf", [""])[0]
                return self.reply(200, self.server.market.read(symbol, frame))
            if url.path == "/api/market-universe":
                return self.reply(200, self.server.market.universe())
            if url.path in {"/api/chart", "/api/ict"}:
                query = parse_qs(url.query)
                symbol = query.get("symbol", [""])[0]
                frame = query.get("tf", [""])[0]
                if url.path == "/api/chart":
                    return self.reply(200, chart(config(), symbol, frame))
                cutoff = int(query["at"][0]) if "at" in query else None
                if cutoff is not None and not 0 < cutoff < 4102444800:
                    raise ValueError("Corte de revisión inválido.")
                return self.reply(200, ict_chart(config(), symbol, frame, cutoff))
            if url.path == "/api/poi-universe":
                return self.reply(200, CATALOG)
            if url.path == "/api/poi-history":
                query = parse_qs(url.query)
                symbols = query.get("symbol", [])
                group = query.get("group", [None])[0]
                if group is not None:
                    if symbols or group not in SYMBOL_GROUPS:
                        raise ValueError("Selecciona un grupo de MT5 o símbolos explícitos.")
                    symbols = SYMBOL_GROUPS[group]
                if "at" in query and "date" in query:
                    raise ValueError("Indica un solo corte.")
                cutoff = (int(query["at"][0]) if "at" in query else
                          date_cutoff(query["date"][0]) if "date" in query else None)
                summary = query.get("summary") == ["1"]
                return self.reply(200, scan_poi_history(config(), symbols, cutoff, summary=summary))
            if url.path == "/api/journal":
                return self.reply(200, {"journal": read_json(journal_path(config()))})
            if url.path == "/api/openings":
                symbol = parse_qs(url.query).get("symbol", [SYMBOL])[0]
                return self.reply(200, OPENINGS.read(datetime.now(timezone.utc), symbol))
            if url.path == "/api/notes":
                return self.reply(200, read_json(MARKS, {}))
        elif self.command == "POST":
            if self.headers.get("Origin") != f"http://{LOCAL}":
                return self.reply(403, {"error": "La solicitud debe venir del tablero local."})
            if url.path == "/api/sync":
                return self.reply(200, {"journal": sync(config())})
            if url.path == "/api/notes":
                length = int(self.headers.get("Content-Length", 0))
                if not 1 <= length <= 32000 or self.headers.get_content_type() != "application/json":
                    raise ValueError("Solicitud de marcaje inválida.")
                return self.reply(200, update_notes(json.loads(self.rfile.read(length))))
        return self.reply(404, {"error": "Página no encontrada."})

    def safe_route(self):
        try:
            self.route()
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            self.reply(400, {"error": str(error) or "Solicitud inválida."})
        except (OSError, RuntimeError) as error:
            self.reply(503, {"error": str(error)})

    do_GET = safe_route
    do_POST = safe_route


class LocalServer(HTTPServer):
    def __init__(self, address, handler, *, market, notify=True):
        super().__init__(address, handler)
        self.market = market
        self.notify = notify

    def service_actions(self):
        if self.notify:
            OPENINGS.poll(datetime.now(timezone.utc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SMC 3.0 · diario local de MT5")
    parser.add_argument("command", choices=("sync", "serve"))
    args = parser.parse_args()
    if args.command == "sync":
        journal = sync(config())
        print(json.dumps({key: value for key, value in journal.items()
                          if key not in {"deals", "closed"}}, ensure_ascii=False, indent=2))
    else:
        market = MarketPanel(notices=MarketNotices())
        with LocalServer(("127.0.0.1", PORT), Handler, market=market) as server, market:
            print(f"SMC 3.0 en http://{LOCAL}", flush=True)
            server.serve_forever()
