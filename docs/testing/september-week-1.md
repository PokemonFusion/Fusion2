# September Week 1 completion evidence

Reviewed October 16, 2026 against merged main `36524cf` and the Week 1 test-gate
follow-up. This is the battle/test foundation scope in issues
[#705](https://github.com/PokemonFusion/Fusion2/issues/705),
[#707](https://github.com/PokemonFusion/Fusion2/issues/707), and
[#709](https://github.com/PokemonFusion/Fusion2/issues/709).

## Test isolation (#705)

The canonical command is:

```powershell
..\evenv\Scripts\python.exe -B tools/run_mandatory_tests.py
```

The runner executes the application, engine, semantic and generated callback
suites together, repeats the same command in a new process, and reverses the
suite order in a third process. All passes use the same checkout/cache and
separate temporary directories inside that checkout. The runner returns the
first failure and clears ambient pytest options that could omit tests or use
parallel workers. `make test-mandatory` and lifecycle CI use this command.

`tests/test_test_import_isolation.py` reproduces an application test replacing
the battle module during import, while another test uses the real Electric
Terrain semantic contract. Both collection orders preserve the owning test's
stub and the real effect-handler module identities. Disabling the shared
collector makes the regression fail during collection.

The opt-in dex and Showdown exclusions, their reasons and commands are listed
in [offline battle testing](../offline-battle-testing.md). Callbacks are enabled
in all three mandatory passes.

## Result commits (#707)

[PR #734](https://github.com/PokemonFusion/Fusion2/pull/734) supplies the merged
reward and checkpoint implementation; capture and gym/Adventure result
services retain their existing durable receipts. See
[battle recovery](../battle-recovery.md) for the player command and guarantees.

| Completion criterion | Implementation and database-backed evidence |
| --- | --- |
| Stable identity and duplicate delivery protection | Battle UUID plus immutable effect keys; prize/faint replay, stale-checkpoint and concurrent duplicate-claim tests |
| Partial failure can finish without replaying committed effects | Wallet, claimed-marker and faint-receipt fault injection; `+battle/retry` after reconstruction; capture rollback/retry |
| Commit effects before success | Character row lock and one transaction for EXP/EVs, trainer resources and claimed marker; messages buffered until commit |
| Pending/completed/retryable state | Character receipt pending index and claimed marker; retained declaration/error and ending state for turn/cleanup recovery |
| Cleanup survives reconnect/rebuild | Failed-cleanup rollback preserves encounters, saved terminal intent and matching locks until a player retries |

`tests/integration/battle_recovery_cases.py` covers 29 real PostgreSQL cases,
including ordinary NPC prizes, PvP, wild capture, concurrent claims, failure
after real writes, active Fusion awards, and retained multi-slot choices.
`recovery_cases.py` adds 9 gym/Adventure claim cases;
`adventure_lifecycle_cases.py` adds 9 startup/result/cleanup cases.

## Lifecycle recovery (#709)

| Completion criterion | Evidence |
| --- | --- |
| Deterministic terminal state and legal forced reserve | All-fainted and forced-switch reconstruction for NPC, wild and PvP sessions |
| Restore actors, choices and turn resources | Pending PvP move and saved switch, rejected stale actor, HP/PP, participation, damage-source identity and retained multi-slot action cases |
| No duplicated turn/result/reward after reload | Atomic checkpoint failure and replay tests, completed declaration clearing, durable reward receipt tests |
| Cleanup releases matching state and protects outcomes | Cleanup-failure retry and old-session/new-lock protection; independent gym/Adventure receipts survive room cleanup |
| Player can understand and recover state | `+battle/retry`, discarded-choice feedback, resumed battle prompts, and existing reconnect recap |
| Real database-backed supported flows | Production sessions/models against disposable PostgreSQL schemas in the three suites above |

## Acceptance boundaries

PR #734 records ordinary-player local NPC, PvP and wild/capture acceptance at
`82316e1`, including reload/reconnect, queued-input preservation, reserve
send-outs, one reward/capture delivery, and final lock/encounter cleanup. Its
later multi-slot review fix at `605ebf8` has automated PostgreSQL and combined
suite coverage. [Hosted lifecycle CI for that final merged source passed](https://github.com/PokemonFusion/Fusion2/actions/runs/38908937892).

The Week 1 follow-up changes test tooling, regression coverage and documentation.
Its PostgreSQL checks build production model tables directly in generated,
guarded schemas and remove those schemas afterward. They apply no migrations
to the game and do not restart services. These results establish local and CI
verification; deployment to PF2-Dev and wider beta acceptance remain separate.
