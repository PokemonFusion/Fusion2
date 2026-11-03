# Application tests

[Documentation home](../docs/index.md) | [Code map](../docs/code-map.md) |
[Offline test commands](../docs/offline-battle-testing.md) |
[Verification reports](../docs/testing/README.md)

Application tests are grouped by the behavior they exercise. Run commands from
the repository root using the project's Python environment.

## Find tests by feature

| Folder | Coverage |
| --- | --- |
| [accounts](accounts/) | Account roster, onboarding, profiles, staff visibility, support requests |
| [adventure](adventure/) | Adventure commands, sessions, progress, results, rendering, recovery |
| [battle](battle/) | Battle commands, AI, lifecycle, persistence, parties, doubles/Multi, forms, UI |
| [breeding](breeding/) | Breeding and Mirror Herb rules |
| [communication](communication/) | Channels, mail, notes, pages, roleplay, bulletin board commands |
| [evolution](evolution/) | Evolution eligibility, item routes, and command safety |
| [items](items/) | Inventory, medicine, berries, acquisition, supply, support reconciliation |
| [mechanics](mechanics/) | Move/ability effects, damage, targeting, statuses, turn mechanics |
| [ownership](ownership/) | Party/storage slots, character sheets, Fusion transitions, trading |
| [pokemon](pokemon/) | Dex/species data, generation, stats, model validation, starter/grant flows |
| [progression](progression/) | EXP/EVs, training, move learning, PP capacity, trainer XP |
| [server](server/) | Protocols, reload/shutdown, database guards, logging, import isolation |
| [spawns](spawns/) | Hunting, spawn profiles, selection, previews, migration comparisons |
| [tools](tools/) | Offline safety/effect checks for the QA tools in [tools/qa](../tools/qa/README.md) |
| [ui](ui/) | General rendering, visibility, accessibility, web and room-editor views |
| [world](world/) | Gyms, NPC trainers, world movement/weather, builder commands |

The separate [battle-mechanics suite](../pokemon/battle/tests/) remains at its
existing path. Both suites use the root [conftest.py](../conftest.py) collector,
which restores legacy import-time stubs between test modules.

## Run the appropriate checks

The mandatory gate includes both test directories with generated callbacks in
three fresh processes: combined, repeat, and battle-first.

```powershell
..\evenv\Scripts\python.exe -B tools/run_mandatory_tests.py
```

A focused feature or single-file run can use its new path:

```powershell
..\evenv\Scripts\python.exe -B -m pytest tests/ownership
..\evenv\Scripts\python.exe -B -m pytest tests/ownership/test_trade_safety.py --basetemp .codex-artifacts/test-work/trade-safety
```

See [offline battle testing](../docs/offline-battle-testing.md) for exhaustive
dex, callbacks, Showdown, and semantic-contract commands. Do not infer live
server acceptance from an offline pass.

## Shared support and integration runners

- [Integration index](integration/README.md): guarded standalone database,
  protocol, and player-flow programs. Their entry paths remain stable.
- [helpers](helpers/): isolated subprocess helpers for rendering and ORM checks.
- [utils/testfactory.py](utils/testfactory.py): shared factories also imported
  by the developer command module; this support path remains stable.
- [urls.py](urls.py): test URL configuration.
- [Battle contract catalog](battle/battle_contract_catalog.py) and
  [coverage inventory](battle/battle_contract_coverage.py): shared metadata and
  reporting for semantic battle tests.

Tests that import another test's fixture now use its full feature package path.
Keep feature package initializers free of application imports so collection
does not introduce extra game setup.

## Finding a test from an older report

Filenames were retained when tests were grouped. To locate a formerly flat
test reference:

```powershell
rg --files tests -g 'test_trade_safety.py'
rg -n 'test_name_or_behavior' tests pokemon/battle/tests
```

Use current paths in new commands, CI steps, and guides. Dated evidence retains
its original commands and source pins; follow the filename to the current
location when reproducing a check.
