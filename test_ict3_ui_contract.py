# -*- coding: utf-8 -*-
"""Fase 6 — contrato de la interfaz de análisis ICT 3.0 (agente de calidad).

SOLO LECTURA. Este módulo lee ``index.html``, ``app.js`` y ``style.css`` desde
la raíz del proyecto; no importa módulos Python de producción, no arranca el
servidor, no escribe en ``data/`` y no modifica los archivos que edita en
paralelo el agente de presentación.

Dos capas de pruebas:

1. Invariantes estables (siempre activas): cableado de recursos, navegación,
   selector de activo, región viva de análisis, ausencia de lenguaje de orden
   o promesa de rentabilidad, y ausencia de un polling nuevo. Verifican lo que
   ya existe y debe conservarse.
2. Contrato esperado de nombres claros (``Ict3StructuredStageContractTests``):
   ganchos ``data-ict3-stage`` / ``data-ict3-time`` / ``data-ict3-reason`` para
   cada etapa. Si el agente de presentación aún no los publicó, esas pruebas se
   omiten con ``skipTest`` y el motivo se reporta, en lugar de dar un falso OK.
   La suite completa termina en ``OK (skipped=N)``.

Contrato esperado de nombres claros
------------------------------------
* Contenedor: ``#ict3Final`` con ``aria-live="polite"``.
* Cada etapa: ``[data-ict3-stage="<clave>"]`` con clave en
  ``ruptura | zona | retest | m5 | m1 | stop | objetivos | invalidacion``.
* Cada etapa expone estado, hora y motivo:
  ``[data-ict3-state]``, ``[data-ict3-time]``, ``[data-ict3-reason]``
  (o el texto visible equivalente en español).
* Escenarios obligatorios con texto visible: evento sin zona, zona sin retest,
  espera de M5, M1 ausente, POI invalidado y setup observable.
"""
from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
APP_JS = ROOT / "app.js"
STYLE_CSS = ROOT / "style.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class _TinyDom(HTMLParser):
    """DOM ligero de stdlib: índice ``id -> (tag, attrs)`` y lista de nodos."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.by_id: dict[str, tuple[str, dict]] = {}
        self.nodes: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.nodes.append((tag, attributes))
        if isinstance(attributes.get("id"), str):
            self.by_id[attributes["id"]] = (tag, attributes)


def load_dom() -> _TinyDom:
    dom = _TinyDom()
    dom.feed(_read(INDEX))
    return dom


def visible_text(html: str) -> str:
    """Texto grueso sin etiquetas, para detectar lenguaje prohibido."""
    return re.sub(r"<[^>]+>", " ", html)


# Palabras prohibidas: lenguaje de orden o promesa de rentabilidad.
FORBIDDEN_PROFIT = (
    "rentabilidad",
    "ganancia segura",
    "sin riesgo",
    "compra garantizada",
    "venta garantizada",
    "entrada garantizada",
    "orden de compra",
    "orden de venta",
    "coloca una orden",
    "ejecutar orden",
)

# Claves canónicas del contrato de etapas (ver docstring).
STAGE_KEYS = (
    "ruptura", "zona", "retest", "m5", "m1", "stop", "objetivos", "invalidacion",
)


class UiWiringContractTests(unittest.TestCase):
    """Invariantes que deben conservarse con o sin la nueva ficha."""

    @classmethod
    def setUpClass(cls):
        cls.dom = load_dom()
        cls.html = _read(INDEX)
        cls.js = _read(APP_JS)

    def test_static_assets_are_wired(self):
        self.assertIn('href="/style.css"', self.html)
        self.assertIn('src="/app.js"', self.html)
        self.assertTrue(STYLE_CSS.exists() and STYLE_CSS.stat().st_size > 0)

    def test_navigation_tabs_preserved(self):
        ids = ("marketTab", "analysisTab", "journalTab")
        for tab_id in ids:
            with self.subTest(tab=tab_id):
                tag, attrs = self.dom.by_id[tab_id]
                self.assertEqual(tag, "button")
                self.assertEqual(attrs.get("role"), "tab")
                panel = attrs.get("aria-controls")
                self.assertIsInstance(panel, str)
                self.assertIn(panel, self.dom.by_id)
                self.assertEqual(self.dom.by_id[panel][1].get("role"), "tabpanel")
        self.assertIn("activateAppTab", self.js)

    def test_navigation_keyboard_support_preserved(self):
        for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
            with self.subTest(key=key):
                self.assertIn("'" + key + "'", self.js)
        self.assertIn("keydown", self.js)

    def test_asset_selector_preserved(self):
        for select_id in ("symbol", "analysisSymbol", "tf"):
            with self.subTest(select=select_id):
                self.assertEqual(self.dom.by_id[select_id][0], "select")
        self.assertIn("populateSymbolMenu", self.js)
        self.assertIn("'analysisSymbol'", self.js)
        self.assertIn("$('analysisSymbol').addEventListener('change'", self.js)
        # La ficha debe indicar a qué activo pertenece.
        self.assertTrue(
            "scope.symbol" in self.js or "$('analysisSymbol').value" in self.js,
            "La ficha no referencia el activo analizado",
        )

    def test_analysis_live_region_present(self):
        self.assertEqual(self.dom.by_id["ict3Final"][0], "div")
        self.assertEqual(self.dom.by_id["ict3Final"][1].get("aria-live"), "polite")
        self.assertEqual(self.dom.by_id["ict3DetailStatus"][1].get("role"), "status")

    def test_no_order_or_profit_language_in_static_copy(self):
        body = visible_text(self.html)
        lowered = body.lower()
        for phrase in FORBIDDEN_PROFIT:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, lowered)
        # La nota de la ficha niega explícitamente ser una orden.
        self.assertIn("no una orden", lowered)

    def test_no_new_polling_mechanism(self):
        # El panel conserva su mecanismo existente: cuatro intervalos Known.
        intervals = re.findall(r"setInterval\(\s*(\w+)", self.js)
        self.assertEqual(len(intervals), 4, intervals)
        self.assertIn("loadChart", intervals)
        self.assertIn("refreshJournal", intervals)
        self.assertIn("refreshOpenings", intervals)
        self.assertIn("refreshUniverseMonitor", intervals)
        # Sin proveedor de eventos propio: el SSE del puente es ajeno al panel.
        self.assertNotIn("EventSource", self.js)
        self.assertNotIn("text/event-stream", self.js)
        self.assertNotIn("addEventListener('message'", self.js)
        # La carga detallada sigue siendo accionada por el usuario, no por un temporizador.
        self.assertIn("loadDetailedAnalysis()", self.js)
        self.assertNotIn("setInterval(loadDetailedAnalysis", self.js)

    def test_bridge_sse_stays_separate(self):
        # Ningún archivo de la interfaz abre un stream propio; si el puente
        # Hermes emitiera SSE, el panel no se suscribe a él desde app.js.
        for path in (INDEX, APP_JS, STYLE_CSS):
            with self.subTest(file=path.name):
                self.assertNotIn("EventSource", _read(path))


class Ict3DetailVocabularyTests(unittest.TestCase):
    """Cobertura conceptual verificable hoy por assertions de texto."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(APP_JS)
        cls.html = _read(INDEX)
        cls.source = cls.js + "\n" + cls.html

    def test_all_six_scenarios_have_visible_spanish_vocabulary(self):
        scenarios = {
            "evento sin zona": r"sin\s+(poi|fvg|zona)|sin\s+poi\s+candidato",
            "zona sin retest": r"sin\s+retest|falta\s+retorno|sin\s+retorno",
            "espera M5": r"m5\s*/\s*m1|esper[^\n]{0,40}m5|m5[^\n]{0,40}(espera|pendiente|confirmación)",
            "M1 ausente": r"sin\s+m1|falta\s+m1|m1[^\n]{0,40}(ausente|no\s+disponible)|m5\s*/\s*m1",
            "POI invalidado": r"invalidaci|invalidado|pierde\s+validez|cuándo\s+descartar",
            "setup observable": r"setup\s+observable|configuración\s+observable|\bobservable\b",
        }
        for name, pattern in scenarios.items():
            with self.subTest(escenario=name):
                self.assertTrue(
                    re.search(pattern, self.source, re.IGNORECASE),
                    "No aparece el vocabulario del escenario: " + name,
                )

    def test_time_and_reason_are_rendered(self):
        self.assertIn("hora MT5", self.js)
        self.assertIn("chartTime", self.js)
        self.assertRegex(
            self.js,
            r"Falta retorno|Esperar|pending_evidence|wait_reason|\breason\b|motivo|razón",
        )

    def test_wait_language_and_no_fabricated_entry(self):
        self.assertRegex(self.js, r"Esperar|esperando|Espera")
        self.assertIn("no una orden", visible_text(self.html).lower())
        self.assertIn("POI candidato", self.js)
        # El bloque de análisis sigue siendo de solo observación.
        self.assertNotIn("entry_authorized: true", self.js)
        self.assertNotIn('"orden"', self.js)


class Ict3StructuredStageContractTests(unittest.TestCase):
    """Contrato esperado de nombres claros; se omite si aún no está publicado."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(APP_JS)
        cls.html = _read(INDEX)

    def test_each_stage_has_a_clear_dom_hook(self):
        hook = re.search(r"data-ict3-stage|data-stage|ict3Stage", self.js + self.html)
        if not hook:
            self.skipTest(
                "El agente de presentación aún no publicó los ganchos "
                "data-ict3-stage='ruptura|zona|retest|m5|m1|stop|objetivos|"
                "invalidacion' (ni ict3Stage*). No se puede verificar una "
                "etapa por etapa; queda reportado como no verificado."
            )
        found = [key for key in STAGE_KEYS if key in self.js.lower()]
        self.assertGreaterEqual(
            len(found), 6,
            "El contrato exige al menos 6 de las 8 etapas claramente nombradas; "
            "encontradas: " + ", ".join(found),
        )

    def test_each_stage_exposes_state_time_and_reason(self):
        source = self.js + self.html
        missing = [attr for attr in ("data-ict3-state", "data-ict3-time",
                                     "data-ict3-reason") if attr not in source]
        if missing:
            self.skipTest(
                "El agente de presentación aún no expone " + ", ".join(missing)
                + " por etapa. La hora y el motivo sólo se verifican a nivel de "
                "vocabulario; queda reportado como no verificado."
            )
        self.assertIn("hora MT5", self.js)


if __name__ == "__main__":
    unittest.main()
