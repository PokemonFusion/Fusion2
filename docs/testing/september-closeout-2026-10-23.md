# September issue closeout — October 23, 2026

September's 13 issues (#705–#717) have been reconciled against current code,
fresh tests and retained dated ordinary-player protocol evidence. Four were
already closed (#706/#713/#714, and #716 consolidated into #712); nine are ready
for evidence-linked closure. Publication of this report precedes tracker updates.
Baseline: `aec4bfcd3737e21915bf2e54b2c51c22de29046a`. [Machine-readable criteria, commands/SQL and source pins](september-closeout-2026-10-23.json).

## Repairs and retained Adventure integration (#717)

Two gaps remained in the September slice. Saved room-pool references are Evennia
mutable sequences; recognizing only plain lists made an available configured
pool appear empty. The resolver now accepts the saved sequence protocol.
Alpha Meadow also required a battle, losing the original non-combat survey.
Reach/search/return now completes it without choosing an encounter. Once chosen,
an encounter's pending result still blocks completion/rewards until resolved.

The host session, per-character participation, result/retry receipt and atomic
first-clear/claim architecture are retained. Wild/NPC routes and the one-Potion
first clear already existed and are preserved. Survey-only runs fabricate no
encounter result; replay/claims never create a second first-clear Potion.
No new mission, encounter, reward, group, map or November feature is introduced.

Three focused unit regressions and six production-model player-route cases
cover actual configured player typeclasses, saved room references, slash/cardinal
commands, read-only views, reconnect seam, completion, replay, leave, expiry,
failed post-write reward delivery/claim and an actual optional wild battle win.
Only outbound transport is captured; game commands/services/effects/SQL are real.
The JSON retains command-by-command output and authoritative before/after rows.
The new PostgreSQL suite is registered in lifecycle CI.

The connected migration graph has one Pokémon leaf. Both Adventure models'
fields/options exactly match checked-in migration state. No model change or new
migration is needed. Table-only disposable schema construction is distinct from
the older migration rehearsals; no migration was executed here.

## Fresh regression evidence

**177 PostgreSQL cases across 14 suites passed.** Each suite uses a fresh
guarded schema with real production models and removes it afterward.

| Standalone integration suite | Passed |
| --- | --- |
| `adventure_player_cases.py` | 6 |
| `adventure_lifecycle_cases.py` | 9 |
| `recovery_cases.py` | 9 |
| `battle_recovery_cases.py` | 36 |
| `trainer_challenge_cases.py` | 10 |
| `ai_action_cases.py` | 6 |
| `ai_scoring_cases.py` | 7 |
| `production_gym_cases.py` | 10 |
| `player_doubles_cases.py` | 10 |
| `terastallization_cases.py` | 6 |
| `placement_cases.py` | 20 |
| `evolution_cases.py` | 28 |
| `progression_cases.py` | 11 |
| `cloud_gameplay_cases.py` | 9 |

The Adventure-focused unit selection passed **41 tests**. The canonical
`python -B tools/run_mandatory_tests.py` passed **4,907 tests / 4,014
optional skips in each of three fresh processes**: combined, repeat and
battle-first. Callback tests are enabled. Final focused checks include test-only
import formatting and the expanded SQL receipt; runtime repairs preceded the
mandatory gate. Scoped Ruff and `git diff --check` pass. Hosted CI is separate.

The first gate attempt failed its final subprocess database check because the
test cluster was stopped too early. The failed receipt/diagnosis is retained in
JSON. All three orders were then rerun successfully with the cluster available
through completion; no game rule was changed to make that check pass.

The final source inventory pins 1,035 Python Git blobs (aggregate plus
29 issue-specific source hashes). The private loopback test cluster
has been stopped with **zero disposable schemas remaining**. No existing game
database/service or human character/Pokémon was changed.

## Issue reconciliation

| Issue | Original work | Disposition after verification |
| --- | --- | --- |
| [#705](https://github.com/PokemonFusion/Fusion2/issues/705) | Stabilize battle test-suite isolation | Verified for closure |
| [#706](https://github.com/PokemonFusion/Fusion2/issues/706) | Preserve full NPC teams and expose player challenges | Already closed; verified |
| [#707](https://github.com/PokemonFusion/Fusion2/issues/707) | Make battle result commits retry-safe | Verified for closure |
| [#708](https://github.com/PokemonFusion/Fusion2/issues/708) | Add player doubles format and target-selection UX | Verified for closure |
| [#709](https://github.com/PokemonFusion/Fusion2/issues/709) | Cover battle lifecycle recovery edge cases | Verified for closure |
| [#710](https://github.com/PokemonFusion/Fusion2/issues/710) | Centralize legal AI actions and reserve switching | Verified for closure |
| [#711](https://github.com/PokemonFusion/Fusion2/issues/711) | Complete doubles and situational AI scoring | Verified for closure |
| [#712](https://github.com/PokemonFusion/Fusion2/issues/712) | Ship one retry-safe production strategy gym | Verified for closure |
| [#713](https://github.com/PokemonFusion/Fusion2/issues/713) | Enforce canonical Pokémon ownership and placement | Already closed; verified |
| [#714](https://github.com/PokemonFusion/Fusion2/issues/714) | Harden evolution and held-item transitions | Already closed; verified |
| [#715](https://github.com/PokemonFusion/Fusion2/issues/715) | Complete Terastallization end to end | Verified for closure |
| [#716](https://github.com/PokemonFusion/Fusion2/issues/716) | Make gym badges and repeat rewards retry-safe | Already closed; verified |
| [#717](https://github.com/PokemonFusion/Fusion2/issues/717) | Reconcile existing Adventure integration work | Verified for closure |

#705 uses the existing fresh-process gate/import-isolation regression and CI
entry. #707/#709 use the durable UUID/effect receipts, transactional checkpoint
and reward writes, reconstruction, retained input and cleanup/retry paths;
faults/concurrent delivery are tested on real SQL. #706/#708 retain full rosters,
normal challenges, actor/target classes, switches, singleton slots and terminal
cleanup. #710/#711 retain shared legal candidates and documented bounded
switching/ally/spread/status/setup/recovery/Protect/Trick Room decisions.

#712 retains durable Tempo configuration, full roster, observable strategy,
first-clear badge, 24-hour rematch cooldown, no farmable repeat progression,
idempotent installer, rebuild and rollback/concurrent claims. #716 remains
consolidated there. #713/#714 retain canonical placement, safe captures,
evolution/current-target/item conditions and atomic give/replace/remove/retries.
#715 retains normal Tera commands, side budgets, supported Gen 9 effects,
deterministic NPC use, checkpoints and transient cleanup. #717's remaining
non-combat and saved-pool gaps are fixed above.

## Dated player evidence and limits

- **October 16 doubles:** retained local Telnet QA has 53 passing checks and zero
  failures. A separate terminal-battle receipt confirms completion through real
  player attacks, surviving A2 identity and both cleared player locks. Older
  recorded follow-ups remain visible in JSON; they are not silently reclassified.
- **October 17 Tempo Gym:** 54 local player-protocol assertions verify discovery,
  Alpha retirement, readiness, Trick Room, first clear, badge-only rewards,
  loss/concession, cooldown and mid-battle reload/reconnect. See the
  [dated gym record](../production-strategy-gym.md#local-acceptance-october-17-2026).
- **October 17 Tera:** retained `18eab55` record has 111 passing command checks
  and 46 data checks; pending/spent side state, Stellar effects, switching,
  NPC policy, real reload and cleanup are retained. One corrected HUD harness
  expectation remains explicit. The
  [October 20 recovery record](battle-recovery-concurrency-2026-10-20.md) adds
  31 socket scenarios/nine reloads and natural reward replay on its dated build.

These are retained local ordinary-player protocol runs, separate from today's
automated command/database verification. They do not establish current PF2-Dev
deployment, a new live walkthrough, browser acceptance, human balance playtests,
abrupt power-loss/load testing or new release approval. Existing shared Windows
battle-log rotation/deprecation/model-reimport warnings remain documented.

## Deferred work

November still owns broader Adventure missions/job board/reward economies,
milestones, difficulty variants, groups, reputation, procedural/user-created maps
and crafting. No parallel session, ownership or reward writer is introduced.
October #722/#723/#725 and the separate item/form lifecycle follow-ups remain
outside September. Any later migration, release, restart or live fixture setup
requires its own exact approved operation; this closeout performs none.
