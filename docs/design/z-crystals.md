# Existing Z-Crystal implementation plan (#775)

Status: **42 explicit mappings on 34 crystals accepted locally**: 18 generic
damage sources, eight status sources and 16 signatures. [Foundation evidence](../testing/z-core-2026-10-23.md),
[status/signature evidence](../testing/z-special-2026-10-23.md) and [player guide](../z-moves.md).
Other ordinary/status sources, fused Necrozma ([#820](https://github.com/PokemonFusion/Fusion2/issues/820))
and Ultra remain deferred. No live deployment or stock installation is asserted.
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

The accepted generic list contains exactly one reviewed damaging source per
crystal, including Normalium Z/Tackle. These remain **partial** support; other
source moves require their own explicit effect and player-route gates. Status issues select at most
six mappings each; other status, variable, called and restricted combinations
stay deferred. Signature groups contain four crystals each and require exact
native-holder/source/effect proof; missing native access becomes a prerequisite.

## Per-item status

| Existing crystal | Family / type | Native holder restriction | Source move | Current status / owner |
| --- | --- | --- | --- | --- |
| Aloraichium Z | Signature | Raichu-Alola | Thunderbolt → Stoked Sparksurfer, 175 Special | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Buginium Z | Generic / Bug | Any eligible native holder | Bug Bite → Savage Spin-Out, 120 Physical; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Darkinium Z | Generic / Dark | Any eligible native holder | Bite → Black Hole Eclipse, 120 Physical; status: Memento; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Decidium Z | Signature | Decidueye | Spirit Shackle → Sinister Arrow Raid, 180 Physical | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Dragonium Z | Generic / Dragon | Any eligible native holder | Dragon Breath → Devastating Drake, 120 Special; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Eevium Z | Signature | Eevee | Last Resort → Extreme Evoboost, Status | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Electrium Z | Generic / Electric | Any eligible native holder | Thunder Shock → Gigavolt Havoc, 100 Special; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Fairium Z | Generic / Fairy | Any eligible native holder | Fairy Wind → Twinkle Tackle, 100 Special; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Fightinium Z | Generic / Fighting | Any eligible native holder | Karate Chop → All-Out Pummeling, 100 Physical; other sources deferred | Accepted bounded pair / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Firium Z | Generic / Fire | Any eligible native holder | Ember → Inferno Overdrive, 100 Special; other sources deferred | Accepted bounded pair / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Flyinium Z | Generic / Flying | Any eligible native holder | Wing Attack → Supersonic Skystrike, 120 Physical; status: Tailwind; other sources deferred | Accepted bounded pair / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Ghostium Z | Generic / Ghost | Any eligible native holder | Lick → Never-Ending Nightmare, 100 Physical; status: Destiny Bond, Curse; other sources deferred | Accepted bounded pair / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Grassium Z | Generic / Grass | Any eligible native holder | Vine Whip → Bloom Doom, 100 Physical; other sources deferred | Accepted bounded pair / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Groundium Z | Generic / Ground | Any eligible native holder | Mud-Slap → Tectonic Rage, 100 Special; other sources deferred | Accepted bounded pair / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Icium Z | Generic / Ice | Any eligible native holder | Powder Snow → Subzero Slammer, 100 Special; status: Haze; other sources deferred | Accepted bounded pair / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Incinium Z | Signature | Incineroar | Darkest Lariat → Malicious Moonsault, 180 Physical | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Kommonium Z | Signature | Kommo-o, Kommo-o-Totem | Clanging Scales → Clangorous Soulblaze, 185 Special | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Lunalium Z | Signature | Lunala; fused Necrozma deferred #820 | Moongeist Beam → Menacing Moonraze Maelstrom, 200 Special | Accepted bounded route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Lycanium Z | Signature | Lycanroc, Lycanroc-Midnight, Lycanroc-Dusk | Stone Edge → Splintered Stormshards, 190 Physical | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Marshadium Z | Signature | Marshadow | Spectral Thief → Soul-Stealing 7-Star Strike, 195 Physical | Accepted bounded route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Mewnium Z | Signature | Mew | Psychic → Genesis Supernova, 185 Special | Accepted bounded route / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Mimikium Z | Signature | Mimikyu, Mimikyu-Totem; matching Busted only after actual native Disguise break | Play Rough → Let's Snuggle Forever, 190 Physical | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Normalium Z | Generic / Normal | Any eligible native holder | Tackle → Breakneck Blitz, 100 Physical; status: Splash, Growl, Swords Dance; other sources deferred | Accepted bounded pair / [#799](https://github.com/PokemonFusion/Fusion2/issues/799) |
| Pikanium Z | Signature | Pikachu | Volt Tackle → Catastropika, 210 Physical | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Pikashunium Z | Signature | Pikachu-Original, Pikachu-Hoenn, Pikachu-Sinnoh, Pikachu-Unova, Pikachu-Kalos, Pikachu-Alola, Pikachu-Partner | Thunderbolt → 10,000,000 Volt Thunderbolt, 195 Special | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Poisonium Z | Generic / Poison | Any eligible native holder | Poison Sting → Acid Downpour, 100 Physical; other sources deferred | Accepted bounded pair / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Primarium Z | Signature | Primarina | Sparkling Aria → Oceanic Operetta, 195 Special | Accepted bounded route / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Psychium Z | Generic / Psychic | Any eligible native holder | Confusion → Shattered Psyche, 100 Special; other sources deferred | Accepted bounded pair / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Rockium Z | Generic / Rock | Any eligible native holder | Rock Throw → Continental Crush, 100 Physical; other sources deferred | Accepted bounded pair / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Snorlium Z | Signature | Snorlax | Giga Impact → Pulverizing Pancake, 210 Physical | Accepted bounded route / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Solganium Z | Signature | Solgaleo; fused Necrozma deferred #820 | Sunsteel Strike → Searing Sunraze Smash, 200 Physical | Accepted bounded route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Steelium Z | Generic / Steel | Any eligible native holder | Metal Claw → Corkscrew Crash, 100 Physical; other sources deferred | Accepted bounded pair / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Tapunium Z | Signature | Tapu Koko, Tapu Lele, Tapu Bulu, Tapu Fini | Nature's Madness → Guardian of Alola, fixed HP fraction Special | Accepted bounded route / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Ultranecrozium Z | Signature | Necrozma-Ultra | Photon Geyser | Deferred: Ultra native-form route needs separate design |
| Waterium Z | Generic / Water | Any eligible native holder | Water Gun → Hydro Vortex, 100 Special; other sources deferred | Accepted bounded pair / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |

Ultranecrozium Z is listed rather than silently enabled: its required native
Necrozma-Ultra lifecycle/Ultra Burst route is outside this non-transformation
slice. No Ultra shortcut, plot unlock, new crystal or automatic NPC action is
created. Other signature forms in this metadata table are requirements, not
claims of obtainable or implemented holders. All 34 other crystals have one
planned owner. The 18 generic, eight status and 16 signature mappings have bounded ordinary Z acceptance.

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
