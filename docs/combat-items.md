# Combat Items

This document defines the held-item policy for Fusion2 combat.

## Scope

Fusion2 uses a battle-first item policy:

- Keep held items that add clear tactical value in battle.
- Treat battle-runtime behavior as supported only when it is covered by battle-level tests.
- Defer or omit low-value canon baggage that does not improve MUD combat.

## Core Held Items

These item families are part of the supported combat surface and should keep battle coverage:

- Sustain and recovery: `Oran Berry`, `Sitrus Berry`, `Aguav Berry`, `Berry Juice`, `Leftovers`, `Black Sludge`
- Simple offensive and defensive staples: `Life Orb`, `Focus Sash`, `Assault Vest`, `Eviolite`, `Choice Band`, `Choice Scarf`, `Choice Specs`
- Readable tactical triggers: `Air Balloon`, `Rocky Helmet`, `Absorb Bulb`, `Cell Battery`, `Luminous Moss`, `Snowball`
- Terrain triggers when terrain support is active: `Electric Seed`, `Grassy Seed`, `Misty Seed`, `Psychic Seed`
- Type-resist berries when the one-shot super-effective trigger is implemented and tested
- Identity items only when their move or species mechanic is already supported: Plates, Memories, Drives, Natural Gift berries, Red/Blue Orb, forced-forme items

## Deferred Or Omitted

The following categories are not worth chasing for combat completeness unless a later feature explicitly needs them:

- Legacy transformation items for unsupported systems, including most Mega and Z-era item sets
- Mail, Apricorns, fossils, shards, and other non-combat inventory clutter
- Capture-only items in combat scope
- Redundant incense or one-off generational gimmicks that do not add meaningful battle decisions

## Support Rule

An item callback existing in `pokemon/dex/functions/items_funcs.py` is not enough to claim support. An item is only considered implemented when:

- the battle engine can reach its runtime hook through normal combat flow, and
- there is a battle-level test that proves the trigger, effect, and one-shot state handling work.

Use the offline battle testing workflow in [offline-battle-testing.md](offline-battle-testing.md)
for targeted held-item outcome tests and exhaustive item smoke checks.

## Item support evidence

The current [per-item reconciliation](testing/battle-item-support-2026-10-21.json)
accounts for all 576 loaded definitions: 283 retained battle/reward items have
declared outcome proof from the final local-player sweep; 293 definitions have
explicit scope exclusions. Each retained item links to exact checks and archived
evidence hashes. This is a battle-scope classification, so an excluded field item
is not thereby declared unsupported in every part of the game.

The [#757 closeout report](testing/item-support-closeout-2026-10-21.md) separates
fresh automated checks from historical ordinary-player evidence and publication
or deployment. Its matrix freezes 18 batches with exact item/check lists, at most
25 items and 50 battle templates each. New defects require separate bounded work.

The original [failure matrix](testing/battle-item-matrix-2026-10-20.json),
[post-repair sweep](testing/full-battle-items-postrepair-2026-10-20.md) and
[final post-form-repair sweep](testing/full-battle-postformfix-2026-10-20.md)
remain historical snapshots. Read them in that order; their results describe
their own builds. Callback resolution, assignment smoke, full Mega/Z systems,
acquisition and untested combinations do not become supported through this index.

Player-facing command/help availability remains coordinated through
[#731](https://github.com/PokemonFusion/Fusion2/issues/731). This reconciliation
changes test fixtures and evidence navigation; it adds no player commands or items.

## Supplemental held escape item

[Smoke Ball](smoke-ball.md) is a supplemental gameplay definition added after
the historical 576-definition reconciliation above. Its living acting holder
uses the normal `+flee` route in eligible wild encounters. It is reusable and
uses effective-item suppression; trainer/PvP and persisted server no-flee rules
take precedence. Capture routing requires canonical `isPokeball` metadata.
This addition has separate [command/model and regression evidence](testing/smoke-ball-2026-10-21.md);
it does not rewrite the pinned #757 matrix or expand plot-only item scope.

## Supplemental leader qualification item

[Leader's Crest](kingambit-evolution.md) marks authored native Bisharp leaders.
An owned Bisharp personally defeats three distinct qualifying leaders in won
NPC/wild encounters, gains the required level, then uses ordinary `+evolve`.
The player's Bisharp needs no Crest; equipped and bag copies are preserved.
This is a qualification role, with no new held combat-stat effect. Private
per-Pokemon evidence uses the existing battle receipts and evolution guards;
`+party <slot>` shows progress. Separate [command/model and regression evidence](testing/leader-crest-2026-10-21.md)
covers this later addition without changing the historical #757 matrix.

## Planned Mega activation

The [#774 activation contract](design/mega-evolution.md) selects Venusaurite as
the first non-plot `+mega` slice and defines side use, native identity, Tera,
suppression and cleanup rules. The [per-stone plan](design/mega-stones.md) assigns
all 47 canonical stones to bounded implementation work; Crucibellite is excluded
CAP content. The [Mega guide](mega-evolution.md) and
[per-pair acceptance](testing/mega-stones-2026-10-23.md) now record all 47
locally accepted canonical pairs. Historical battle-support classifications
remain dated evidence; deployment and live availability are separate.

The [Z-Move guide](z-moves.md) describes the 42 accepted generic/status/signature
mappings and `+zmove`, including Normalium Z/Tackle. The [35-crystal inventory](design/z-crystals.md) retains
explicit partial move/effect gates; other pairs and Ultra remain deferred.

## Native species stat and critical items

Light Ball, Thick Club, Deep Sea Scale, Deep Sea Tooth, Lucky Punch, Stick and
Leek use the holder's canonical native species, including each item's permitted
forms. Nicknames cannot grant or remove these bonuses. Their native bonuses
survive Transform; copying an eligible appearance cannot grant a foreign holder
the bonus. Stick permits Farfetch'd and its Galarian form; Leek also permits
Sirfetch'd. Metal Powder and Quick Powder require native, currently
untransformed Ditto and stop working after Transform.

All nine retain ordinary item suppression and normal `+hold` ownership rules.
The [#853 report](testing/native-stat-items-2026-10-25.md) records the exact
allowlists, local nickname/equip/battle command acceptance, outcomes and limits.
This bounded repair does not change item sources or the historical support
matrix. Legendary boosters have separate evidence below; removal protections
remain separate work.

## Native legendary type boosters

Adamant Orb/Crystal boost native Dialga's Steel and Dragon moves; Lustrous
Orb/Globe boost native Palkia's Water and Dragon moves; Griseous Orb/Core boost
native Giratina's Ghost and Dragon moves. Soul Dew boosts native Latias/Latios
Psychic and Dragon moves. All seven use canonical native base species, including
their legitimate forms, and preserve the existing integer `power × 1.2` rule.
Renaming cannot change eligibility. Their native bonuses survive Transform;
copying a legendary appearance cannot grant the bonus to a foreign holder.

Origin form-entry guards and suppression still apply separately. This repair
adds no Mega/Z profile, acquisition source, form activation or removal rule.
The [#854 report](testing/legendary-item-identity-2026-10-25.md) records the exact
forms/types, ordinary nickname/equip/battle cases and local validation limits.

## Native Plate removal protection

The 17 existing Plates protect against removal when either the holder or the
source is natively Arceus, including its canonical type forms. Nicknames and
copied appearances cannot grant that protection; a native Arceus keeps it after
renaming or Transform. This removal rule has no ability condition. Entering a
Plate's Arceus form still separately requires the existing native Multitype
checks. Every Plate retains its generic matching-type power boost for other
species.

Physical `TakeItem` checks still run under Magic Room, Embargo and Klutz;
ordinary item power effects remain suppressed. Thief, Knock Off, Trick and
Switcheroo share these removal checks. The [#855 report](testing/plate-theft-identity-2026-10-25.md)
records the exact item list, ordinary nickname/equip/attack/reconnect/end routes,
item conservation, rollback controls and local acceptance limits. Other item
families' identity protections and plot-only content are outside this repair.
