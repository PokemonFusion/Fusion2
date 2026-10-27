# Manual battle recovery acceptance (#773)

32 existing items now work through `+item`: 13 foods/drinks/revival equivalents and 19 recovery berries/Berry Juice, including all nine legacy equivalents. No definitions or plot effects are added.

The [named policy](../battle-recovery-items.md) records every enabled item, the 12 excluded candidates and failure/action rules. Field flavor/EV berries and Sacred Ash remain excluded from `+item`. Existing field and held routes remain independent.

## Final evidence

- Base: `a07e6bdd5e9fa1f7fcebdafef1e61191dfdd218b` plus this scoped change.
- **48 new PostgreSQL cases**, **597 total PostgreSQL cases** across 24 fresh isolated suites.
- **874 focused tests passed**.
- Mandatory combined: **4,729 passed / 4,014 skipped**.
- Mandatory repeat: **4,729 passed / 4,014 skipped**.
- Mandatory battle-first: **4,729 passed / 4,014 skipped**.
- **82 command/SQL observations**, with all 32 item effects, one-copy debits and two completed checkpoint rebuilds per item.
- **986 Python source files** stayed unchanged throughout the qualifying run; normalized LF hashes, exact test commands, durations and log hashes are in the [JSON report](battle-recovery-foods-2026-10-22.json).
- No private schemas or public tables remain; the disposable PostgreSQL cluster is stopped. No game database or migration runner was used.

Coverage includes real parsing, PlayerChoices, action queues, complete turns, active/reserve targets, revive, boosted selected-move PP caps/defaults, waiting declarations and repeated checkpoints. Unsupported/field-only/missing-stock/wrong-target/wrong-actor, four active actors in PvP doubles, no-effect action costs, stale cached ownership/egg/placement, partial failed debits, post-write failure and HP/PP checkpoint rollback all passed. Normal field-food/berry/EV/medicine/herbal routes, capture restrictions, held activation and inventory separation are regression-tested.

The initial Hyper Training regression run had one stale-object contention assertion fail. It reproduced on immutable pre-change sources in 5/12 attempts; SQL held all six trained stats in every baseline/current attempt. The unchanged full 29-case suite passed on rerun, and the separate current-build 12-attempt diagnosis also passed. The JSON retains the original failure, baseline/current cached-versus-SQL values and passing rerun; no Hyper Training implementation or fixture fix is included. [#783](https://github.com/PokemonFusion/Fusion2/issues/783) tracks this separate pre-existing fixture follow-up; the passing rerun does not erase it.

Native Ripen/Cheek Pouch with opposing Unnerve do not change trainer bag effects or consume held copies. A separate natural held Oran activation remains effective after a bag food action. Bag use never invokes held `onEat` callbacks.

## Per-item ordinary input

Each row started with two bag copies and ended with one. Status = major persistent condition; HP caps are calculated from native stats.

| Command | HP before → after | Status before → after | PP before → after |
| --- | --- | --- | --- |
| `+item Aspear Berry=1` | 1 → 1 / 198 | frz → none | [40, 35, 25] → [40, 35, 25] |
| `+item Berry=1` | 1 → 11 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Berry Juice=1` | 1 → 21 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Big Malasada=1` | 1 → 1 / 198 | par → none | [40, 35, 25] → [40, 35, 25] |
| `+item Burnt Berry=1` | 1 → 1 / 198 | frz → none | [40, 35, 25] → [40, 35, 25] |
| `+item Casteliacone=1` | 1 → 1 / 198 | tox → none | [40, 35, 25] → [40, 35, 25] |
| `+item Cheri Berry=1` | 1 → 1 / 198 | par → none | [40, 35, 25] → [40, 35, 25] |
| `+item Chesto Berry=1` | 1 → 1 / 198 | slp → none | [40, 35, 25] → [40, 35, 25] |
| `+item Fresh Water=1` | 1 → 31 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Gold Berry=1` | 1 → 31 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Ice Berry=1` | 1 → 1 / 198 | brn → none | [40, 35, 25] → [40, 35, 25] |
| `+item Lava Cookie=1` | 1 → 1 / 198 | slp → none | [40, 35, 25] → [40, 35, 25] |
| `+item Lemonade=1` | 1 → 71 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Leppa Berry=3/Water Gun` | 1 → 1 / 180 | none → none | [40, 0, 0] → [40, 0, 10] |
| `+item Lum Berry=1` | 1 → 1 / 198 | psn → none | [40, 35, 25] → [40, 35, 25] |
| `+item Lumiose Galette=1` | 1 → 1 / 198 | brn → none | [40, 35, 25] → [40, 35, 25] |
| `+item Max Honey=3` | 0 → 180 / 180 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Mint Berry=1` | 1 → 1 / 198 | slp → none | [40, 35, 25] → [40, 35, 25] |
| `+item Miracle Berry=1` | 1 → 1 / 198 | tox → none | [40, 35, 25] → [40, 35, 25] |
| `+item Moomoo Milk=1` | 1 → 101 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Mystery Berry=3/Water Gun` | 1 → 1 / 180 | none → none | [40, 0, 0] → [40, 0, 5] |
| `+item Old Gateau=1` | 1 → 1 / 198 | psn → none | [40, 35, 25] → [40, 35, 25] |
| `+item Oran Berry=1` | 1 → 11 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Pecha Berry=1` | 1 → 1 / 198 | tox → none | [40, 35, 25] → [40, 35, 25] |
| `+item Pewter Crunchies=1` | 1 → 1 / 198 | slp → none | [40, 35, 25] → [40, 35, 25] |
| `+item PRZ Cure Berry=1` | 1 → 1 / 198 | par → none | [40, 35, 25] → [40, 35, 25] |
| `+item PSN Cure Berry=1` | 1 → 1 / 198 | psn → none | [40, 35, 25] → [40, 35, 25] |
| `+item Rawst Berry=1` | 1 → 1 / 198 | brn → none | [40, 35, 25] → [40, 35, 25] |
| `+item Shalour Sable=1` | 1 → 1 / 198 | frz → none | [40, 35, 25] → [40, 35, 25] |
| `+item Sitrus Berry=1` | 1 → 50 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Soda Pop=1` | 1 → 51 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |
| `+item Sweet Heart=1` | 1 → 21 / 198 | none → none | [40, 35, 25] → [40, 35, 25] |

## Reproduce

Use an explicit disposable `PF2_TEST_POSTGRES_DSN`, then:

```text
python -B tests/integration/battle_recovery_food_cases.py
python -B tests/integration/battle_item_validation_cases.py
python -B tests/integration/field_food_cases.py
python -B tests/integration/field_berry_cases.py
python -B tests/integration/legacy_berry_cases.py
python -B tools/run_mandatory_tests.py
```

The standalone PostgreSQL harness creates production tables inside guarded random schemas and drops them afterward; it does not run migrations. The JSON lists every final regression command. Optional `PF2_BATTLE_RECOVERY_EVIDENCE` writes the detailed normal-command receipts. Local orchestration redirects only battle logs to this task's ignored artifact folder.

## Findings, history and limits

The stale-cache negative exposed a real bug: a target changed to an egg in SQL could still receive healing from a cached instance. Current medicine execution reads locked row values for owner/egg/friendship and placement. Failed HP/status debits now abort their savepoint, matching PP's existing behavior. A native-ability fixture assertion was corrected. One early gate was intentionally interrupted for a stale help sentence; only the final frozen rerun qualifies.

The dated #772 acquisition reports and #757/#766/field recovery reports remain byte-identical. The current audit tool now emits a manual battle route for enabled medicine and intentional exclusions for the other candidates; this report's 44 current candidate rows supplement those historical snapshots.

This is **local automated ordinary-command/session/SQL evidence**, with fixture setup separate from player actions. There was no fresh live-player login or deployment. Prepared inventories/encounters do not establish current obtainability, natural acquisition/learnsets, all interactions, concurrency/load or economy balance. Hosted CI, main merge, release acceptance and #779–#782 remain separate. Existing human characters, live stock, game services, migrations and unrelated WIP were untouched.
