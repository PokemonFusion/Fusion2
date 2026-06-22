# Move Inventory Audit - 2026-06-22

Scope: current local `fusion2` checkout, loaded `pokemon.dex.MOVEDEX` entries.
The CSV inventory is one row per loaded dex key, so compatibility aliases are
included separately.

Inventory file: `docs/move-inventory-2026-06-22.csv`

## Summary

| Measure | Count |
| --- | ---: |
| Loaded move dex keys | 1,904 |
| Unique display names | 952 |
| Physical rows | 848 |
| Special rows | 514 |
| Status rows | 542 |
| Rows with callback references | 602 |
| Explicit semantic contract rows | 256 |
| Mechanic-covered rows | 1,648 |
| Smoke-only move rows | 0 |
| Known-gap move rows | 0 |

## Coverage Interpretation

- `explicit_contract` means the exact move is named by an executable semantic
  outcome contract.
- `mechanic_contract` means the move uses at least one mechanic group already
  covered by executable semantic contracts, but that exact move may not have
  its own per-move proof.
- The current move inventory has no `smoke_only` or `known_gap` move entries.

Top inferred move mechanic groups:

| Mechanic | Rows |
| --- | ---: |
| Damage | 1,276 |
| Callback behavior | 636 |
| Random branch | 564 |
| Secondary effect | 412 |
| Stat boost/drop | 300 |
| Volatile | 280 |
| Status outcome | 174 |
| Callback damage/base power | 164 |
| Priority | 112 |
| Side condition | 38 |
| Drain | 26 |
| Field condition | 26 |

## Findings

1. All loaded move entries are classified by the current proof inventory.
2. No move is currently limited to smoke-only proof coverage.
3. The optional all-dex execution suite completed without move exceptions.
4. The generated callback adapter suite initially exposed a `Nature Power`
   nested-move path where lightweight battle objects lacked
   `participant_for(...)`. `pokemon/battle/engine.py` now skips ally
   `onAllyBasePower` processing when that participant interface is absent.
5. The broad inventory test still has one non-move smoke-only entry:
   `item:Rarecandy`. That does not affect the move inventory above.

## Higher-Risk Mechanic-Covered Groups

These are not failing, but they are the best candidates for future exact
per-move semantic contracts because their behavior is more conditional than
plain damage:

| Group | Unique move names |
| --- | ---: |
| Status/stat/volatile state | 288 |
| Callback behavior | 147 |
| Callback damage/base power | 66 |
| Field/side/weather state | 19 |
| Self switch | 8 |
| Forced switch | 3 |

## Validation

Commands were run from `H:\PokemonFusionProject\fusion2` with
`PYTHONPATH=H:\PokemonFusionProject\fusion2`.

| Command | Result |
| --- | --- |
| `..\evenv\Scripts\python.exe -m tests.battle_contract_coverage` | Passed; move summary was `total=1904; explicit_contract=256, mechanic_contract=1648, smoke_only=0, known_gap=0`. |
| `..\evenv\Scripts\python.exe -m pytest pokemon\battle\tests\test_generated_move_callbacks.py --run-callback-tests -q` | Passed after the engine guard. |
| `..\evenv\Scripts\python.exe -m pytest tests\test_all_moves_and_abilities.py --run-dex-tests -q` | Passed. |
| `..\evenv\Scripts\python.exe -m pytest tests\test_battle_semantic_contracts.py -q` | Passed. |
| `..\evenv\Scripts\python.exe -m pytest pokemon\battle\tests\test_move_resolution_event_flow.py pokemon\battle\tests\test_try_move_event_flow.py pokemon\battle\tests\test_move_control_event_flow.py pokemon\battle\tests\test_move_abort_message_flow.py pokemon\battle\tests\test_move_pp_serialization.py pokemon\battle\tests\test_post_hit_after_move_flow.py -q` | Passed. |
| `..\evenv\Scripts\python.exe -m pytest tests\test_base_power_callback.py tests\test_avalanche_base_power.py tests\test_assurance_base_power.py tests\test_beatup_base_power.py tests\test_boltbeak_base_power.py tests\test_crushgrip_base_power.py tests\test_dragonenergy_base_power.py tests\test_echoedvoice_base_power.py tests\test_electroball_base_power.py tests\test_eruption_base_power.py tests\test_firepledge_base_power.py tests\test_fishiousrend_base_power.py tests\test_flail_base_power.py tests\test_frustration_base_power.py tests\test_furycutter_base_power.py tests\test_grassknot_base_power.py tests\test_grasspledge_base_power.py tests\test_gyroball_base_power.py tests\test_hardpress_base_power.py tests\test_more_base_power_moves.py -q` | Passed. |
| `..\evenv\Scripts\python.exe -m pytest tests\test_move_effects.py tests\test_move_accuracy_from_dex.py tests\test_move_flags.py tests\test_status_moves_no_damage.py tests\test_move_failures.py tests\test_two_turn_moves.py tests\test_multi_hit_moves.py tests\test_self_switch_moves.py tests\test_field_hazard_moves.py -q` | Passed. |
| `..\evenv\Scripts\python.exe -m pytest tests\test_battle_contract_coverage.py -q` | Failed only on `test_inventory_uses_explicit_and_mechanic_buckets_without_smoke_only` because `item:Rarecandy` remains smoke-only. |
