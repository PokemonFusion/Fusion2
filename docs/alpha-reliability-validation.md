# Alpha reliability branch validation

Reviewed October 15, 2026 against main `b31ed36`.

## Scope

This branch completes the existing Alpha Meadow Adventure participation,
authored encounters, outcome recording, and first-clear reward path. It adds
durable retry/claim recovery for Adventure results and gym badges, preserves
full trainer rosters in ordinary hunt encounters, fixes application/battle
test import isolation, and improves account selection and first-session help.
It also retains the branch's theme-foundations working-direction document.

The local QA repairs also preserve battle EXP, HP, PP and major status;
normalize move, species and inventory name lookups; make capture/item writes
retry-safe; bind post-capture nickname input; and render active Fusion sheets
and HP bars correctly. Exit traversal aliases remain available beside core
commands. Live QA additionally exposed and repaired redirect-callback arguments
for Lightning Rod and Storm Drain.

This is the agreed reliability slice of the September roadmap. The larger
roadmap still tracks doubles, additional AI strategy, Terastallization,
production gym content, and other Pokemon lifecycle work separately.

## Completed local validation

| Check | Result |
| --- | --- |
| Combined application, battle, and generated callback suite | 2,922 passed; 4,010 skipped; 1,279 warnings |
| PostgreSQL progression, names, status/items, capture/Ether, PP/Full Restore, UI and Adventure lifecycle suites | 88 passed |
| Production-model PostgreSQL reward recovery suite | 9 passed |
| PostgreSQL placement, capture, and concurrent-writer suite | 20 passed |
| Additional PostgreSQL lifecycle diagnostics | 14 passed |
| Fresh PostgreSQL migration install | Passed; no Pokemon model drift |
| Upgrade from Adventure `0040_adventure_participation` | Passed; existing progression preserved |
| Upgrade from main `0041_placement_integrity_triggers` | Passed; existing progression preserved |
| Upgrade from `0043_gym_victory` through status migration 0044 | Passed; existing Pokemon start healthy |
| Merged migration graph | Connected, one Pokemon leaf |
| Scoped Ruff comparison with the pre-repair branch | No introduced findings |
| Complete branch diff whitespace check | Passed |
| Local database migration 0044 and server reload | Applied successfully after backup; Portal/Server running |
| Ordinary-player capture, nickname resume/reconnect, medicine, status and Fusion UI | Passed locally |

The opt-in dex and Showdown tests remain outside this validation run. Existing
Ruff findings on main are recorded separately from new changes; this review
does not claim that the repository as a whole is lint clean.

PostgreSQL checks use actual account, character, inventory, badge, Adventure,
and gym-victory models. Competing calls run on distinct database connections.
The tests verify overlapping claims, different rematches awarding one badge,
concurrent first clears, rollback after real writes, retry after reconnect
through newly fetched characters, and isolation between two characters on one
account. A held character row is observed blocking a competing gym claim.

Migration rehearsals seed inventory, earned badges, a canonically placed
Pokemon, and an unpaid Adventure clear. All four paths retain those records
and recover the first-clear reward once. Every database write is confined to
a generated `pf2_recovery_test_` schema, removed after the run. No running-game
tables are migrated and no services are started or restarted by these checks.

Separately, the user authorized local activation. A PostgreSQL custom-format
backup was saved and its archive listing verified before applying only
`0044_owned_pokemon_status` to the loopback game. The server was reloaded and
ordinary QA characters exercised Low Grass, spaced move/ball commands, Potion,
capture/nickname input and reconnect, Ether, paralysis across cleanup/reconnect
and a subsequent battle, Full Restore, Fusion sheets and clean HP bars. The
live redirect callback failure was repaired and its PvP sequence repeated
without new battle errors. QA accounts and their normal gameplay history are
retained; these results do not establish deployment to PF2-Dev.

PR review additionally verifies startup failures inside, before and after registration,
metadata persistence before the first turn, concession receipt failures and
single cleanup, retry after a cleanup outage, and a committed capture replay
after losing its in-memory nickname tracking. All nine cases use real
commands, sessions, the canonical battle handler and saved models in a guarded
disposable PostgreSQL schema. Failed startup releases locks or retains a
player-accessible cleanup retry; pending terminal concessions freeze battle
input until `+adventure/retry` can save the result. These review failure paths
were not injected into the running game.

## Repeatable checks

From the repository root:

```powershell
..\evenv\Scripts\python.exe -m pytest tests pokemon/battle/tests --run-callback-tests
..\evenv\Scripts\python.exe tests/integration/migration_graph.py
```

With `PF2_TEST_POSTGRES_DSN` explicitly supplied for an approved test connection:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_cases.py
..\evenv\Scripts\python.exe tests/integration/progression_cases.py
..\evenv\Scripts\python.exe tests/integration/name_resolution_cases.py
..\evenv\Scripts\python.exe tests/integration/status_item_cases.py
..\evenv\Scripts\python.exe tests/integration/capture_ether_cases.py
..\evenv\Scripts\python.exe tests/integration/capture_pp_item_cases.py
..\evenv\Scripts\python.exe tests/integration/ui_cases.py
..\evenv\Scripts\python.exe tests/integration/adventure_lifecycle_cases.py
```

The progression regressions use production Pokemon models and the battle
move-use, faint/reward, HP cleanup, and healing paths in a disposable PostgreSQL schema.
They cover array-backed EVs, persisted EXP and remaining HP, switched party
members, active Fusion forms, healing/PP after a win, and the next battle's
calculated maximum HP. PP spending is checked against fresh SQL reads across
restored snapshots and new battles, including zero-PP rejection and healing.
They do not modify running-game records or reload code.

Name-resolution regressions cover spaced and punctuated species, nicknames,
learned-move identity, moveset editing, PP bonuses, Pokédex progress, and faint
rewards using production models in a disposable PostgreSQL schema. The regular
suite also checks every loaded dex name and every CSV-backed reward entry.

UI regressions use the real EvMenu input handler and sheet renderer with saved
models in a disposable PostgreSQL schema. Captures queue a choice by owned
Pokemon ID, open it after battle cleanup, and support yes/no, spaced nicknames,
and `+nickname` to resume. Fusion sheets use the active form's battle stats and
the trainer's saved inventory and wallet. The ordinary suite also checks HP
bars through Evennia's real Telnet and web text converters. These checks use
current model tables directly, without migrations or service reloads.

After approval to apply migrations in disposable test schemas:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_migrations.py
```

The lifecycle-integrity CI workflow runs the combined suite, placement
integrity tests, PostgreSQL recovery checks, migration rehearsals, and the
merged graph check. Local results do not establish that a hosted CI run has
passed; record that run separately after pushing/opening the PR.

## Live acceptance and deployment gate

Focused local battle/item/UI acceptance has passed. Broader Adventure, gym,
onboarding and injected-failure acceptance below remains pending. Use two ordinary characters on one account
and a separate staff login on a development game running this exact code with
the merged migrations through `0044_owned_pokemon_status`. Obtain operational approval
before applying game migrations or changing service state.

| Acceptance check | Status |
| --- | --- |
| Wild and trainer Adventure routes; capture, win, loss, flee; normal leave/cleanup | Pending |
| Saved result after failure, cleanup, and reconnect; `+adventure/retry` | Pending |
| Unpaid first-clear reward after reconnect; repeated `+adventure/claim` | Pending |
| Normal gym victory, rematch, loss/concede, and `+gym claim` | Pending |
| Badge-write/marker failure, rebuilt result, and ledger-outage cleanup guard | Pending |
| Two characters on one account cannot claim each other's rewards | Pending |
| Ordinary NPC hunt preserves reserves and completes switching/cleanup | Pending |
| Website/game login, character selection, both chargen paths, and beginner links | Pending |

Use the [Adventure operations guide](adventure-operations.md), the detailed
[Adventure manual checklist](testing/adventure-manual-acceptance.md), and the
[gym recovery checklist](gym-recovery.md#pending-live-acceptance). Record the
code commit, commands/responses, character and session/victory IDs, and any
traceback for each check. Remove all temporary failure hooks after each test.
Keep pending receipts and progression history when diagnosing failures.

Before a game upgrade, take a verified database backup and run the canonical
placement audit required by migration 0040 on the placement branch. Resolve
any reported ambiguity before retrying; the migration intentionally refuses
to repair player data automatically. Apply the merged graph through gym
migration 0044 before loading this branch's status-persistence code into a game.
