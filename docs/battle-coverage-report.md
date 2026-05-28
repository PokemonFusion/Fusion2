# Battle Outcome Proof Coverage Report

Generated: 2026-05-26

This report classifies loaded dex entries by offline proof status. Counts are
per loaded dex entry, so compatibility aliases can appear as duplicate entries.

## Status Summary

| Kind | Total | Explicit contracts | Mechanic contracts | Smoke only | Known gaps |
| --- | ---: | ---: | ---: | ---: | ---: |
| Move | 1904 | 234 | 1650 | 20 | 0 |
| Ability | 314 | 24 | 252 | 38 | 0 |
| Item | 575 | 1 | 7 | 567 | 0 |
| Pokemon | 1421 | 0 | 0 | 1421 | 0 |

## Move Mechanics

| Mechanic | Explicit | Mechanic | Smoke only | Known gaps | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Damage | 42 | 1234 | 0 | 0 | 1276 |
| Callback behavior | 180 | 436 | 20 | 0 | 636 |
| Random branch | 12 | 552 | 0 | 0 | 564 |
| Secondary effect | 4 | 408 | 0 | 0 | 412 |
| Stat boost/drop | 4 | 296 | 0 | 0 | 300 |
| Volatile | 2 | 278 | 0 | 0 | 280 |
| Status outcome | 6 | 168 | 0 | 0 | 174 |
| Callback damage | 32 | 132 | 0 | 0 | 164 |
| Priority | 4 | 108 | 0 | 0 | 112 |
| Side condition | 2 | 36 | 0 | 0 | 38 |
| Drain | 2 | 24 | 0 | 0 | 26 |
| Field condition | 14 | 12 | 0 | 0 | 26 |
| Recoil | 2 | 22 | 0 | 0 | 24 |
| Self switch | 2 | 16 | 0 | 0 | 18 |
| Healing | 2 | 12 | 0 | 0 | 14 |
| Combo move | 12 | 0 | 0 | 0 | 12 |
| Weather | 2 | 10 | 0 | 0 | 12 |
| Fixed damage | 8 | 0 | 0 | 0 | 8 |
| Forced switch | 2 | 6 | 0 | 0 | 8 |
| Terrain | 2 | 6 | 0 | 0 | 8 |
| No inferred mechanic | 2 | 0 | 0 | 0 | 2 |

## Ability And Item Mechanics

| Kind | Mechanic | Explicit | Mechanic | Smoke only | Known gaps | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Ability | Callback behavior | 13 | 252 | 38 | 0 | 303 |
| Ability | Ability damage modifier | 4 | 81 | 0 | 0 | 85 |
| Ability | Ability start | 2 | 67 | 0 | 0 | 69 |
| Ability | Ability move modifier | 1 | 48 | 0 | 0 | 49 |
| Ability | Ability immunity | 4 | 35 | 0 | 0 | 39 |
| Ability | Ability contact trigger | 1 | 37 | 0 | 0 | 38 |
| Ability | Ability weather | 1 | 24 | 0 | 0 | 25 |
| Ability | Ability boost guard | 1 | 19 | 0 | 0 | 20 |
| Ability | Ability residual | 1 | 12 | 0 | 0 | 13 |
| Ability | Ability control | 0 | 5 | 7 | 0 | 12 |
| Ability | Ability item trigger | 0 | 6 | 5 | 0 | 11 |
| Ability | Ability faint trigger | 0 | 3 | 7 | 0 | 10 |
| Ability | Ability post-battle item | 2 | 0 | 0 | 0 | 2 |
| Ability | Ability flag protection | 2 | 0 | 0 | 0 | 2 |
| Ability | Ability dance copy | 1 | 0 | 0 | 0 | 1 |
| Ability | Ability escape | 1 | 0 | 0 | 0 | 1 |
| Ability | Ability field duration | 1 | 0 | 0 | 0 | 1 |
| Ability | Ability ground immunity | 1 | 0 | 0 | 0 | 1 |
| Ability | Ability sleep modifier | 1 | 0 | 0 | 0 | 1 |
| Ability | Ability status bypass | 1 | 0 | 0 | 0 | 1 |
| Ability | No battle effect | 1 | 0 | 0 | 0 | 1 |
| Item | Callback behavior | 1 | 7 | 369 | 0 | 377 |
| Item | No inferred mechanic | 0 | 0 | 198 | 0 | 198 |
| Item | Item residual | 1 | 7 | 0 | 0 | 8 |

## Pokemon Mechanics

| Mechanic | Explicit | Mechanic | Smoke only | Known gaps | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| No inferred battle mechanic | 0 | 0 | 1114 | 0 | 1114 |
| Species/form behavior | 0 | 0 | 307 | 0 | 307 |
| Species requirements | 0 | 0 | 105 | 0 | 105 |

## Converted In Conversion Passes

These entries moved from smoke-only/broad behavior into explicit semantic
contracts:

- Fixed damage: Dragon Rage, Sonic Boom, Night Shade, Seismic Toss, plus Night Shade immunity.
- Callback-only support moves: Belly Drum, Heal Pulse, Aromatherapy, Heal Bell, Haze.
- Trapping callbacks: Block and Mean Look.
- Field pseudo-weather: Fairy Lock, Gravity, Magic Room, Mud Sport, Water Sport, Wonder Room.
- Healing and status callbacks: Synthesis, Morning Sun, Moonlight, Shore Up,
  Floral Healing, Jungle Healing, Lunar Blessing, Refresh, Rest, Take Heart,
  Purify, Swallow.
- Type and ability changes: Camouflage, Conversion, Conversion 2, Forest's
  Curse, Magic Powder, Reflect Type, Soak, Trick-or-Treat, Doodle,
  Entrainment, Role Play, Simple Beam, Skill Swap, Worry Seed, Transform.
- Stat, volatile, and HP callbacks: Defog, Flower Shield, Gear Up, Guard Swap,
  Heart Swap, Magnetic Flux, Pain Split, Perish Song, Power Swap, Psych Up,
  Quash, Rototiller, Spider Web, Strength Sap, Tidy Up, Topsy-Turvy,
  Venom Drench.
- Item and no-effect callbacks: Bestow, Corrosive Gas, Fling, Recycle, Stuff
  Cheeks, Switcheroo, Tea Time, Trick, Celebrate, Happy Hour, Hold Hands,
  Splash.
- Remaining callback reductions: Acupressure, Guard Split, Magnitude, Mimic,
  Natural Gift, Power Split, Psycho Shift, Sketch, Speed Swap, Spite.
- Ability proof reductions: Blaze, Adaptability, Huge Power, Aerilate, Iron
  Barbs, Speed Boost, Drizzle, Intimidate, and Clear Body now have exact
  semantic contracts for damage/stat calculations, move/type modification,
  contact damage, residual boosts, entry weather, entry stat drops, and boost
  guarding.
- No-battle-mechanic ability pass: No Ability, Ball Fetch, Corrosion, Dancer,
  Early Bird, Honey Gather, Levitate, Multitype, RKS System, Run Away, and
  Persistent now have explicit semantic proofs. The ability inventory has no
  remaining `No inferred mechanic` row.

The conversion work also added engine support for raw `damage` values,
level-based fixed damage, type immunity for fixed damage, pseudo-weather moves,
Fling's held-item base power, Rest replacing an existing status with sleep, and
boost-swap callbacks reading normalized stat keys. The harness now also captures
type, species, ability, raw stat, move-slot, and last-move snapshots. Ability
proofing added an entry/start outcome runner and damage expectations for
calculated attack and defense values.

## Remaining Priority Queue

1. High-risk callback-only moves still smoke-only:
   After You, Assist, Copycat, Court Change, Instruct, Me First, Metronome,
   Mirror Move, Nature Power, Sleep Talk.
2. Several remaining moves require additional harness observability:
   battle queue order, side-condition swapping setup, dynamically called moves,
   selected move queues, and sleep-call move execution.
3. Remaining ability smoke-only groups:
   unique callback-only abilities, faint-trigger abilities, trapping/control
   abilities, and item-triggered abilities. Current smoke-only abilities: 38
   entries; none are in the no-inferred-mechanic bucket.
4. Item callback families still mostly smoke-only:
   berries, type-boosting items, Gems, Choice items, Assault Vest, Air Balloon,
   damage-triggered items, item-removal interactions, and form-changing items.
5. Pokemon species/form behavior:
   currently all species/form entries are smoke-only unless their behavior is
   indirectly covered by move, ability, or item contracts.

## Commands

```powershell
$env:PYTHONPATH = "fusion2"; .\evenv\Scripts\python.exe -m tests.battle_contract_coverage
.\evenv\Scripts\python.exe -m pytest fusion2\tests\test_battle_semantic_contracts.py -q
.\evenv\Scripts\python.exe -m pytest fusion2\pokemon\battle\tests\test_generated_move_callbacks.py --run-callback-tests -q
```
