# Existing incense boosters

These five existing held items have current-build automated player-command
coverage. Equip a bag copy with `+hold 3=Odd Incense`, then choose a legal move
with `+attack A1 Psychic` in an ordinary battle. Equip before battle; `+hold`
cannot change equipment during battle. Use `+hold 3=` afterward to return a
held copy to the bag. Replacing it returns the old item and equips the new one.

| Item | Boosted move type | Tested matching move | PF2 base power |
| --- | --- | --- | --- |
| Odd Incense | Psychic | Psychic | 90 → 108 |
| Rock Incense | Rock | Power Gem | 80 → 96 |
| Rose Incense | Grass | Energy Ball | 90 → 108 |
| Sea Incense | Water | Surf | 90 → 108 |
| Wave Incense | Water | Surf | 90 → 108 |

The matching-type base-power multiplier is 1.2, following the reviewed
[primary item rules](https://github.com/smogon/pokemon-showdown/blob/master/data/items.ts).
PF2 uses integer base power followed by its existing damage rounding, STAB,
effectiveness and variance rules. Final HP loss need not be exactly 20% larger.
Nonmatching moves receive no boost. Ordinary attacks do not consume incense;
repeated uses do not compound or rewrite the shared move definition.

Magic Room, Embargo and Klutz disable the boost while preserving the held item.
Magic Room ending restores the boost. Ordinary Knock Off removes the runtime
item; an explicit empty held-item checkpoint prevents it returning on rebuild.
Normal equip/removal/replacement, saved held state, queued moves and suppressed
state are tested through the production session/checkpoint routes.

The confirmed repair makes offensive item hooks use the existing effective-item
resolver rather than raw held ownership. Ability and item power results now
compose in order: native Sand Force Gigalith keeps Rock Incense's boost in clear
weather and combines both boosts in sandstorm. Existing integer rounding gives
Power Gem 80 → 104 from Sand Force, then 104 → 124 with Rock Incense.
Item definitions, boost magnitudes, move rules, breeding and incense offspring
behavior are unchanged.

The [October 22 report](testing/incense-2026-10-22.md) and
[per-item evidence](testing/incense-2026-10-22.json) qualify these tested contexts
on the reported build. They supplement the historical #757 support matrix;
its exclusions and older battle observations remain unchanged. These are local
automated ordinary `+hold`/`+attack` production-command/model checks with real
private PostgreSQL and captured session transport. They do not establish a new
live-player login, hosted CI completion, main merge or deployment.

All five dex entries retain their existing generation, Fling power 10 and
`Past` availability metadata. Itemdex descriptions and reference prices are
metadata, not proof of current shop/world obtainability. Disposable fixture
stock is explicit setup; current obtainable coverage remains #772. New items,
plot-only content, breeding, offspring rules and broader incense systems remain
outside this verification.
