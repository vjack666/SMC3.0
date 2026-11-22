"""Causal ICT 3.0 observation simulation using the maximum MT5 history returned.

This is not a backtest: it does not model fills, P&L, orders, or execution.
It replays closed candles only to measure how the proposed reading states behave
across the 26 confirmed Forex symbols.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

import MetaTrader5 as mt5

from diario import checked, config, connection
from ict import SECONDS, closed_frame, daily_break_studies
from motor_smc.instrumentos import FOREX_SYMBOLS

# Practical upper request for the connected terminal. MT5 may return fewer
# bars when its local history or "Max bars in chart" setting is smaller.
M15_REQUEST = 5_000
D1_REQUEST = 2_000
OUTPUT = Path(__file__).resolve().parent / "docs" / "research" / "ICT3_SIMULACION_26_PARES.md"


def _rows(rates):
    return [(int(row["time"]), float(row["open"]), float(row["high"]),
             float(row["low"]), float(row["close"])) for row in rates]


def _date(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def simulate_symbol(symbol):
    info = checked(mt5.symbol_info(symbol), f"símbolo {symbol}")
    d1_rates = checked(mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, D1_REQUEST),
                       f"D1 {symbol}")
    m15_rates = checked(mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, M15_REQUEST),
                        f"M15 {symbol}")
    d1 = _rows(d1_rates)
    m15_raw = _rows(m15_rates)
    if len(d1) < 3 or len(m15_raw) < 30:
        raise RuntimeError("historial insuficiente")
    m15 = closed_frame(m15_raw, "M15")
    cutoff = int(m15["closed"].iloc[-1])
    studies = daily_break_studies(d1, m15, cutoff, symbol=symbol, digits=info.digits)
    states = Counter(item["state"] for item in studies)
    strong = [item for item in studies if item.get("strong")]
    accepted = [item for item in studies if item["state"] == "ACCEPTED_BREAK_WAIT_RETEST"]
    return {
        "symbol": symbol, "digits": info.digits, "d1_bars": len(d1),
        "m15_bars": len(m15_raw), "m15_closed": len(m15),
        "first_d1": _date(d1[0][0]), "last_d1": _date(d1[-2][0]),
        "first_m15": _date(m15_raw[0][0]), "last_m15_closed": _date(cutoff),
        "studies": len(studies), "states": dict(states),
        "strong_candidates": len(strong), "accepted_breaks": len(accepted),
        "strong_accepted": sum(1 for item in accepted if item.get("strong")),
        "strong_examples": strong[-5:],
    }


def render(results, generated_at):
    total = Counter()
    for result in results:
        total.update(result["states"])
    lines = [
        "# ICT 3.0 — Simulación causal de observación en 26 pares",
        "",
        f"Generado: {generated_at}",
        "",
        "> Esta ejecución no es un backtest. No calcula rentabilidad, fills, órdenes,",
        "> lotaje ni curva de capital. Solo reinterpreta velas cerradas de MT5 para",
        "> entrenar/inspeccionar la máquina de estados propuesta para rupturas de",
        "> PDH/PDL.",
        "",
        "## Alcance de datos",
        "",
        f"- Símbolos: {len(results)} pares Forex confirmados.",
        f"- Solicitud máxima del script: {M15_REQUEST:,} velas M15 y {D1_REQUEST:,} velas D1 por símbolo.",
        "- El terminal puede devolver menos barras según su historial local; el informe conserva la cobertura real.",
        "- Solo se usan prefijos hasta la última M15 cerrada de cada símbolo.",
        "- Fuente: cuenta MT5 configurada en `data/cuenta.json`; no se envían solicitudes de trading.",
        "",
        "## Estados agregados",
        "",
        "| Estado | Conteo |",
        "|---|---:|",
    ]
    for state, count in sorted(total.items()):
        lines.append(f"| `{state}` | {count} |")
    lines += ["", "## Cobertura por símbolo", "", "| Símbolo | D1 | M15 solicitadas | M15 cerradas | Rango D1 | Rango M15 | Estudios | Fuertes | Aceptadas |", "|---|---:|---:|---:|---|---|---:|---:|---:|"]
    for result in results:
        lines.append(f"| {result['symbol']} | {result['d1_bars']:,} | {result['m15_bars']:,} | {result['m15_closed']:,} | {result['first_d1']} → {result['last_d1']} | {result['first_m15']} → {result['last_m15_closed']} | {result['studies']} | {result['strong_candidates']} | {result['strong_accepted']} |")
    lines += ["", "## Lectura de resultados", "", "- `BREAK_CANDIDATE` es un primer cierre fuera del PDH/PDL aún sin aceptación.", "- `FAILED_BREAK` vuelve a separar ruptura fallida de sweep/ruptura sostenida.", "- `ACCEPTED_BREAK_WAIT_RETEST` confirma dos cierres consecutivos fuera; no es una entrada.", "- La simulación no promueve una ruptura a setup si faltan POI, retest o stop estructural.", "- Una muestra grande de aceptadas fuertes sin retest debe etiquetarse como `EXPANSION_NO_ENTRY`, no como oportunidad perdida imputable al motor.", "", "## EURAUD y el caso de estudio", "", "El caso EURAUD del 20 de noviembre de 2026 queda documentado en `docs/ict3/01_RUPTURA_FUERTE_LIQUIDEZ_DIARIA.md`. La simulación general no sustituye ese expediente: sirve para comprobar si la misma separación entre ruptura aceptada, retest y setup aparece en otros símbolos.", "", "## Mediocridades y fallas que esta simulación puede revelar", "", "1. **Etiquetado binario prematuro:** descartar por `no_stop_structure` borra una ruptura observada antes de que exista un retest.", "2. **Duplicación de eventos:** una misma permanencia fuera del nivel no debe generar una nueva ruptura cada vela; solo el cruce inicial y la aceptación.", "3. **Confusión de mecha y cierre:** una mecha fuera con cierre dentro es sweep, no breakout aceptado.", "4. **Fuga temporal:** ningún target o estado posterior debe usar velas que aún no existían en el corte.", "5. **Falsa precisión del volumen:** el tick volume de FX es relativo al feed MT5 y no puede convertirse en confirmación institucional centralizada.", "6. **Ruptura sin entrada:** continuar sin volver al FVG/OB es un resultado válido, no un fallo de ejecución del modelo.", "", "## Mejoras siguientes", "", "- Correlacionar cada `ACCEPTED_BREAK_WAIT_RETEST` con FVG/OB canónico y retest M15, después bajar a M5/M1.", "- Añadir estados persistentes `RETESTING_POI`, `OBSERVABLE_SETUP`, `EXPANSION_NO_ENTRY` e `INVALIDATED` al payload del motor.", "- Calibrar los umbrales de fuerza por símbolo y sesión, sin convertirlos en reglas firmadas hasta tener validación fuera de muestra.", "- Crear un expediente causal por evento con nivel roto, fuerza, contexto D1/H4/H1, POI, retest, stop disponible y motivo de espera.", "- Repetir la simulación en una ventana de validación separada; no usar estas mismas observaciones para afirmar ventaja estadística.", "", "## Limitación importante", "", "Esta simulación entrena la representación y la trazabilidad de la lectura; no demuestra que una estrategia sea rentable ni autoriza automatización de órdenes.", ""]
    return "\n".join(lines)


def main():
    results = []
    with connection(config()):
        for symbol in FOREX_SYMBOLS:
            try:
                results.append(simulate_symbol(symbol))
            except Exception as exc:
                results.append({"symbol": symbol, "error": str(exc), "d1_bars": 0,
                                "m15_bars": 0, "m15_closed": 0, "states": {},
                                "strong_candidates": 0, "strong_accepted": 0,
                                "studies": 0, "first_d1": "—", "last_d1": "—",
                                "first_m15": "—", "last_m15_closed": "—"})
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(results, generated_at), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "symbols": len(results),
                      "errors": [item for item in results if "error" in item]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
