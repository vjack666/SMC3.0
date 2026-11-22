# -*- coding: utf-8 -*-
"""Revisión 2b75b99c: semántica de ``cutoff=asof`` en ``ict3_contract.validate``.

Aísla las cuatro incidencias observadas en US30 y deja constancia ejecutable de
la regla causal que las explica: el bloque se construye con **dos relojes**.

* Reloj M15 (``result['asof']`` / ``decision_epoch``): ancla la instantánea
  diaria y el contrato base. Con MT5 stale queda en el último cierre M15.
* Reloj de pared (``int(time.time())`` en ``ict_chart``): se pasa a
  ``attach_confirmations`` y filtra M5/M1. Por eso ``last_closed_m5``,
  ``last_closed_m1`` y ``target_liquidity[].observed_at`` pueden ser más
  recientes que el ancla M15 sin ser velas futuras: todos son ``<=`` el
  ``cutoff`` con el que se construyó el bloque.

Validar con el ancla M15 cuando el bloque se construyó con el reloj de pared
mezcla ambos relojes y produce falsos "instante posterior al corte" en esos
tres campos. Validar con el MISMO corte de construcción da 0 incidencias.

Sin MT5, sin credenciales y sin escrituras en ``data/``: usa los mismos
generadores deterministas que el resto de la suite.
"""
import copy
import unittest

from ict3_contract import validate
from test_ict3_confirm import bullish_bars, m1_bullish_bars, run
from test_ict3_contract_dictionary import CUTOFF, complete_event

# Ancla M15 del fixture: la mayor marca temporal del expediente base. Es el
# equivalente determinista del ``asof`` stale servido por /api/ict.
STALE_ASOF = 1_001_400
# Cortes "frescos" del reloj usado por attach_confirmations, todos <= CUTOFF.
M1_FRESH = 1_002_000
LIQ_FRESH = 1_002_500
BUILD_CUTOFF = CUTOFF  # 1_003_800


def historical_block():
    """Bloque válido construido y validado con un único corte explícito."""
    return run([complete_event()], bullish_bars(), m1_bullish_bars(),
               BUILD_CUTOFF)["ict3"]


def us30_two_clock_block():
    """Fixture controlado con la forma exacta de las 4 incidencias de US30.

    Solo se ajustan los tres campos que pertenecen al reloj M5/M1: dos
    niveles de liquidez y los dos últimos cierres M5/M1. Todos siguen siendo
    ``<= BUILD_CUTOFF``; ninguno es dato futuro respecto al reloj que los
    produjo. El resto del expediente se deja intacto.
    """
    block = copy.deepcopy(historical_block())
    liquidity = block["events"][0]["target_liquidity"]
    liquidity[2]["observed_at"] = LIQ_FRESH
    block["load"]["last_closed_m1"] = M1_FRESH
    return block


class CutoffAsOfContractTests(unittest.TestCase):
    def test_historical_payload_has_zero_issues_at_its_own_cutoff(self):
        """La salida exigida: 0 incidencias para un payload histórico válido."""
        self.assertEqual(validate(historical_block(), cutoff=BUILD_CUTOFF), [])

    def test_four_us30_incidences_are_isolated(self):
        """Las 4 incidencias son 2 liquidez + last_closed_m5 + last_closed_m1."""
        issues = validate(us30_two_clock_block(), cutoff=STALE_ASOF)
        self.assertEqual(len(issues), 4, issues)
        counts = (
            sum("liquidez.observed_at" in item for item in issues),
            sum("load.last_closed_m5" in item for item in issues),
            sum("load.last_closed_m1" in item for item in issues),
        )
        self.assertEqual(counts, (2, 1, 1), issues)
        allowed = ("liquidez.observed_at", "load.last_closed_m5",
                   "load.last_closed_m1")
        self.assertTrue(all(any(key in item for key in allowed)
                            for item in issues), issues)

    def test_flagged_instants_are_not_future_data_in_build_clock(self):
        """Regla causal: todo lo marcado es <= al corte que construyó el bloque."""
        block = us30_two_clock_block()
        issues = validate(block, cutoff=STALE_ASOF)
        self.assertTrue(issues)
        flagged = [liq["observed_at"]
                   for liq in block["events"][0]["target_liquidity"]
                   if liq["observed_at"] > STALE_ASOF]
        flagged += [value for value in (block["load"]["last_closed_m5"],
                                        block["load"]["last_closed_m1"])
                    if value > STALE_ASOF]
        self.assertEqual(len(flagged), len(issues))
        self.assertTrue(all(value <= BUILD_CUTOFF for value in flagged))
        self.assertEqual(validate(block, cutoff=BUILD_CUTOFF), [])


if __name__ == "__main__":
    unittest.main()
