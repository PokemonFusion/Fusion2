# Existing Z-Crystal implementation plan (#775)

Status: **63 explicit mappings on 35 crystals accepted locally**: 32 generic
damage sources, 14 status sources, 16 signatures and one guarded Ultra profile. [Foundation evidence](../testing/z-core-2026-10-23.md),
[status/signature evidence](../testing/z-special-2026-10-23.md) and [player guide](../z-moves.md).
Other unreviewed ordinary/status sources remain deferred. The separate
[Ultra route](../ultra-burst.md) uses its reviewed native-pair and held-crystal
guards; [its dated evidence](../testing/ultra-burst-2026-10-25.md) does not certify
a newer checkout or public stock. The two
[live-pair-proved Necrozma lifecycles](necrozma-combination.md) now pass
[local acceptance](../testing/necrozma-items-2026-10-24.md) for #825–#830.
They extend holder eligibility for the same two signatures; that earlier
42-mapping/34-crystal/16-signature inventory and native fingerprints remain
historical. [#863's separate expansion](../testing/z-existing-sources-2026-10-25.md)
adds only Flamethrower and Surf; all16 signature profiles remain unchanged.
[Released local socket acceptance](../testing/necrozma-released-retry-2026-10-24.md) passes for #831. No shared-game
deployment, permanent source or stock installation is asserted.
Read the [activation contract](z-moves.md). The [JSON inventory](z-crystals.json)
retains local crystal/source/holder metadata. This fresh enumeration found 18
generic plus 17 signature definitions; the earlier combined audit count is
historical and is not used as the current catalog denominator.

## Implementation issues

| Issue | Deliverable | Depends on |
| --- | --- | --- |
| [#797](https://github.com/PokemonFusion/Fusion2/issues/797) | Implement guarded Normalium Z / Tackle action effects | #775 design |
| [#798](https://github.com/PokemonFusion/Fusion2/issues/798) | Persist Z declarations and integrate battle mechanic budgets | #797 |
| [#799](https://github.com/PokemonFusion/Fusion2/issues/799) | Accept the Normalium Z player command and opt-in source | #797, #798 |
| [#800](https://github.com/PokemonFusion/Fusion2/issues/800) | Accept 6 generic Z-Crystal damage slices (1) | #799 |
| [#801](https://github.com/PokemonFusion/Fusion2/issues/801) | Accept 6 generic Z-Crystal damage slices (2) | #799 |
| [#802](https://github.com/PokemonFusion/Fusion2/issues/802) | Accept 5 generic Z-Crystal damage slices (3) | #799 |
| [#803](https://github.com/PokemonFusion/Fusion2/issues/803) | Accept bounded Z status boosts and self-healing effects | #799 |
| [#804](https://github.com/PokemonFusion/Fusion2/issues/804) | Accept bounded special Z status effects and move restrictions | #803 |
| [#805](https://github.com/PokemonFusion/Fusion2/issues/805) | Accept four existing signature Z-Crystal routes (1) | #799 |
| [#806](https://github.com/PokemonFusion/Fusion2/issues/806) | Accept four existing signature Z-Crystal routes (2) | #799 |
| [#807](https://github.com/PokemonFusion/Fusion2/issues/807) | Accept four existing signature Z-Crystal routes (3) | #799 |
| [#808](https://github.com/PokemonFusion/Fusion2/issues/808) | Accept four existing signature Z-Crystal routes (4) | #799 |

The accepted generic list retains each crystal's first reviewed damaging source,
including Normalium Z/Tackle, Flamethrower/Firium Z, Surf/Waterium Z and
the six [#910 special sources](../testing/z-six-special-sources-2026-10-25.md) and
six [#911 physical sources](../testing/z-six-physical-sources-2026-10-25.md).
The six [#912 status sources](../testing/z-six-status-sources-2026-10-25.md)
follow qualified ordinary-move prerequisites; the other status sources stay deferred.
These remain **partial** support; other
source moves require their own explicit effect and player-route gates. Status issues select at most
six mappings each; other status, variable, called and restricted combinations
stay deferred. Signature groups contain four crystals each and require exact
native-holder/source/effect proof; missing native access becomes a prerequisite.

## Per-item status

| Existing crystal | Family / type | Native holder restriction | Source move | Current status / owner |
| --- | --- | --- | --- | --- |
| Aloraichium Z | Signature | Raichu-Alola | Thunderbolt → Stoked Sparksurfer, 175 Special | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Buginium Z | Generic / Bug | Any eligible native holder | Bug Bite → Savage Spin-Out, 120 Physical; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Darkinium Z | Generic / Dark | Any eligible native holder | Bite → Black Hole Eclipse, 120 Physical; status: Memento; Crunch → Black Hole Eclipse, 160 Physical; other sources deferred | Accepted bounded pairs / [#800](https://github.com/PokemonFusion/Fusion2/issues/800), [#911](https://github.com/PokemonFusion/Fusion2/issues/911) |
| Decidium Z | Signature | Decidueye | Spirit Shackle → Sinister Arrow Raid, 180 Physical | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Dragonium Z | Generic / Dragon | Any eligible native holder | Dragon Breath → Devastating Drake, 120 Special; Dragon Claw → Devastating Drake, 160 Physical; other sources deferred | Accepted bounded pairs / [#800](https://github.com/PokemonFusion/Fusion2/issues/800), [#911](https://github.com/PokemonFusion/Fusion2/issues/911) |
| Eevium Z | Signature | Eevee | Last Resort → Extreme Evoboost, Status | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Electrium Z | Generic / Electric | Any eligible native holder | Thunder Shock → Gigavolt Havoc, 100 Special; Thunderbolt → Gigavolt Havoc, 175 Special; status: Thunder Wave gives user Special Defense +1; other sources deferred | Accepted bounded pairs / [#800](https://github.com/PokemonFusion/Fusion2/issues/800), [#910](https://github.com/PokemonFusion/Fusion2/issues/910), [#912](https://github.com/PokemonFusion/Fusion2/issues/912) |
| Fairium Z | Generic / Fairy | Any eligible native holder | Fairy Wind → Twinkle Tackle, 100 Special; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Fightinium Z | Generic / Fighting | Any eligible native holder | Karate Chop → All-Out Pummeling, 100 Physical; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Firium Z | Generic / Fire | Any eligible native holder | Ember → Inferno Overdrive,100 Special; Flamethrower → Inferno Overdrive,175 Special; other sources deferred | Accepted bounded pairs / [#801](https://github.com/PokemonFusion/Fusion2/issues/801), [#863](https://github.com/PokemonFusion/Fusion2/issues/863) |
| Flyinium Z | Generic / Flying | Any eligible native holder | Wing Attack → Supersonic Skystrike, 120 Physical; status: Tailwind; status: Roost clears negative user stages; other sources deferred | Accepted bounded pairs / [#801](https://github.com/PokemonFusion/Fusion2/issues/801), [#912](https://github.com/PokemonFusion/Fusion2/issues/912) |
| Ghostium Z | Generic / Ghost | Any eligible native holder | Lick → Never-Ending Nightmare, 100 Physical; status: Destiny Bond, Curse; Shadow Ball → Never-Ending Nightmare, 160 Special; other sources deferred | Accepted bounded pairs / [#801](https://github.com/PokemonFusion/Fusion2/issues/801), [#910](https://github.com/PokemonFusion/Fusion2/issues/910) |
| Grassium Z | Generic / Grass | Any eligible native holder | Vine Whip → Bloom Doom, 100 Physical; Energy Ball → Bloom Doom, 175 Special; status: Synthesis clears negative user stages; other sources deferred | Accepted bounded pairs / [#801](https://github.com/PokemonFusion/Fusion2/issues/801), [#910](https://github.com/PokemonFusion/Fusion2/issues/910), [#912](https://github.com/PokemonFusion/Fusion2/issues/912) |
| Groundium Z | Generic / Ground | Any eligible native holder | Mud-Slap → Tectonic Rage, 100 Special; Earthquake → Tectonic Rage, 180 Physical; other sources deferred | Accepted bounded pairs / [#801](https://github.com/PokemonFusion/Fusion2/issues/801), [#911](https://github.com/PokemonFusion/Fusion2/issues/911) |
| Icium Z | Generic / Ice | Any eligible native holder | Powder Snow → Subzero Slammer, 100 Special; status: Haze; Ice Beam → Subzero Slammer, 175 Special; other sources deferred | Accepted bounded pairs / [#801](https://github.com/PokemonFusion/Fusion2/issues/801), [#910](https://github.com/PokemonFusion/Fusion2/issues/910) |
| Incinium Z | Signature | Incineroar | Darkest Lariat → Malicious Moonsault, 180 Physical | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Kommonium Z | Signature | Kommo-o, Kommo-o-Totem | Clanging Scales → Clangorous Soulblaze, 185 Special | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Lunalium Z | Signature | Lunala; Dawn-Wings with [valid live native pair proof](necrozma-combination.md) | Moongeist Beam → Menacing Moonraze Maelstrom, 200 Special | Accepted native Lunala route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808); native pair route accepted locally / #830; released local socket QA #831 passed |
| Lycanium Z | Signature | Lycanroc, Lycanroc-Midnight, Lycanroc-Dusk | Stone Edge → Splintered Stormshards, 190 Physical | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Marshadium Z | Signature | Marshadow | Spectral Thief → Soul-Stealing 7-Star Strike, 195 Physical | Accepted bounded route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Mewnium Z | Signature | Mew | Psychic → Genesis Supernova, 185 Special | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Mimikium Z | Signature | Mimikyu, Mimikyu-Totem; matching Busted only after actual native Disguise break | Play Rough → Let's Snuggle Forever, 190 Physical | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Normalium Z | Generic / Normal | Any eligible native holder | Tackle → Breakneck Blitz, 100 Physical; status: Splash, Growl, Swords Dance; Body Slam → Breakneck Blitz, 160 Physical; status: Recover/Protect clear negative user stages; other sources deferred | Accepted bounded pairs / [#799](https://github.com/PokemonFusion/Fusion2/issues/799), [#911](https://github.com/PokemonFusion/Fusion2/issues/911), [#912](https://github.com/PokemonFusion/Fusion2/issues/912) |
| Pikanium Z | Signature | Pikachu | Volt Tackle → Catastropika, 210 Physical | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Pikashunium Z | Signature | Pikachu-Original, Pikachu-Hoenn, Pikachu-Sinnoh, Pikachu-Unova, Pikachu-Kalos, Pikachu-Alola, Pikachu-Partner | Thunderbolt → 10,000,000 Volt Thunderbolt, 195 Special | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Poisonium Z | Generic / Poison | Any eligible native holder | Poison Sting → Acid Downpour, 100 Physical; Sludge Bomb → Acid Downpour, 175 Special; status: Toxic gives user Defense +1; other sources deferred | Accepted bounded pairs / [#802](https://github.com/PokemonFusion/Fusion2/issues/802), [#910](https://github.com/PokemonFusion/Fusion2/issues/910), [#912](https://github.com/PokemonFusion/Fusion2/issues/912) |
| Primarium Z | Signature | Primarina | Sparkling Aria → Oceanic Operetta, 195 Special | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Psychium Z | Generic / Psychic | Any eligible native holder | Confusion → Shattered Psyche, 100 Special; Psychic → Shattered Psyche, 175 Special; other sources deferred | Accepted bounded pairs / [#802](https://github.com/PokemonFusion/Fusion2/issues/802), [#910](https://github.com/PokemonFusion/Fusion2/issues/910) |
| Rockium Z | Generic / Rock | Any eligible native holder | Rock Throw → Continental Crush, 100 Physical; Rock Slide → Continental Crush, 140 Physical; other sources deferred | Accepted bounded pairs / [#802](https://github.com/PokemonFusion/Fusion2/issues/802), [#911](https://github.com/PokemonFusion/Fusion2/issues/911) |
| Snorlium Z | Signature | Snorlax | Giga Impact → Pulverizing Pancake, 210 Physical | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Solganium Z | Signature | Solgaleo; Dusk-Mane with [valid live native pair proof](necrozma-combination.md) | Sunsteel Strike → Searing Sunraze Smash, 200 Physical | Accepted native Solgaleo route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808); native pair route accepted locally / #830; released local socket QA #831 passed |
| Steelium Z | Generic / Steel | Any eligible native holder | Metal Claw → Corkscrew Crash, 100 Physical; Iron Head → Corkscrew Crash, 160 Physical; other sources deferred | Accepted bounded pairs / [#802](https://github.com/PokemonFusion/Fusion2/issues/802), [#911](https://github.com/PokemonFusion/Fusion2/issues/911) |
| Tapunium Z | Signature | Tapu Koko, Tapu Lele, Tapu Bulu, Tapu Fini | Nature's Madness → Guardian of Alola, fixed HP fraction Special | Accepted bounded route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Ultranecrozium Z | Signature | Necrozma-Ultra | Photon Geyser | Deferred runtime: [accepted Ultra contract](ultra-burst.md), implementation #885–#888 |
| Waterium Z | Generic / Water | Any eligible native holder | Water Gun → Hydro Vortex,100 Special; Surf → Hydro Vortex,175 Special, normal single target; other sources deferred | Accepted bounded pairs / [#802](https://github.com/PokemonFusion/Fusion2/issues/802), [#863](https://github.com/PokemonFusion/Fusion2/issues/863) |

Ultranecrozium Z is listed rather than silently enabled: its required native
Necrozma-Ultra lifecycle/Ultra Burst route is outside this non-transformation
slice. No Ultra shortcut, plot unlock, new crystal or automatic NPC action is
created. Other signature forms in this metadata table are requirements, not
claims of obtainable or implemented holders. All 34 other crystals have one
planned owner. The 32 generic, 14 status and 16 signature mappings have bounded ordinary Z acceptance.

The optional Counter has the 34 accepted generic/signature offers, PF2 price 10,000,
finite stock 1 each and no refill. Other offers require their named acceptance gate.
No live stocking is performed. #781 configured supply and #782 released live
walkthroughs remain separate. The [design receipt](../testing/item-designs-2026-10-22.md)
records static inventory/link validation without claiming a player route.

## Qualified native access and special rules

Seven exact cap forms and intact Mimikyu-Totem/Kommo-o-Totem pass configured
ordinary `+hunt` → `+item Master Ball` → `+teach` → moveset selection → held
crystal → `+zmove` in disposable SQL. These are existing authored routes, not
new native-form grants or a claim that live charts contain them. Both real
Disguise breaks, their matching Busted forms and reconnects pass; an owned
Busted row, copied proof, Transform and unlisted World Cap are rejected.

The [source reviews](z-move-source-review.md) and [signature review](z-signature-source-review.md)
freeze exact powers, flags and effects. Guardian uses its reviewed fixed
fraction/Protect rounding; Soulblaze resolves targets independently and boosts
five stats once after any hit (Sheer Force removes that bonus and boosts power).
Terrain effects require actual HP/substitute damage. Breakable abilities are
bypassed by Searing/Menacing; Shadow Shield, Prism Armor and Ability Shield
retain the ordinary boundary. No source recoil, recharge, trapping, stage theft,
defensive-stage bypass or Defense drop is inherited by a signature.
