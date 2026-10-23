# Existing Mega Stone rollout (#774)

Status: **one implemented pair: Venusaurite**. The
[local acceptance](../testing/mega-core-2026-10-23.md) covers #784–#787;
46 other canonical pairs retain their gates. Source inventory/design
baseline: `1c36da6f449ce837455a65a1fa616013eee95c62`, October 22, 2026. Read the
[activation contract](mega-evolution.md) before implementing any pair. The
[machine-readable inventory](mega-stones.json) retains native/Mega base stats.

## Implementation issues

The first four issues supply the accepted Venusaurite slice; later batches remain
implementation work. Closing #774 originally accepted the design alone.
Complete the first four gates before extending the
allowlist. Each later batch requires real per-pair effects and ordinary player
purchase/equip/activation/rebuild/cleanup evidence; callback presence is insufficient.

| Issue | Deliverable | Dependencies |
| --- | --- | --- |
| [#784](https://github.com/PokemonFusion/Fusion2/issues/784) | Add guarded Venusaurite Mega effects and side reservations | #774 design |
| [#785](https://github.com/PokemonFusion/Fusion2/issues/785) | Persist Mega state and integrate Tera, switches and cleanup | #784 |
| [#786](https://github.com/PokemonFusion/Fusion2/issues/786) | Enable and accept the Venusaurite +mega player route | #784, #785 |
| [#787](https://github.com/PokemonFusion/Fusion2/issues/787) | Author an opt-in Venusaurite shop and purchase-to-Mega walkthrough | #786 |
| [#788](https://github.com/PokemonFusion/Fusion2/issues/788) | Enable six contact and offensive Mega Stone pairs | #786, #787 |
| [#789](https://github.com/PokemonFusion/Fusion2/issues/789) | Enable six weather, entry and speed Mega Stone pairs | #786, #787, #788 |
| [#790](https://github.com/PokemonFusion/Fusion2/issues/790) | Enable six type-conversion and Skill Link Mega Stone pairs | #786, #787 |
| [#791](https://github.com/PokemonFusion/Fusion2/issues/791) | Enable six move-power and coverage Mega Stone pairs | #786, #787 |
| [#792](https://github.com/PokemonFusion/Fusion2/issues/792) | Enable six reflection, priority and trapping Mega Stone pairs | #786, #787 |
| [#793](https://github.com/PokemonFusion/Fusion2/issues/793) | Enable six defensive and immunity Mega Stone pairs | #786, #787 |
| [#794](https://github.com/PokemonFusion/Fusion2/issues/794) | Enable six environment, support and accuracy Mega Stone pairs | #786, #787 |
| [#795](https://github.com/PokemonFusion/Fusion2/issues/795) | Enable Ampharosite and both Mewtwonite branches | #786, #787 |
| [#796](https://github.com/PokemonFusion/Fusion2/issues/796) | Enable Kangaskhanite with real Parental Bond turn effects | #786, #787 |

Venusaurite is the first pair: #784 provides effects/guards, #785 durable state
and transformation interactions, #786 the accepted normal `+mega` route, and
#787 the opt-in source recipe. Remaining batches contain six, six, six, six,
six, six, six, three and one pairs respectively: 46 distinct stones. #789 also
depends on #788 for the first Charizard branch precedent. Kangaskhanite is
separate because its actual Parental Bond multi-hit effects need dedicated proof.

## Per-item status

Venusaurite now has bounded ordinary command/effect/SQL acceptance; the other
46 canonical stones remain **deferred implementation**. Their target stats/types/abilities are observations of local data,
not verified player support. The CAP definition Crucibellite is excluded and
has no implementation issue. All 48 pairs preserve native HP base stats.

| Existing stone | Native species | Mega form | Mega types | Ability | Current status / owner |
| --- | --- | --- | --- | --- | --- |
| Abomasite | Abomasnow | Abomasnow-Mega | Grass / Ice | Snow Warning | Deferred / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) |
| Absolite | Absol | Absol-Mega | Dark | Magic Bounce | Deferred / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) |
| Aerodactylite | Aerodactyl | Aerodactyl-Mega | Rock / Flying | Tough Claws | Deferred / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) |
| Aggronite | Aggron | Aggron-Mega | Steel | Filter | Deferred / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) |
| Alakazite | Alakazam | Alakazam-Mega | Psychic | Trace | Deferred / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) |
| Altarianite | Altaria | Altaria-Mega | Dragon / Fairy | Pixilate | Deferred / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) |
| Ampharosite | Ampharos | Ampharos-Mega | Electric / Dragon | Mold Breaker | Deferred / [#795](https://github.com/PokemonFusion/Fusion2/issues/795) |
| Audinite | Audino | Audino-Mega | Normal / Fairy | Healer | Deferred / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) |
| Banettite | Banette | Banette-Mega | Ghost | Prankster | Deferred / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) |
| Beedrillite | Beedrill | Beedrill-Mega | Bug / Poison | Adaptability | Deferred / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) |
| Blastoisinite | Blastoise | Blastoise-Mega | Water | Mega Launcher | Deferred / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) |
| Blazikenite | Blaziken | Blaziken-Mega | Fire / Fighting | Speed Boost | Deferred / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) |
| Cameruptite | Camerupt | Camerupt-Mega | Fire / Ground | Sheer Force | Deferred / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) |
| Charizardite X | Charizard | Charizard-Mega-X | Fire / Dragon | Tough Claws | Deferred / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) |
| Charizardite Y | Charizard | Charizard-Mega-Y | Fire / Flying | Drought | Deferred / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) |
| Crucibellite | Crucibelle | Crucibelle-Mega | Rock / Poison | Magic Guard | Excluded CAP |
| Diancite | Diancie | Diancie-Mega | Rock / Fairy | Magic Bounce | Deferred / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) |
| Galladite | Gallade | Gallade-Mega | Psychic / Fighting | Inner Focus | Deferred / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) |
| Garchompite | Garchomp | Garchomp-Mega | Dragon / Ground | Sand Force | Deferred / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) |
| Gardevoirite | Gardevoir | Gardevoir-Mega | Psychic / Fairy | Pixilate | Deferred / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) |
| Gengarite | Gengar | Gengar-Mega | Ghost / Poison | Shadow Tag | Deferred / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) |
| Glalitite | Glalie | Glalie-Mega | Ice | Refrigerate | Deferred / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) |
| Gyaradosite | Gyarados | Gyarados-Mega | Water / Dark | Mold Breaker | Deferred / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) |
| Heracronite | Heracross | Heracross-Mega | Bug / Fighting | Skill Link | Deferred / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) |
| Houndoominite | Houndoom | Houndoom-Mega | Dark / Fire | Solar Power | Deferred / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) |
| Kangaskhanite | Kangaskhan | Kangaskhan-Mega | Normal | Parental Bond | Deferred / [#796](https://github.com/PokemonFusion/Fusion2/issues/796) |
| Latiasite | Latias | Latias-Mega | Dragon / Psychic | Levitate | Deferred / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) |
| Latiosite | Latios | Latios-Mega | Dragon / Psychic | Levitate | Deferred / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) |
| Lopunnite | Lopunny | Lopunny-Mega | Normal / Fighting | Scrappy | Deferred / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) |
| Lucarionite | Lucario | Lucario-Mega | Fighting / Steel | Adaptability | Deferred / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) |
| Manectite | Manectric | Manectric-Mega | Electric | Intimidate | Deferred / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) |
| Mawilite | Mawile | Mawile-Mega | Steel / Fairy | Huge Power | Deferred / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) |
| Medichamite | Medicham | Medicham-Mega | Fighting / Psychic | Pure Power | Deferred / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) |
| Metagrossite | Metagross | Metagross-Mega | Steel / Psychic | Tough Claws | Deferred / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) |
| Mewtwonite X | Mewtwo | Mewtwo-Mega-X | Psychic / Fighting | Steadfast | Deferred / [#795](https://github.com/PokemonFusion/Fusion2/issues/795) |
| Mewtwonite Y | Mewtwo | Mewtwo-Mega-Y | Psychic | Insomnia | Deferred / [#795](https://github.com/PokemonFusion/Fusion2/issues/795) |
| Pidgeotite | Pidgeot | Pidgeot-Mega | Normal / Flying | No Guard | Deferred / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) |
| Pinsirite | Pinsir | Pinsir-Mega | Bug / Flying | Aerilate | Deferred / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) |
| Sablenite | Sableye | Sableye-Mega | Dark / Ghost | Magic Bounce | Deferred / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) |
| Salamencite | Salamence | Salamence-Mega | Dragon / Flying | Aerilate | Deferred / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) |
| Sceptilite | Sceptile | Sceptile-Mega | Grass / Dragon | Lightning Rod | Deferred / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) |
| Scizorite | Scizor | Scizor-Mega | Bug / Steel | Technician | Deferred / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) |
| Sharpedonite | Sharpedo | Sharpedo-Mega | Water / Dark | Strong Jaw | Deferred / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) |
| Slowbronite | Slowbro | Slowbro-Mega | Water / Psychic | Shell Armor | Deferred / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) |
| Steelixite | Steelix | Steelix-Mega | Steel / Ground | Sand Force | Deferred / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) |
| Swampertite | Swampert | Swampert-Mega | Water / Ground | Swift Swim | Deferred / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) |
| Tyranitarite | Tyranitar | Tyranitar-Mega | Rock / Dark | Sand Stream | Deferred / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) |
| Venusaurite | Venusaur | Venusaur-Mega | Grass / Poison | Thick Fat | Implemented locally / [receipt](../testing/mega-core-2026-10-23.md) |

## Availability and exclusions

The optional Counter starts with Venusaurite only at selected PF2 price 10,000,
finite stock 1, and no automatic refill. Later accepted batches may extend only
their own offers under the same policy. No stock is created in a running world.
Configured sources, runtime support and released player acceptance remain
separate (#781/#782). The earlier #772 availability snapshots are dated evidence.

Rayquaza/Dragon Ascent has an internal required-move hook but no stone in this
inventory and no accepted player route. CAP, new ZA/other definitions, Z-Moves,
Ultra Burst, NPC Mega AI, plot Rings/Keys/quests and new battle formats remain
outside this plan. Existing Primal and item-forced forms keep their own rules.

The historical #757 and #772 reports remain unchanged. The
[validation receipt](../testing/mega-design-2026-10-22.md) records catalog
coverage and existing baseline tests, without claiming a new player command.
