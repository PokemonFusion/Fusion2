# QA tools

[Tools index](../README.md) | [Application tests](../../tests/README.md) |
[Testing and evidence](../../docs/testing/README.md)

These scripts prepare or inspect controlled QA runs. Their regression tests
are under [tests/tools](../../tests/tools/). Merely running a CLI help command
does not execute a player walkthrough.

## Entry points

| Task | Script and supporting modules |
| --- | --- |
| Controlled battle pilot | [live_battle_pilot.py](live_battle_pilot.py), [cases](live_battle_pilot_cases.py), [server observer](live_battle_pilot_server.py) |
| Catalog-driven dex sweep | [live_dex_runner.py](live_dex_runner.py), [cases](live_dex_cases.py), [server observer](live_dex_server.py) |
| Ability-specific probes | [live_dex_ability_probes.py](live_dex_ability_probes.py) |
| Wild/capture probes | [live_dex_wild_probes.py](live_dex_wild_probes.py), [server observer](live_dex_wild_server.py) |
| Effect probes | [live_smoke_effects.py](live_smoke_effects.py), [cases](live_smoke_effects_cases.py), [server observer](live_smoke_effects_server.py) |
| Coverage reports for retained observations | [live_dex_coverage.py](live_dex_coverage.py), [live_smoke_effect_coverage.py](live_smoke_effect_coverage.py) |

From the repository root:

```powershell
..\evenv\Scripts\python.exe -B tools/qa/live_battle_pilot.py --help
..\evenv\Scripts\python.exe -B tools/qa/live_dex_runner.py --help
..\evenv\Scripts\python.exe -B tools/qa/live_smoke_effects.py --help
```

Read the [battle pilot guide](../../docs/testing/live-battle-pilot.md) and
[dex sweep guide](../../docs/testing/live-dex-sweep.md) for prerequisites,
fixture protection, and evidence limits before an actual run. QA preparation
and player runs can create fixtures or change game state.

The former flat `tools/live_*.py` files now live together in `tools/qa/`.
Current code uses `tools.qa` imports so CLI and test callers share module
identities. Supporting server modules remain beside their case/runner modules.
Dated reports may cite the earlier flat paths.

Retained observations and scratch output belong in the locations described by
[workspace hygiene](../../docs/workspace-hygiene.md).
