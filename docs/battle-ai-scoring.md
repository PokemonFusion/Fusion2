# Doubles and situational AI scoring

September Week 3 / #711 extends the existing legal-action and profile pipeline.
`AIActionScorer` binds each score to its executable move, actor and target; the
existing profile candidate band and seeded weighted chooser select the action.
Each active actor gets an independent choice. PP, Disable, Encore, Taunt,
target legality, active slots and reserve availability remain the responsibility
of `LegalActions`.

## Targets and damage

- Single-target moves score each legal foe separately. Ordinary attacks on an
  ally are excluded from AI preferences. Permitted ally healing and Helping
  Hand are evaluated for their specific recipient. Pure healing gives no value
  to an enemy recipient; an equally ineffective ally heal precedes that fallback.
- Spread moves use the complete conscious target set supplied by `LegalActions`,
  including allies for `allAdjacent`. Each target contributes the existing
  profile-weighted damage baseline, with a 0.75 spread modifier when more than
  one battler is affected. A pure level/stat/STAB/type estimate adds a bounded
  45-point profile-weighted bonus for an apparent knockout.
- Supported spread status and stat changes sum the eligible recipients' bounded
  utilities, so a second foe or ally matters and a fainted recipient adds none.
- Friendly damage subtracts 1.5 times the ally's damage baseline. Visible type
  immunity and the AI's own ally's known absorbing ability remove that cost.
  Estimated lethal friendly damage sets the action's utility to zero. If every
  choice has zero utility, a harmless legal choice precedes lethal friendly fire.
- Damage scores retain their relative scale; utility actions have the explicit
  limits below. These estimates do not run move callbacks or simulate a turn.

## Situational utility

These are intentionally small heuristics for supported primitives, rather than
a complete evaluation of every move callback. Status-move accuracy scales the
result. A profile that does not allow an intent limits it to the existing move
baseline. Unknown utility keeps that baseline, and Struggle remains the shared
legality fallback.

| Primitive | Rule and bound |
| --- | --- |
| Recovery | No value at full HP, below a 20% deficit, under Heal Block, or for an enemy. Per recipient, `min(230, 160 * recoverable_fraction + 170 * missing_fraction)`. Recoverable HP is capped at the move's healing fraction. Covers raw `heal` and Heal Pulse, Floral Healing, ally Pollen Puff, Jungle Healing and Lunar Blessing. Group healing sums eligible active recipients. |
| Helping Hand | Needs an eligible conscious ally with a legal damaging move, PP, priority at most +3 and no completed action. If that ally already has an own-side declaration, it must be an attack. Utility is 60% of its best foe damage baseline, capped at 150. |
| Major status | Starts at 85, rejects occupied status slots and core type immunities, including Ground immunity to Thunder Wave. Burn gets a 1.35 physical-attacker multiplier or 0.6 otherwise. A target at quarter HP gets 0.4. Paralysis under Trick Room gets 0.3. Maximum 114.75 before accuracy. |
| Stat setup/debuff | Values only available stages in the useful direction, diminished by existing stages, at 55 per stage and capped at 140 per recipient. Friendly setup requires at least half HP; offensive setup requires a legal own attack with PP in the relevant category. Speed boosts and foe speed drops get no value while Trick Room is active. |
| Protect | Needs visible foe burn/poison residual, Leftovers or a Poison-type Black Sludge holder without Heal Block, or an injured actor covering an ally that can attack. Utility is 95, or 160 at one-third HP or less, divided by the existing consecutive-use `stall.counter`. No inferred opponent choice is read. |

Already selected actions from the same AI side are passed to subsequent actors.
This prevents duplicate Trick Room toggles, suppresses Helping Hand for an ally
that has committed to switching, and avoids duplicate raw-heal declarations
for the same recipient. This is bounded coordination of the AI's own choices.
Opponent movesets, pending choices and future decisions are not inspected.

## Selected gym strategy: Trick Room speed control

The explicit `gym_trick_room` profile inherits `gym_leader` weights and sets
`strategy_key="trick_room"`. `trick_room` and `gym_speed_control` are aliases.
Generic gym profiles do not acquire this strategy implicitly.

For each conscious ally/foe pair, compare current battle speed including stat
stages and paralysis. Average +1 for a slower ally, -1 for a faster ally and 0
for a tie. An actor at least half healthy values setting Trick Room at
`210 * advantage` only when advantage is at least 0.5. Existing beneficial room
gets zero toggle value; an existing room harming the side can be removed using
the reversed advantage. A slower actor's ordinary-priority attack gains an 8%
damage-value bonus under room. Immediate strong attacks can still outrank setup.
No other weather, terrain or hazard strategy is added here.

Trick Room now retains its structured five-turn duration (seven for Persistent),
source and field references. The activation turn's residual counts as the first
turn. Duration advances once per residual and removal runs the field-end event.
Legacy boolean room checkpoints receive a bounded five-residual remaining
lifetime because their original remaining duration was not saved.

## Persistence and inspection

The engine and `BattleData` share the live field. Field and Pokémon references
in effect state serialize as markers, then reconnect to the rebuilt field and
roster. This avoids pickling the live field/ORM graph. AI profile metadata and
each actor's pending declaration use the existing trainer encounter checkpoint
path. When a saved AI target disappears, the legal replacement action is also
reflected in its saved target declaration for subsequent rebuilds.

The staff-only `+aidebug` score rows include logical target slots and the full
spread set, as well as intent and reason codes. Old traces without target labels
still render. Debug traces are runtime diagnostics, not persistent battle state.

An encounter can opt in with `ai_profile="gym_trick_room"` and
`battle_format="double"`. Durable production gym configuration, authored roster,
challenge/reward content and live gym acceptance belong to #712. This change
does not install a gym, change the database schema or reload the game service.

## Validation

`tests/battle/test_ai_action_scoring.py` covers individual and spread targets, permitted
ally support, status, setup, recovery, Protect, room decisions, source-state
purity, fainting, duration and serializable field references.
`tests/integration/ai_scoring_cases.py` uses real gym generation, ordinary-player
models, battle sessions, engine turns and isolated PostgreSQL schemas to verify
two pending choices, profiles, target recovery, HP, PP, Protect, room ordering
and expiry through repeated rebuilds. Player transport alone is captured.
The lifecycle-integrity workflow runs these cases alongside the existing legal
AI, doubles, recovery and mandatory combined-suite gates.

Automated ordinary-player session coverage and staff command tests do not claim
manual Evennia acceptance or a deployed production gym.
