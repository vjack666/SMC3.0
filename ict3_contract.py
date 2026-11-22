"""Diccionario y validador del bloque ``ict3`` expuesto por ``GET /api/ict``.

Fase 5 del plan continuo.  Este modulo es de solo lectura: describe y comprueba
el contrato ya producido por ``ict.ict3_payload`` + ``ict3_confirm.attach_confirmations``.
No lee MT5, no escribe archivos y no anade rutas de orden, cuenta o posicion.

El proposito es que un consumidor nuevo pueda distinguir sin adivinar entre:

* sin retest (``SIN_RETEST``),
* datos ausentes (``DATOS_AUSENTES``) y
* evidencia insuficiente (``EVIDENCIA_INSUFICIENTE``),

mientras los consumidores actuales siguen leyendo ``ict3_breaks`` sin cambios.
"""
from dataclasses import dataclass
from typing import Any

CONTRACT_VERSION = "1.0"
SCHEMA_VERSION = "0.2-research"
MODE = "OBSERVE_ONLY_NO_ORDER"

# Claves que nunca pueden aparecer en un bloque observacional.
FORBIDDEN_KEYS = frozenset({
    "entry", "order", "fill", "lots", "volume", "pnl", "position",
    "cash_value", "balance", "equity", "margin", "ticket", "deal",
})

NUMBER = (int, float)


@dataclass(frozen=True)
class Field:
    """Un campo del contrato: tipo, nulabilidad, unidad, procedencia y sentido."""

    kind: Any
    nullable: bool
    unit: str
    source: str
    meaning: str

    def describe(self):
        kind = self.kind
        name = getattr(kind, "__name__", None)
        if name is None:
            name = "|".join(getattr(item, "__name__", str(item)) for item in kind)
        return {"type": name, "nullable": self.nullable, "unit": self.unit,
                "source": self.source, "meaning": self.meaning}


# --------------------------------------------------------------------------- #
# Diccionario de campos                                                        #
# --------------------------------------------------------------------------- #
TOP_LEVEL: dict[str, Field] = {
    "schema_version": Field(str, False, "-", "interno",
                            "Version del bloque ict3; hoy 0.2-research."),
    "mode": Field(str, False, "-", "interno", "Siempre OBSERVE_ONLY_NO_ORDER."),
    "events": Field(list, False, "-", "daily_break_studies + link_breaks",
                    "Expedientes causales, uno por ruptura aceptada."),
    "load": Field(dict, False, "-", "attach_confirmations",
                  "Estado de la carga M5/M1 bajo demanda."),
}

EVENT: dict[str, Field] = {
    "event_id": Field(str, False, "-", "daily_break_studies",
                      "Identificador determinista de la ruptura."),
    "symbol": Field(str, False, "-", "consulta /api/ict", "Activo consultado."),
    "session_open": Field(int, False, "epoch s", "D1", "Apertura de la sesion diaria."),
    "observed_at": Field(int, False, "epoch s", "M15 cerrada", "Instante en que se conocio el evento."),
    "state_time": Field(int, False, "epoch s", "maquina de estados", "Instante del ultimo estado."),
    "accept_time": Field(int, True, "epoch s", "M15 cerrada", "Cierre que acepto la ruptura."),
    "level_name": Field(str, False, "-", "D1", "PDH o PDL."),
    "level": Field(NUMBER, False, "precio", "D1", "Nivel de liquidez leido."),
    "direction": Field(int, False, "+1/-1", "D1 + M15", "Sentido de la ruptura."),
    "force": Field(dict, False, "-", "cuerpo/rango M15", "Medidas de la vela de senal."),
    "link_state": Field(str, False, "-", "link_breaks", "Resultado de la asociacion causal."),
    "current_state": Field(str, False, "-", "maquina de estados", "Estado causal actual."),
    "retest_at": Field(int, True, "epoch s", "M15 cerrada", "Cierre del retest observado."),
    "poi_candidates": Field(list, False, "-", "FVG/OB ICT 2.0", "Zonas canonicas candidatas."),
    "primary_poi": Field((dict, str), True, "-", "link_breaks",
                         "Zona principal asociada (objeto) o id heredado de zona."),
    "transition_history": Field(list, False, "-", "maquina de estados", "Transiciones con hora y motivo."),
    "window_results": Field(dict, False, "-", "link_breaks", "Resultado por ventana de observacion."),
    "observation_windows": Field(list, False, "-", "link_breaks", "Ventanas comparables usadas."),
    "pending_evidence": Field(list, False, "-", "motor", "Evidencia que todavia falta; nunca se inventa."),
    "wait_reason": Field(str, False, "-", "motor", "Union de pending_evidence o OBSERVATION_ONLY."),
    "entry_authorized": Field(bool, False, "-", "politica", "Siempre false."),
    "mode": Field(str, False, "-", "politica", "Siempre OBSERVE_ONLY_NO_ORDER."),
    "confirmation_state": Field(str, False, "-", "M5/M1", "WAIT_M5_M1_CONFIRMATION o M5_STRUCTURE_CONFIRMED."),
    "defense_at": Field(int, True, "epoch s", "M5 cerrada", "Cierre M5 de la primera defensa."),
    "m5_structure_kind": Field(str, True, "BOS/CHOCH/MSS", "M5 cerrada", "Estructura M5 confirmada por cierre."),
    "m5_structure_at": Field(int, True, "epoch s", "M5 cerrada", "Cierre de la vela de ruptura M5."),
    "m1_structure_kind": Field(str, True, "BOS/CHOCH/MSS", "M1 cerrada", "Corroboracion M1, nunca sustituto de M5."),
    "m1_structure_at": Field(int, True, "epoch s", "M1 cerrada", "Cierre de la vela de ruptura M1."),
    "stop_basis": Field(str, False, "-", "swing causal", " Autoridad del stop estructural informativo."),
    "stop_price": Field(NUMBER, True, "precio", "swing causal", "Precio informativo del stop; no es una entrada."),
    "stop_observed_at": Field(int, True, "epoch s", "swing causal", "Instante en que el pivote era conocible."),
    "target_policy_status": Field(str, False, "-", "liquidez conocida", "Estado de la politica TP1>=3R / TP2>=5R."),
    "target_price": Field(NUMBER, True, "precio", "liquidez conocida", "Liquidez conocida mas cercana."),
    "target_liquidity": Field(list, False, "-", "M5/M1 cerradas", "Niveles {kind, price, observed_at}."),
}

LOAD: dict[str, Field] = {
    "m5_loaded": Field(bool, False, "-", "M5 cerradas", "Existe al menos una vela M5 cerrada <= cutoff."),
    "m1_loaded": Field(bool, False, "-", "M1 cerradas", "Existe al menos una vela M1 cerrada <= cutoff."),
    "last_closed_m5": Field(int, True, "epoch s", "M5 cerradas", "Ultimo cierre M5 observable."),
    "last_closed_m1": Field(int, True, "epoch s", "M1 cerradas", "Ultimo cierre M1 observable."),
    "coverage": Field(dict, False, "-", "M5/M1 cerradas", "Conteo y primeros cierres observados."),
    "load_reason": Field(str, False, "-", "carga bajo demanda", "Motivo de carga o espera."),
}

COVERAGE: dict[str, Field] = {
    "m5_bars_closed": Field(int, False, "velas", "M5 cerradas", "Velas M5 usadas."),
    "m1_bars_closed": Field(int, False, "velas", "M1 cerradas", "Velas M1 usadas."),
    "m5_first_closed": Field(int, True, "epoch s", "M5 cerradas", "Cierre M5 mas antiguo usado."),
    "m1_first_closed": Field(int, True, "epoch s", "M1 cerradas", "Cierre M1 mas antiguo usado."),
    "events_requested": Field(int, False, "eventos", "maquina de estados", "Eventos en RETESTING_POI que pidieron carga."),
}

TRANSITION: dict[str, Field] = {
    "from": Field(str, False, "-", "maquina de estados", "Estado anterior."),
    "to": Field(str, False, "-", "maquina de estados", "Estado nuevo."),
    "at": Field(int, False, "epoch s", "vela cerrada", "Instante de la transicion."),
    "reason": Field(str, False, "-", "motor", "Motivo legible de la transicion."),
}

LIQUIDITY: dict[str, Field] = {
    "kind": Field(str, False, "BROKEN_LEVEL/M5_SWING/M1_SWING", "estructura", "Tipo de liquidez."),
    "price": Field(NUMBER, False, "precio", "estructura", "Precio de la liquidez."),
    "observed_at": Field(int, False, "epoch s", "estructura", "Instante en que era conocible."),
}

CATALOG = {
    "contract_version": CONTRACT_VERSION,
    "schema_version": SCHEMA_VERSION,
    "mode": MODE,
    "sections": {
        "ict3": TOP_LEVEL, "event": EVENT, "load": LOAD,
        "coverage": COVERAGE, "transition": TRANSITION, "liquidity": LIQUIDITY,
    },
}

# La evidencia M5/M1 es un subobjeto todo-o-nada: no existe para eventos que
# nunca entraron en RETESTING_POI, y aparece completa para los que si entraron.
CONFIRMATION_FIELDS = frozenset({
    "confirmation_state", "defense_at", "m5_structure_kind", "m5_structure_at",
    "m1_structure_kind", "m1_structure_at", "stop_basis", "stop_price",
    "stop_observed_at", "target_policy_status", "target_price", "target_liquidity",
})


def _event_fields(event):
    if isinstance(event, dict) and CONFIRMATION_FIELDS.intersection(event):
        return EVENT
    return {key: field for key, field in EVENT.items()
            if key not in CONFIRMATION_FIELDS}

# Campos del contrato anterior que se conservan sin cambio para clientes actuales.
LEGACY_BREAK_FIELDS = (
    "event_id", "session_open", "source_open", "level_name", "level", "direction",
    "signal_open", "signal_close", "body_ratio", "body_multiple", "close_extension",
    "close_location", "strong_body", "strong_range", "strong_extension", "strong",
    "state", "observed_at", "state_time", "accept_time", "accept_open", "failure_time",
)

# Casos de espera que un consumidor debe poder distinguir.
WAIT_CASES = {
    "SIN_RETEST": {
        "description": "Ruptura aceptada todavia sin retest observable.",
        "wait_reason": "RETEST_NOT_OBSERVED",
        "load_reason": "NOT_REQUESTED_NO_M15_RETEST",
    },
    "DATOS_AUSENTES": {
        "description": "No hay velas M5/M1 cerradas utilizables al corte.",
        "wait_reason": "M5_M1_CONFIRMATION_NOT_LOADED",
        "load_reason": ("LOWER_SOURCE_UNAVAILABLE", "LOWER_SOURCE_MALFORMED",
                        "NO_CLOSED_M5_BARS_AT_CUTOFF", "M1_BARS_UNAVAILABLE_M5_USED"),
    },
    "EVIDENCIA_INSUFICIENTE": {
        "description": "Datos cargados, pero falta defensa, estructura, stop o liquidez.",
        "wait_reason": "M5_M1_CONFIRMATION_NOT_COMPLETE",
        "load_reason": "M5_M1_LOADED",
    },
}


def describe():
    """Devuelve el catalogo en tipos JSON (util para documentacion y pruebas)."""
    return {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "forbidden_keys": sorted(FORBIDDEN_KEYS),
        "legacy_break_fields": list(LEGACY_BREAK_FIELDS),
        "confirmation_fields": sorted(CONFIRMATION_FIELDS),
        "wait_cases": WAIT_CASES,
        "sections": {
            name: {key: field.describe() for key, field in fields.items()}
            for name, fields in CATALOG["sections"].items()
        },
    }


def _type_ok(value, field):
    if value is None:
        return field.nullable
    if field.kind is bool:
        return isinstance(value, bool)
    if field.kind is NUMBER:
        return isinstance(value, NUMBER) and not isinstance(value, bool)
    if isinstance(field.kind, tuple):
        return isinstance(value, field.kind) and not isinstance(value, bool)
    return isinstance(value, field.kind) and not isinstance(value, bool)


def _check_section(node, fields, label, issues):
    if not isinstance(node, dict):
        issues.append(f"{label}: esperado objeto, get {type(node).__name__}")
        return
    for key, field in fields.items():
        if key not in node:
            issues.append(f"{label}.{key}: campo ausente")
        elif not _type_ok(node[key], field):
            issues.append(f"{label}.{key}: tipo o nulabilidad invalida")
    for key in node:
        if key in FORBIDDEN_KEYS:
            issues.append(f"{label}.{key}: clave prohibida")


def _check_time(value, label, cutoff, issues):
    if value is not None and cutoff is not None:
        if not isinstance(value, int) or isinstance(value, bool) or value > cutoff:
            issues.append(f"{label}: instante posterior al corte")


def validate(block, *, cutoff=None):
    """Comprueba un bloque ``ict3`` completo y devuelve lista de incidencias.

    ``cutoff`` debe ser el MISMO instante con que se construyó el bloque. El
    productor usa dos relojes (ver ``ict.ict_chart`` / ``ict3_confirm``):

    1. Reloj M15: ``result['asof']`` = ``decision_epoch``; ancla la snapshot
       diaria y el contrato base. Con MT5 stale es el último cierre M15.
    2. Reloj de pared: ``int(time.time())``; se pasa a
       ``attach_confirmations`` y filtra M5/M1 con ``closed <= cutoff``.

    Por regla causal, ``load.last_closed_m5``, ``load.last_closed_m1`` y
    ``target_liquidity[].observed_at`` pertenecen al reloj 2: son ``<=`` ese
    cutoff de construcción y NO son velas futuras, aunque superen el ancla M15
    del reloj 1 (el comentario de ``analyze_cached`` lo permite expresamente:
    "M1/M5 may show later closed formations without altering the daily
    snapshot"). Pasar el ``asof`` M15 como ``cutoff`` mezcla dos relojes y
    produce falsos "instante posterior al corte" en esos tres campos: en US30
    fueron 4 incidencias (2 ``liquidez.observed_at``, ``last_closed_m5`` y
    ``last_closed_m1``). Validado con el corte de construcción, el mismo bloque
    da 0 incidencias. Evidencia ejecutable: ``test_ict3_cutoff_asof.py`` y
    ``docs/ict3/CUTOFF_ASOF_REGLA_CAUSAL.md``. Esta docstring no cambia el
    comportamiento del validador.
    """
    issues = []
    if not isinstance(block, dict):
        return ["ict3: esperado objeto, get " + type(block).__name__]
    _check_section(block, TOP_LEVEL, "ict3", issues)
    if block.get("schema_version") not in (None, SCHEMA_VERSION):
        issues.append("ict3.schema_version: version desconocida")
    if block.get("mode") not in (None, MODE):
        issues.append("ict3.mode: politica inesperada")

    for event in block.get("events") or []:
        label = "ict3.event:" + str(event.get("event_id", "?"))
        _check_section(event, _event_fields(event), label, issues)
        if event.get("entry_authorized") is not False:
            issues.append(label + ".entry_authorized: debe ser false")
        if event.get("mode") not in (None, MODE):
            issues.append(label + ".mode: politica inesperada")
        for key in ("observed_at", "state_time", "retest_at", "defense_at",
                    "m5_structure_at", "m1_structure_at", "stop_observed_at"):
            _check_time(event.get(key), label + "." + key, cutoff, issues)
        for item in event.get("target_liquidity") or []:
            _check_section(item, LIQUIDITY, label + ".liquidez", issues)
            _check_time(item.get("observed_at"), label + ".liquidez.observed_at", cutoff, issues)
        for step in event.get("transition_history") or []:
            _check_section(step, TRANSITION, label + ".transicion", issues)
            _check_time(step.get("at"), label + ".transicion.at", cutoff, issues)

    load = block.get("load")
    if isinstance(load, dict):
        _check_section(load, LOAD, "ict3.load", issues)
        _check_section(load.get("coverage"), COVERAGE, "ict3.load.coverage", issues)
        for key in ("last_closed_m5", "last_closed_m1"):
            _check_time(load.get(key), "ict3.load." + key, cutoff, issues)
    return issues


def assert_valid(block, *, cutoff=None):
    """Lanza AssertionError si el bloque no cumple el contrato."""
    issues = validate(block, cutoff=cutoff)
    if issues:
        raise AssertionError("; ".join(issues))
    return True


def classify_wait(block):
    """Clasifica la espera de un evento para consumidores y tipos de interfaz."""
    load = block.get("load") or {}
    reason = str(load.get("load_reason") or "")
    events = block.get("events") or []
    if reason == "NOT_REQUESTED_NO_M15_RETEST" or any(
            event.get("current_state") == "ACCEPTED_BREAK_WAIT_RETEST"
            for event in events):
        return "SIN_RETEST"
    if reason.startswith("LOWER_SOURCE_") or reason in (
            "NO_CLOSED_M5_BARS_AT_CUTOFF", "M1_BARS_UNAVAILABLE_M5_USED"):
        return "DATOS_AUSENTES"
    for event in events:
        pending = event.get("pending_evidence") or []
        if "RETEST_NOT_OBSERVED" in pending:
            return "SIN_RETEST"
        if "M5_M1_CONFIRMATION_NOT_LOADED" in pending:
            return "DATOS_AUSENTES"
        if pending:
            return "EVIDENCIA_INSUFICIENTE"
    return "SIN_ESPERA"


__all__ = [
    "CONTRACT_VERSION", "SCHEMA_VERSION", "MODE", "FORBIDDEN_KEYS", "Field",
    "TOP_LEVEL", "EVENT", "LOAD", "COVERAGE", "TRANSITION", "LIQUIDITY",
    "CATALOG", "CONFIRMATION_FIELDS", "LEGACY_BREAK_FIELDS", "WAIT_CASES", "describe", "validate",
    "assert_valid", "classify_wait",
]
