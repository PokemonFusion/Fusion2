# Alpha reliability branch validation

Reviewed October 15, 2026 against main `b31ed36`.

## Scope

This branch completes the existing Alpha Meadow Adventure participation,
authored encounters, outcome recording, and first-clear reward path. It adds
durable retry/claim recovery for Adventure results and gym badges, preserves
full trainer rosters in ordinary hunt encounters, fixes application/battle
test import isolation, and improves account selection and first-session help.
It also retains the branch's theme-foundations working-direction document.

This is the agreed reliability slice of the September roadmap. The larger
roadmap still tracks doubles, additional AI strategy, Terastallization,
production gym content, and other Pokemon lifecycle work separately.

## Completed local validation

| Check | Result |
| --- | --- |
| Combined application, battle, and generated callback suite | 2,857 passed; 4,010 skipped; 1,333 warnings |
| Production-model PostgreSQL reward recovery suite | 9 passed |
| PostgreSQL placement, capture, and concurrent-writer suite | 20 passed |
| Fresh PostgreSQL migration install | Passed; no Pokemon model drift |
| Upgrade from Adventure `0040_adventure_participation` | Passed; existing progression preserved |
| Upgrade from main `0041_placement_integrity_triggers` | Passed; existing progression preserved |
| Merged migration graph | Connected, one Pokemon leaf |
| Ruff comparison against main | No introduced findings |
| Complete branch diff whitespace check | Passed |

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
Pokemon, and an unpaid Adventure clear. All three paths retain those records
and recover the first-clear reward once. Every database write is confined to
a generated `pf2_recovery_test_` schema, removed after the run. No running-game
tables are migrated and no services are started or restarted by these checks.

## Repeatable checks

From the repository root:

```powershell
..\evenv\Scripts\python.exe -m pytest tests pokemon/battle/tests --run-callback-tests
..\evenv\Scripts\python.exe tests/integration/migration_graph.py
```

With `PF2_TEST_POSTGRES_DSN` explicitly supplied for an approved test connection:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_cases.py
```

After approval to apply migrations in disposable test schemas:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_migrations.py
```

The lifecycle-integrity CI workflow runs the combined suite, placement
integrity tests, PostgreSQL recovery checks, migration rehearsals, and the
merged graph check. Local results do not establish that a hosted CI run has
passed; record that run separately after pushing/opening the PR.

## Live acceptance and deployment gate

Interactive acceptance is pending. Use two ordinary characters on one account
and a separate staff login on a development game running this exact code with
the merged migrations through `0043_gym_victory`. Obtain operational approval
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
migration 0043 before loading the new gym-recovery code into the game.
