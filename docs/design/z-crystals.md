# Existing Z-Crystal implementation plan (#775)

Status: **all 35 crystals deferred; zero ordinary-player routes enabled**.
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

The first route accepts Normalium Z/Tackle only. Later generic issues choose
one reviewed source move per named crystal and remain **partial** support
until their explicit move/effect allowlists pass. Status issues select at most
six mappings each; other status, variable, called and restricted combinations
stay deferred. Signature groups contain four crystals each and require exact
native-holder/source/effect proof; missing native access becomes a prerequisite.

## Per-item status

| Existing crystal | Family / type | Native holder restriction | Source move | Current status / owner |
| --- | --- | --- | --- | --- |
| Aloraichium Z | Signature | Raichu-Alola | Thunderbolt | Deferred / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Buginium Z | Generic / Bug | Any eligible native holder | Explicit mapping pending | Deferred / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Darkinium Z | Generic / Dark | Any eligible native holder | Explicit mapping pending | Deferred / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Decidium Z | Signature | Decidueye | Spirit Shackle | Deferred / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Dragonium Z | Generic / Dragon | Any eligible native holder | Explicit mapping pending | Deferred / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Eevium Z | Signature | Eevee | Last Resort | Deferred / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Electrium Z | Generic / Electric | Any eligible native holder | Explicit mapping pending | Deferred / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Fairium Z | Generic / Fairy | Any eligible native holder | Explicit mapping pending | Deferred / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Fightinium Z | Generic / Fighting | Any eligible native holder | Explicit mapping pending | Deferred / [#800](https://github.com/PokemonFusion/Fusion2/issues/800) |
| Firium Z | Generic / Fire | Any eligible native holder | Explicit mapping pending | Deferred / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Flyinium Z | Generic / Flying | Any eligible native holder | Explicit mapping pending | Deferred / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Ghostium Z | Generic / Ghost | Any eligible native holder | Explicit mapping pending | Deferred / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Grassium Z | Generic / Grass | Any eligible native holder | Explicit mapping pending | Deferred / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Groundium Z | Generic / Ground | Any eligible native holder | Explicit mapping pending | Deferred / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Icium Z | Generic / Ice | Any eligible native holder | Explicit mapping pending | Deferred / [#801](https://github.com/PokemonFusion/Fusion2/issues/801) |
| Incinium Z | Signature | Incineroar | Darkest Lariat | Deferred / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Kommonium Z | Signature | Kommo-o, Kommo-o-Totem | Clanging Scales | Deferred / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Lunalium Z | Signature | Lunala, Necrozma-Dawn-Wings | Moongeist Beam | Deferred / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Lycanium Z | Signature | Lycanroc, Lycanroc-Midnight, Lycanroc-Dusk | Stone Edge | Deferred / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Marshadium Z | Signature | Marshadow | Spectral Thief | Deferred / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Mewnium Z | Signature | Mew | Psychic | Deferred / [#807](https://github.com/PokemonFusion/Fusion2/issues/807) |
| Mimikium Z | Signature | Mimikyu, Mimikyu-Busted, Mimikyu-Totem, Mimikyu-Busted-Totem | Play Rough | Deferred / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Normalium Z | Generic / Normal | Any eligible native holder | Tackle initially; others deferred | Deferred / [#799](https://github.com/PokemonFusion/Fusion2/issues/799) |
| Pikanium Z | Signature | Pikachu | Volt Tackle | Deferred / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Pikashunium Z | Signature | Pikachu-Original, Pikachu-Hoenn, Pikachu-Sinnoh, Pikachu-Unova, Pikachu-Kalos, Pikachu-Alola, Pikachu-Partner | Thunderbolt | Deferred / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Poisonium Z | Generic / Poison | Any eligible native holder | Explicit mapping pending | Deferred / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Primarium Z | Signature | Primarina | Sparkling Aria | Deferred / [#805](https://github.com/PokemonFusion/Fusion2/issues/805) |
| Psychium Z | Generic / Psychic | Any eligible native holder | Explicit mapping pending | Deferred / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Rockium Z | Generic / Rock | Any eligible native holder | Explicit mapping pending | Deferred / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Snorlium Z | Signature | Snorlax | Giga Impact | Deferred / [#806](https://github.com/PokemonFusion/Fusion2/issues/806) |
| Solganium Z | Signature | Solgaleo, Necrozma-Dusk-Mane | Sunsteel Strike | Deferred / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Steelium Z | Generic / Steel | Any eligible native holder | Explicit mapping pending | Deferred / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |
| Tapunium Z | Signature | Tapu Koko, Tapu Lele, Tapu Bulu, Tapu Fini | Nature's Madness | Deferred / [#808](https://github.com/PokemonFusion/Fusion2/issues/808) |
| Ultranecrozium Z | Signature | Necrozma-Ultra | Photon Geyser | Deferred: Ultra native-form route needs separate design |
| Waterium Z | Generic / Water | Any eligible native holder | Explicit mapping pending | Deferred / [#802](https://github.com/PokemonFusion/Fusion2/issues/802) |

Ultranecrozium Z is listed rather than silently enabled: its required native
Necrozma-Ultra lifecycle/Ultra Burst route is outside this non-transformation
slice. No Ultra shortcut, plot unlock, new crystal or automatic NPC action is
created. Other signature forms in this metadata table are requirements, not
claims of obtainable or implemented holders. All 34 other crystals have one
planned owner; all 35 remain unsupported through ordinary Z activation today.

An optional Counter begins at Normalium Z only, selected PF2 price 10,000,
finite stock 1 and no refill. Later offers require each named acceptance gate.
No live stocking is performed. #781 configured supply and #782 released live
walkthroughs remain separate. The [design receipt](../testing/item-designs-2026-10-22.md)
records static inventory/link validation without claiming a player route.
