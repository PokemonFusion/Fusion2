# Held stat, damage and recovery items

Equip the physical copy with `+hold 3=<item>`, then use ordinary battle actions.
Bag copies do not activate held effects. Inspect with `+party 3`; reusable held
items return through `+hold 3=` after battle. Consumables can be recovered by
the existing Recycle route when that Pokémon actually knows the move.

| Items | Qualifying effect |
| --- | --- |
| Liechi, Ganlon, Salac, Petaya, Apicot Berry | At quarter HP, raise Attack, Defense, Speed, Sp. Atk or Sp. Def by one stage respectively |
| Starf Berry | At quarter HP, choose uniformly among Attack/Defense/Sp. Atk/Sp. Def/Speed below +6 and raise it by two stages |
| Absorb Bulb / Cell Battery / Luminous Moss / Snowball | Survive an actual Water / Electric / Water / Ice hit; raise Sp. Atk / Attack / Sp. Def / Attack by one stage |
| Kee / Maranga Berry | Survive an actual physical / special hit; raise Defense / Sp. Def by one stage |
| Weakness Policy | Survive an ordinary super-effective damaging hit; raise Attack and Sp. Atk by two stages |
| Throat Spray | Complete an eligible sound move; raise Sp. Atk by one stage |
| Electric / Grassy Seed | Matching current terrain raises Defense by one stage |
| Misty / Psychic Seed | Matching current terrain raises Sp. Def by one stage |
| Berserk Gene | Consume on an eligible battle update; raise Attack by two stages and attempt ordinary confusion |

All these stage effects retain earned stages, normal ability rules and the
−6/+6 caps. Contrary reverses the delta; Simple doubles it. Pinch berries
also qualify at half HP with effective Gluttony. Eating still checks Unnerve
and suppression. Qualifying uses consume even when a stat is capped. Starf's
eligible list follows the reference's pre-ability stage check; it never chooses
accuracy or evasion. Its future choice and committed result survive checkpoints.

Berserk Gene uses PF2's current ability and volatile rules alongside its legacy
Attack-only effect. Own Tempo prevents confusion, Contrary/Simple affect Attack,
and no Speed increase occurs. Recovered eligible copies can activate again at a
later normal update. This policy does not recreate generation-two-only battles.

Black Sludge on a non-Poison holder, Sticky Barb, Rocky Helmet and Jaboca/Rowap
retaliation use indirect-damage guards. Magic Guard prevents that damage while
ordinary direct attacks still work. A Jaboca/Rowap Berry is retained when the
attacker has effective Magic Guard. Protective Pads and contact-removing effects
retain their contact protections; retaliation berries use their damage category.

Leftovers and Poison-type Black Sludge heal through ordinary healing eligibility.
Heal Block, including Psychic Noise's two-turn block, prevents their healing.
Healing resumes after expiry; neither item revives a fainted holder. The reusable
copy remains held. See the separate [manual medicine policy](battle-recovery-items.md)
for bag use against Embargo recipients.

These mechanics follow the pinned primary
[item reference](https://github.com/smogon/pokemon-showdown/blob/ccfaa20f32af363569cd21a9d501b2bc1ded26b1/data/items.ts)
and [consumption reference](https://github.com/smogon/pokemon-showdown/blob/ccfaa20f32af363569cd21a9d501b2bc1ded26b1/sim/pokemon.ts).
The [dated repair receipt](testing/item-repairs-2026-10-29.md) records the exact
tested candidate and evidence limits. Definitions and local checks establish no
new public source, current stock, deployed code or logged-in acceptance.
