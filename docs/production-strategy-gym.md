# Tempo Gym: production strategy reference

September Week 4 / #712 ships one standalone introductory gym. Cadence and the
Tempo Badge are authored content, without assigning them a canonical map region.
Players discover and launch the gym through `+gym list`, `+gym check tempo_gym`
and `+gym challenge tempo_gym`. No badge prerequisite or Builder command is needed.

## Configuration and roster

`GymLeaderProfile` now stores the battle format, AI profile, bounded strategy key,
content stage, introduction/rules/result text, reward policy and rematch cooldown.
The only supported strategy primitive is `trick_room`, paired with doubles and
the explicit `gym_trick_room` profile. Unknown/mismatched configuration fails
before battle allocation. Existing gyms default to singles and legacy rewards.

The installer owns `independent:tempo_gym`, leader `Gym Leader Cadence`, badge
`Tempo Badge` and three stable roster keys. All members are level 20, Hardy, with
zero IVs/EVs and no held items. HP comes from those saved template stats, not a
randomly generated substitute.

| Role | Pokémon | Ability | Moves |
| --- | --- | --- | --- |
| Setter | Slowbro | Own Tempo | Trick Room, Water Gun, Heal Pulse, Protect |
| Support/setter | Slowking | Own Tempo | Trick Room, Water Gun, Recover, Helping Hand |
| Reserve attacker | Snorlax | Immunity | Tackle, Body Slam, Protect, Rest |

The AI establishes room against faster teams, avoids its own duplicate toggle,
and supports an eligible ally. Room does not change move priority. Its duration,
source references, profile, both pending actions and reserve roster survive
battle-session rebuilds. Later profile edits do not rewrite an existing battle's
snapshot. See [the scoring rules](battle-ai-scoring.md).

## Reward and retry policy

- First clear awards one badge. Badge delivery and `GymVictory.claimed_at` plus
  `award_kind` commit atomically under the character row lock.
- Every attempt, including first clears, losses, concessions and rematches,
  gives no Pokémon XP, EVs, trainer XP, money or item reward. Gym opponents hold
  no items. Ordinary battle HP, PP, status and player item costs still apply.
- A rematch is practice. It awards no second badge or other repeat reward and
  is available 24 hours after the character's last confirmed victory.
- Losses, concessions and aborted starts create no victory receipt or new
  cooldown. First-clear retries are immediate; an expired rematch cooldown is
  not restarted by a loss. An aborted session cannot later award a delayed win.
- A pending award blocks another challenge. `+gym claim` retries it without a
  healthy party or another battle. Missing prerequisites remain pending.
- Replay retains the original receipt metadata and delivery classification.
  Competing claims for separate wins classify exactly one as a first clear.

Production launch locks the character and profile, rereads eligibility and
requires two conscious party actors. Session allocation, encounter rows, battle
locks and checkpoints share a transaction. Failure rolls them back and releases
only that failed attempt's runtime references. Concurrent launch attempts cannot
start two battles for the same character.

## Installation and update

Migration `0045_production_strategy_gym` must be applied through the approved
deployment procedure before the new code is loaded by a running server.
It preserves existing badges, rosters, victories and progression. Installed
`alpha:alpha_gym` profiles become test content. The Alpha seed also explicitly
marks its content as test, so rerunning it cannot expose that gym through the
normal player command. Builder diagnostics remain available for test content.

After schema/code deployment, run the Django management command
`seed_production_gym` from the game directory. It updates this gym's existing
identities under a leader row lock, then disables the old Alpha profile.
It does not reset earned badges, receipts or cooldown history. Concurrent and
repeated runs preserve one profile, one badge and three owned roster rows.
Unexpected roster keys, duplicates or conflicting leader links fail atomically
for review instead of deleting staff-authored content.

Any migration application and Evennia restart/reload require the repository's
explicit operational approval. Before reverting to code without these policy
fields, disable the Tempo profile; older code cannot enforce its reward policy.

## Validation and acceptance

`tests/test_gym_policy.py` checks bounded configuration and explicit aliases.
`tests/integration/production_gym_cases.py` exercises the normal player command,
full first-clear/rematch engine battles, real PostgreSQL claims and row locking,
installer reruns, failed-start rollback, pending delivery, loss/concession/abort,
profile edits and rebuilds. It captures player transport while using real models,
commands and transactions. The lifecycle workflow includes these scenarios.

`tests/integration/migration_graph.py` compares the graph's profile/victory field
state with the models without applying migrations. The approval-gated
`tests/integration/recovery_migrations.py` includes fresh installs and an upgrade
from 0044, preserving installed Alpha configuration, badge ownership and pending
victories. It runs only inside disposable PostgreSQL schemas.

Live acceptance remains a separate record. After approved local deployment:

1. With an ordinary QA character, discover/check the gym and confirm Alpha is
   absent. Verify the two-conscious-actor requirement and visible badge-only rules.
2. Start a doubles challenge, observe Trick Room and its reversed speed order,
   then save/reload mid-battle. Confirm the roster, profile, room duration and
   both selected actors remain valid after reconnect.
3. Complete a battle and verify one badge, first-clear messaging, unchanged
   progression/inventory rewards and a rematch cooldown. A loss or concession
   must grant nothing and permit retry after healing.
4. Verify staff diagnostics and installed configuration separately. Record
   ordinary-player results separately from Builder/admin checks. Fault injection
   and forced cooldown expiry belong in disposable test schemas, not real-player
   progression records.

These automated scenarios do not claim human playtesting or completed live
Evennia acceptance. Migration rehearsal and live deployment must be recorded
when they are actually performed.
