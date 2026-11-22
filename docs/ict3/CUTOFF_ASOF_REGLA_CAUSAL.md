# `cutoff=asof` en US30 — regla causal y aislamiento de las 4 incidencias

**Revisión atendida:** `2b75b99c-aa5b-4ec9-92ab-09e6b87e9c53` (Fase 8).
**Autoridad:** ICT 2.0 `f453bf2`. **Modo:** `OBSERVE_ONLY_NO_ORDER`, sin órdenes,
credenciales ni escrituras en `data/`.
**Fecha de la corrida:** 2026-11-22T16:51Z.

## 1. Conclusión

Las cuatro incidencias de `ict3_contract.validate(..., cutoff=asof)` en US30
**no son velas futuras ni un fallo del contrato**. Son el resultado de validar
un bloque construido con el reloj de pared usando como corte el ancla M15
(`asof`), que está desactualizada porque MT5 está `stale`. Cada una de las
cuatro marcas es `<=` el corte con el que se construyó el bloque; validado con
ese corte, el mismo bloque da **0 incidencias**.

No se cambió la semántica de `validate`: solo se documentó la regla en su
docstring y se añadió evidencia ejecutable en `test_ict3_cutoff_asof.py`.

## 2. Los dos relojes

| Reloj | Dónde se fija | Qué ancla | Valor en US30 |
|---|---|---|---|
| M15 (`asof`) | `ict.analyze_cached`: `decision_epoch` desde la última vela M15 cerrada; `result['asof']` | snapshot diaria, contexto, POI, contrato base | `1795218300` = `2026-11-20T23:45:00Z` (stale) |
| Pared | `ict.ict_chart`: `as_of = cutoff if cutoff is not None else int(time.time())` | filtro de M5/M1 en `attach_confirmations` (`closed <= cutoff`) | `1795219200` (último cierre M5 servido) |

`analyze_cached` lo declara explícitamente: *"Context and POI use the same
as-of instant; M1/M5 may show later closed formations without altering the
daily snapshot."* Por tanto es **esperable** que M5/M1 y su liquidez sean más
recientes que `asof` sin que ello altere la lectura diaria.

`_closed_bars` en `ict3_confirm.py` garantiza que toda vela M5/M1 usada
cumple `closed <= cutoff` del reloj de pared. `last_closed_m5`,
`last_closed_m1` y `target_liquidity[].observed_at` derivan de esas velas.

## 3. Aislamiento de las cuatro incidencias

Payload vivo capturado con `GET http://127.0.0.1:8766/api/ict?symbol=US30&tf=M15`
(lectura, sin `at`, sin POST). `ict3_contract.validate(block, cutoff=asof)`:

| # | Incidencia | Valor | `<= asof` | `<= cutoff` de construcción |
|---|---|---|---|---|
| 1 | `evt_36b6f6e056899a9c.liquidez.observed_at` (`M1_SWING`) | `1795218540` | no | sí (`<= 1795219200`) |
| 2 | `evt_ba099ef9917346ec.liquidez.observed_at` (`M1_SWING`) | `1795218540` | no | sí (`<= 1795219200`) |
| 3 | `ict3.load.last_closed_m5` | `1795219200` | no | sí (igual) |
| 4 | `ict3.load.last_closed_m1` | `1795219080` | no | sí (`<= 1795219200`) |

Resultados: `cutoff=asof(1795218300)` → **4 incidencias**;
`cutoff=now(1795219200)` → **0 incidencias**. Ningún otro campo del contrato
cruza el corte. No aparece `schema_version` desconocida, política inesperada,
clave prohibida ni `entry_authorized=true`.

## 4. Regla causal precisa

1. `validate(block, cutoff=C)` exige que **toda** marca temporal del bloque sea
   `<= C`. Esa invariante es correcta siempre que `C` sea el corte real de
   construcción.
2. El bloque servido sin `at` se construye con dos cortes: `C_base = asof`
   (M15) y `C_lower = int(time.time())` (M5/M1).
3. Los campos del bloque `load` y `target_liquidity` se generan con
   `C_lower`, no con `C_base`. Al validar con `C_base` se comparan dos
   instantes distintos y aparecen las cuatro incidencias.
4. En cuanto existe una cotización autorizada y se pide `GET /api/ict?...&at=<epoch>`,
   `ict_chart` usa ese mismo `epoch` para ambos relojes: `asof == cutoff`.
   Entonces `validate(..., cutoff=at)` da 0 incidencias. Es el caso cubierto por
   `test_ict3_cutoff_asof.CutoffAsOfContractTests.test_historical_payload_has_zero_issues_at_its_own_cutoff`.

**Uso correcto:** validar con el `at` explícito usado al construir el payload,
o con `cutoff=now` cuando el bloque se sirvió sin `at` con el reloj de pared.
**Uso incorrecto:** pasar `result['asof']` como `cutoff` a un bloque construido
sin `at` con MT5 stale.

## 5. Evidencia ejecutable

```
.venv/Scripts/python.exe -m unittest -v test_ict3_cutoff_asof
Ran 3 tests in 0.002s
OK
```

- `test_historical_payload_has_zero_issues_at_its_own_cutoff`: 0 incidencias
  para un payload histórico válido.
- `test_four_us30_incidences_are_isolated`: reproduce exactamente
  `(2 liquidez, 1 last_closed_m5, 1 last_closed_m1)` = 4.
- `test_flagged_instants_are_not_future_data_in_build_clock`: cada marca
  marcada es `<=` al corte de construcción; con ese corte, 0 incidencias.

Sin MT5, sin credenciales y sin escrituras en `data/`: los generadores son los
mismos deterministas que usa ya la suite.
