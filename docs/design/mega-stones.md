# Existing Mega Stone rollout (#774)

Status: **47 canonical pairs implemented locally**. The
[first-pair acceptance](../testing/mega-core-2026-10-23.md) covers #784–#787;
the [per-stone expansion](../testing/mega-stones-2026-10-23.md) covers #788–#796.
CAP and required-move routes remain excluded. Source inventory/design
baseline: `1c36da6f449ce837455a65a1fa616013eee95c62`, October 22, 2026. Read the
[activation contract](mega-evolution.md) before implementing any pair. The
[machine-readable inventory](mega-stones.json) retains native/Mega base stats.

## Implementation issues

The first four issues supply the Venusaurite foundation; the later named
batches now have per-pair acceptance evidence. Closing #774 originally accepted the design alone.
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

All 47 named canonical stones have bounded ordinary command/effect/SQL
acceptance in the linked receipts. The historical catalog JSON retains its
original planning snapshot; this Markdown and the runtime explicit allowlist
record the current overlay. The CAP definition Crucibellite is excluded and
has no implementation issue. All 48 pairs preserve native HP base stats.

| Existing stone | Native species | Mega form | Mega types | Ability | Current status / owner |
| --- | --- | --- | --- | --- | --- |
| Abomasite | Abomasnow | Abomasnow-Mega | Grass / Ice | Snow Warning | Implemented locally / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) / [effects](../testing/mega-stones-2026-10-23.md) |
| Absolite | Absol | Absol-Mega | Dark | Magic Bounce | Implemented locally / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) / [effects](../testing/mega-stones-2026-10-23.md) |
| Aerodactylite | Aerodactyl | Aerodactyl-Mega | Rock / Flying | Tough Claws | Implemented locally / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) / [effects](../testing/mega-stones-2026-10-23.md) |
| Aggronite | Aggron | Aggron-Mega | Steel | Filter | Implemented locally / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) / [effects](../testing/mega-stones-2026-10-23.md) |
| Alakazite | Alakazam | Alakazam-Mega | Psychic | Trace | Implemented locally / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) / [effects](../testing/mega-stones-2026-10-23.md) |
| Altarianite | Altaria | Altaria-Mega | Dragon / Fairy | Pixilate | Implemented locally / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) / [effects](../testing/mega-stones-2026-10-23.md) |
| Ampharosite | Ampharos | Ampharos-Mega | Electric / Dragon | Mold Breaker | Implemented locally / [#795](https://github.com/PokemonFusion/Fusion2/issues/795) / [effects](../testing/mega-stones-2026-10-23.md) |
| Audinite | Audino | Audino-Mega | Normal / Fairy | Healer | Implemented locally / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) / [effects](../testing/mega-stones-2026-10-23.md) |
| Banettite | Banette | Banette-Mega | Ghost | Prankster | Implemented locally / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) / [effects](../testing/mega-stones-2026-10-23.md) |
| Beedrillite | Beedrill | Beedrill-Mega | Bug / Poison | Adaptability | Implemented locally / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) / [effects](../testing/mega-stones-2026-10-23.md) |
| Blastoisinite | Blastoise | Blastoise-Mega | Water | Mega Launcher | Implemented locally / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) / [effects](../testing/mega-stones-2026-10-23.md) |
| Blazikenite | Blaziken | Blaziken-Mega | Fire / Fighting | Speed Boost | Implemented locally / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) / [effects](../testing/mega-stones-2026-10-23.md) |
| Cameruptite | Camerupt | Camerupt-Mega | Fire / Ground | Sheer Force | Implemented locally / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) / [effects](../testing/mega-stones-2026-10-23.md) |
| Charizardite X | Charizard | Charizard-Mega-X | Fire / Dragon | Tough Claws | Implemented locally / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) / [effects](../testing/mega-stones-2026-10-23.md) |
| Charizardite Y | Charizard | Charizard-Mega-Y | Fire / Flying | Drought | Implemented locally / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) / [effects](../testing/mega-stones-2026-10-23.md) |
| Crucibellite | Crucibelle | Crucibelle-Mega | Rock / Poison | Magic Guard | Excluded CAP |
| Diancite | Diancie | Diancie-Mega | Rock / Fairy | Magic Bounce | Implemented locally / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) / [effects](../testing/mega-stones-2026-10-23.md) |
| Galladite | Gallade | Gallade-Mega | Psychic / Fighting | Inner Focus | Implemented locally / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) / [effects](../testing/mega-stones-2026-10-23.md) |
| Garchompite | Garchomp | Garchomp-Mega | Dragon / Ground | Sand Force | Implemented locally / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) / [effects](../testing/mega-stones-2026-10-23.md) |
| Gardevoirite | Gardevoir | Gardevoir-Mega | Psychic / Fairy | Pixilate | Implemented locally / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) / [effects](../testing/mega-stones-2026-10-23.md) |
| Gengarite | Gengar | Gengar-Mega | Ghost / Poison | Shadow Tag | Implemented locally / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) / [effects](../testing/mega-stones-2026-10-23.md) |
| Glalitite | Glalie | Glalie-Mega | Ice | Refrigerate | Implemented locally / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) / [effects](../testing/mega-stones-2026-10-23.md) |
| Gyaradosite | Gyarados | Gyarados-Mega | Water / Dark | Mold Breaker | Implemented locally / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) / [effects](../testing/mega-stones-2026-10-23.md) |
| Heracronite | Heracross | Heracross-Mega | Bug / Fighting | Skill Link | Implemented locally / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) / [effects](../testing/mega-stones-2026-10-23.md) |
| Houndoominite | Houndoom | Houndoom-Mega | Dark / Fire | Solar Power | Implemented locally / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) / [effects](../testing/mega-stones-2026-10-23.md) |
| Kangaskhanite | Kangaskhan | Kangaskhan-Mega | Normal | Parental Bond | Implemented locally / [#796](https://github.com/PokemonFusion/Fusion2/issues/796) / [effects](../testing/mega-stones-2026-10-23.md) |
| Latiasite | Latias | Latias-Mega | Dragon / Psychic | Levitate | Implemented locally / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) / [effects](../testing/mega-stones-2026-10-23.md) |
| Latiosite | Latios | Latios-Mega | Dragon / Psychic | Levitate | Implemented locally / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) / [effects](../testing/mega-stones-2026-10-23.md) |
| Lopunnite | Lopunny | Lopunny-Mega | Normal / Fighting | Scrappy | Implemented locally / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) / [effects](../testing/mega-stones-2026-10-23.md) |
| Lucarionite | Lucario | Lucario-Mega | Fighting / Steel | Adaptability | Implemented locally / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) / [effects](../testing/mega-stones-2026-10-23.md) |
| Manectite | Manectric | Manectric-Mega | Electric | Intimidate | Implemented locally / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) / [effects](../testing/mega-stones-2026-10-23.md) |
| Mawilite | Mawile | Mawile-Mega | Steel / Fairy | Huge Power | Implemented locally / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) / [effects](../testing/mega-stones-2026-10-23.md) |
| Medichamite | Medicham | Medicham-Mega | Fighting / Psychic | Pure Power | Implemented locally / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) / [effects](../testing/mega-stones-2026-10-23.md) |
| Metagrossite | Metagross | Metagross-Mega | Steel / Psychic | Tough Claws | Implemented locally / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) / [effects](../testing/mega-stones-2026-10-23.md) |
| Mewtwonite X | Mewtwo | Mewtwo-Mega-X | Psychic / Fighting | Steadfast | Implemented locally / [#795](https://github.com/PokemonFusion/Fusion2/issues/795) / [effects](../testing/mega-stones-2026-10-23.md) |
| Mewtwonite Y | Mewtwo | Mewtwo-Mega-Y | Psychic | Insomnia | Implemented locally / [#795](https://github.com/PokemonFusion/Fusion2/issues/795) / [effects](../testing/mega-stones-2026-10-23.md) |
| Pidgeotite | Pidgeot | Pidgeot-Mega | Normal / Flying | No Guard | Implemented locally / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) / [effects](../testing/mega-stones-2026-10-23.md) |
| Pinsirite | Pinsir | Pinsir-Mega | Bug / Flying | Aerilate | Implemented locally / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) / [effects](../testing/mega-stones-2026-10-23.md) |
| Sablenite | Sableye | Sableye-Mega | Dark / Ghost | Magic Bounce | Implemented locally / [#792](https://github.com/PokemonFusion/Fusion2/issues/792) / [effects](../testing/mega-stones-2026-10-23.md) |
| Salamencite | Salamence | Salamence-Mega | Dragon / Flying | Aerilate | Implemented locally / [#790](https://github.com/PokemonFusion/Fusion2/issues/790) / [effects](../testing/mega-stones-2026-10-23.md) |
| Sceptilite | Sceptile | Sceptile-Mega | Grass / Dragon | Lightning Rod | Implemented locally / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) / [effects](../testing/mega-stones-2026-10-23.md) |
| Scizorite | Scizor | Scizor-Mega | Bug / Steel | Technician | Implemented locally / [#788](https://github.com/PokemonFusion/Fusion2/issues/788) / [effects](../testing/mega-stones-2026-10-23.md) |
| Sharpedonite | Sharpedo | Sharpedo-Mega | Water / Dark | Strong Jaw | Implemented locally / [#791](https://github.com/PokemonFusion/Fusion2/issues/791) / [effects](../testing/mega-stones-2026-10-23.md) |
| Slowbronite | Slowbro | Slowbro-Mega | Water / Psychic | Shell Armor | Implemented locally / [#793](https://github.com/PokemonFusion/Fusion2/issues/793) / [effects](../testing/mega-stones-2026-10-23.md) |
| Steelixite | Steelix | Steelix-Mega | Steel / Ground | Sand Force | Implemented locally / [#794](https://github.com/PokemonFusion/Fusion2/issues/794) / [effects](../testing/mega-stones-2026-10-23.md) |
| Swampertite | Swampert | Swampert-Mega | Water / Ground | Swift Swim | Implemented locally / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) / [effects](../testing/mega-stones-2026-10-23.md) |
| Tyranitarite | Tyranitar | Tyranitar-Mega | Rock / Dark | Sand Stream | Implemented locally / [#789](https://github.com/PokemonFusion/Fusion2/issues/789) / [effects](../testing/mega-stones-2026-10-23.md) |
| Venusaurite | Venusaur | Venusaur-Mega | Grass / Poison | Thick Fat | Implemented locally / [receipt](../testing/mega-core-2026-10-23.md) |

## Availability and exclusions

The optional Counter lists only these 47 accepted stones at selected PF2
price 10,000 each, finite initial stock 1 each, and no automatic refill/resale.
Existing Venusaurite-only receipts fail drift checks instead of acquiring new
stock silently; a current-world source update needs separate review. No stock is created in a running world.
Configured sources, runtime support and released player acceptance remain
separate (#781/#782). The earlier #772 availability snapshots are dated evidence.

Rayquaza/Dragon Ascent has an internal required-move hook but no stone in this
inventory and no accepted player route. CAP, new ZA/other definitions, Z-Moves,
Ultra Burst, NPC Mega AI, plot Rings/Keys/quests and new battle formats remain
outside this plan. Existing Primal and item-forced forms keep their own rules.

The historical #757 and #772 reports remain unchanged. The
[validation receipt](../testing/mega-design-2026-10-22.md) records catalog
coverage and existing baseline tests, without claiming a new player command.
