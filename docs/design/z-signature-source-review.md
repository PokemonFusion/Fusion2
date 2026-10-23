# Signature Z source review before implementation

This freezes the bounded #805–#808 mappings before any signature is enabled.
The [ordinary/status source review](z-move-source-review.md),
[activation contract](z-moves.md) and [crystal gates](z-crystals.md) still apply.
The checked-in ITEMDEX and MOVEDEX supply these exact native/source/signature
identities, powers, categories and flags. Priority is zero and accuracy is true
for every signature below. Single-target rows use `normal`; special targets are
explicit. Nothing here installs supply or grants a form.

| Crystal / issue | Native holder scope | Active source | Signature | Power / type / category | Intrinsic effect / flags |
| --- | --- | --- | --- | --- | --- |
| Aloraichium Z / #805 | Raichu-Alola | Thunderbolt | Stoked Sparksurfer | 175 Electric Special | 100% paralysis; noncontact |
| Decidium Z / #805 | Decidueye | Spirit Shackle | Sinister Arrow Raid | 180 Ghost Physical | Noncontact; no source trapping |
| Incinium Z / #805 | Incineroar | Darkest Lariat | Malicious Moonsault | 180 Dark Physical | Contact; no ordinary source defensive-stage bypass |
| Primarium Z / #805 | Primarina | Sparkling Aria | Oceanic Operetta | 195 Water Special | Noncontact; single target; no source burn cure |
| Pikanium Z / #806 | Pikachu | Volt Tackle | Catastropika | 210 Electric Physical | Contact; no source recoil |
| Pikashunium Z / #806 | Seven checked-in cap forms only | Thunderbolt | 10,000,000 Volt Thunderbolt | 195 Electric Special | Noncontact; critical ratio 3 in dex, normalized to PF2 critical stage 2 |
| Snorlium Z / #806 | Snorlax | Giga Impact | Pulverizing Pancake | 210 Normal Physical | Contact; no ordinary recharge |
| Mimikium Z / #806 | Native Mimikyu and its real Busted lifecycle | Play Rough | Let's Snuggle Forever | 190 Fairy Physical | Contact; Totem native access remains a separate gate |
| Eevium Z / #807 | Eevee | Last Resort | Extreme Evoboost | 0 Normal Status | Self target; Atk/Def/SpA/SpD/Spe +2, ordinary caps |
| Kommonium Z / #807 | Kommo-o | Clanging Scales | Clangorous Soulblaze | 185 Dragon Special | All adjacent foes; sound/bypass substitute; one +1 five-stat self boost after a successful hit; Totem native access separate |
| Lycanium Z / #807 | Lycanroc, Midnight, Dusk | Stone Edge | Splintered Stormshards | 190 Rock Physical | Noncontact; remove terrain after real HP/substitute damage |
| Mewnium Z / #807 | Mew | Psychic | Genesis Supernova | 185 Psychic Special | Noncontact; set Psychic Terrain after a successful hit |
| Lunalium Z / #808 | Lunala | Moongeist Beam | Menacing Moonraze Maelstrom | 200 Ghost Special | Noncontact; intrinsic ability bypass; fused Necrozma access separate |
| Solganium Z / #808 | Solgaleo | Sunsteel Strike | Searing Sunraze Smash | 200 Steel Physical | Contact; intrinsic ability bypass; fused Necrozma access separate |
| Marshadium Z / #808 | Marshadow | Spectral Thief | Soul-Stealing 7-Star Strike | 195 Ghost Physical | Contact; no ordinary Spectral Thief boost theft |
| Tapunium Z / #808 | Tapu Koko/Lele/Bulu/Fini | Nature's Madness | Guardian of Alola | Fixed Fairy Special | Noncontact; floor(current HP × 3/4), minimum one; explicit protection rounding |

The seven cap forms are Pikachu-Original, Hoenn, Sinnoh, Unova, Kalos, Alola and
Partner. Ordinary Pikachu, nickname/Transform copies and unlisted World Cap are
not substitutes. Existing authored hunt/capture and actual source teaching must
prove native access; metadata and direct owned-row fixtures alone do not.
Mimikyu-Busted must result from the existing native Disguise consumer with an
ordinary Mimikyu owner, not an owned Busted species grant. Fused Necrozma,
Mimikyu Totem and Kommo-o Totem remain deferred until a named prerequisite proves
their actual native creation/lifecycle. No species-fusion route or plot shortcut
is introduced. Ultranecrozium remains outside this rollout.

The primary simulator's [signature definitions](https://github.com/smogon/pokemon-showdown/blob/1636bf6d0848fb3c9330576963a647d4e179d278/data/moves.ts)
confirm that Soul-Stealing 7-Star Strike does **not** inherit Spectral Thief's
boost theft. The #808 wording must use damage and unchanged-stage controls.
Guardian's protected damage is `max(1, ceil(floor(3*HP/4)/4 - 1/2))`; ordinary
damage is `max(1, floor(3*HP/4))`. Critical-ratio metadata uses a one-based dex
value, while PF2's consumer uses a zero-based critical stage; the private
10,000,000 Volt descriptor must normalize 3 to 2 rather than grant guaranteed
criticals. No global ordinary-move critical rewrite is part of this mapping.

Each signature descriptor retains only its reviewed intrinsic effects and flags.
The source provides its actual active identity, legal restrictions and one PP;
it does not donate ordinary trapping, recoil, recharge, stage theft, spread or
secondary effects. Generic and status lists remain independently bounded.
All real effects, immunity/protection, current targets, PP, budgets, rollback,
rebuild, source purchase and cleanup gates must pass before a row is released.
