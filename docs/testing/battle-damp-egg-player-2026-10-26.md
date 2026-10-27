# Damp and egg-roster player-route repairs — 2026-10-26

Scope: [#915](https://github.com/PokemonFusion/Fusion2/issues/915) and
[#918](https://github.com/PokemonFusion/Fusion2/issues/918), based on
`cb5480203accbd438e82fd9b6ff2ceb01ce092bc`. No plot route, item stock,
migration, shared deployment or game service operation is included.

## Fresh diagnosis

Native Damp Wooper plus ordinary Sandstorm reproduced
`AttributeError: 'Sandstorm' object has no attribute 'id'` in the actual Damage
callback, including a queued player turn restored from SQL. The corrected
pre-repair unit reproduction had 21 failures and four passing controls. It also
showed that blocked Explosion/Self-Destruct still sacrificed their user, and
Aftermath's direct HP write bypassed Damp prevention.
The suppressed-Damp control independently reproduced one further failure with
30 passing controls: pre-move gating read the stored ability while Damage used
the effective ability. Pre-move gating now uses the same shared effect adapter.

An independent SQL reproduction placed an unhatched Eevee in party slot 1,
Quagsire in slot 3 and a fainted Mew reserve in slot 5. Ordinary PvP
create/join/start admitted Eevee as the lead and roster member. The unchanged
`OwnedBattleActor.locked(..., active=False)` guard then rejected that same owned
egg with `That Pokemon is no longer your eligible party or current Fusion.`
The structured evidence retains that original checkpoint and its SQL resources.

## Repairs and player acceptance

Damp uses `EffectContext.key` for Damage and TryMove identity. Prevented attempts
pay the ordinary PP cost and stop before self-sacrifice; later protection/miss
self-destruct handling remains intact. Aftermath now uses the established
indirect-damage event. Actual non-Damp and suppressed-Damp controls still take
explosive damage and its sacrifice cost. Ordinary contact damage, recoil and
status/weather residuals remain effective, without suppressing diagnostics.

The shared battle builder filters current owned egg flags before choosing leads.
Fainted non-eggs remain roster members for Revive. Canonical party selectors and
Fusion order remain separate from internal roster indices; no custody, egg HP,
hatch timer or party placement is repaired or compacted as a side effect.

The focused SQL acceptance contains **16 cases**:

- Four Damp cases use native Wooper/Quagsire, actual Sandstorm, Explosion,
  Self-Destruct and a contact KO on native Aftermath Drifloon. Fresh SQL proves HP
  and PP effects; pending inputs and weather survive checkpoint reconstruction.
- Ten egg-roster cases cover ordinary PvP create/join/start, singles/doubles,
  stale readiness, no usable party, canonical switch rejection, `+item Revive=5`,
  `+switch 5`, `+fuse/temp 6`, `+switch fusion`, `+box/deposit <UUID>`, an
  already-hatched positive control, encounter builders and recovery refusal.
- Two additional cases use the existing actual acquisition/combine/teach/equip
  player harness for both Dawn and Dusk Ultra. A separately labelled party egg
  remains outside the roster while preview/confirmation, activation, the
  signature attack and reconstruction complete. The egg's full SQL row is
  unchanged across both guarded turns.

The wider affected SQL suites also pass: battle recovery **36**, player doubles
**10**, Multi Battle **33**, manual recovery foods/berries **50**, and the complete
Ultra suite **45**. The Ultra total includes the two new egg cases; these are
overlapping suites, not 190 unique new tests. The stale-egg medicine fixture now
respects quarantine during teardown instead of bypassing protected end writes.

Final verification completed on **2026-10-27**. The focused engine/party suite
passed **53** tests. The canonical mandatory gate exited **0** after all three
fresh orders:

| Order | Passed | Skipped | Seconds |
| --- | ---: | ---: | ---: |
| Combined | 6,649 | 4,030 | 693.83 |
| Repeat | 6,649 | 4,030 | 678.56 |
| Battle-first | 6,649 | 4,030 | 598.42 |

Command: `H:\PokemonFusionProject\evenv\Scripts\python.exe -B tools/run_mandatory_tests.py`.
The legacy test harness emits model re-registration warnings (counts are retained
in JSON). PostgreSQL cases are separately executed above; no skipped SQL test is
counted as player acceptance. The ledger contains **77** ordinary command
observations plus **66** Ultra command/menu inputs, with setup and refusals
labelled separately.

## Existing checkpoint recovery policy

An old saved roster containing an unhatched owned egg is **paused**, retaining
its original roster and choices. A separate `battle_<id>_roster_recovery`
Attribute records the reason and egg references. Reconstruction does not replay
its declarations. Further player choices, persistent turns, synchronization and
concession/end writes refuse with the battle ID and an instruction to ask staff.
The tests prove that HP, PP, inventory, placement and the original checkpoint
remain unchanged. This policy deliberately requires staff recovery; boxing or
hatching later does not automatically clear a saved recovery marker.

Staff must retain and inspect the original `data`, `state`, `roster_recovery`,
canonical custody and any native-pair/resource receipts before proposing a
specific recovery or void operation. Do not change `is_egg`, weaken the owned
actor guard, delete/renumber party positions, or clear the marker merely to
resume a turn. This change authorizes no live recovery or administrative edits.

## Evidence limits and preservation

These are shipped parser/command and production battle/persistence tests over
random disposable PostgreSQL model-table schemas with captured player transport.
They are **not** live login/socket, deployment, migration-installed-trigger or
shared-server acceptance. Wild/trainer checks exercise production encounter
startup with labelled encounter fixtures, not world discovery. Egg, HP0/HP1,
bond, move/source and inventory prerequisites are separate setup; the hatched
control does not claim a real hatch wait. Original reproduction logs and full
private observations remain task-local; the companion JSON publishes bounded
observations and source/log hashes.

The task-owned SQL fixture was stopped after all schemas were removed; zero
disposable schemas and zero public tables remained. All **25** unrelated dirty
paths in the shared checkout retain their original status and raw-byte hashes.
No shared game data, stock, services or unrelated WIP was changed.

Structured results, source hashes, original egg checkpoint and command/resource
ledger: [battle-damp-egg-player-2026-10-26.json](battle-damp-egg-player-2026-10-26.json).
