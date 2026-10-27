# Reactive held-item consumption

Equip an owned party member through `+hold`, for example
`+hold 3=Kee Berry`, then use the ordinary battle commands.

| Item | Consumption trigger |
| --- | --- |
| Jaboca Berry | An actual physical hit, with a living active attacker to retaliate against |
| Rowap Berry | An actual special hit, with a living active attacker to retaliate against |
| Kee Berry | A surviving holder receives an actual physical hit |
| Maranga Berry | A surviving holder receives an actual special hit |
| Weakness Policy | A surviving holder receives ordinary super-effective damage, excluding fixed damage |
| Throat Spray | The holder completes a sound move; a damaging sound move must hit |

Magic Room, Embargo and Klutz keep these effects inactive while leaving the
physical item held. Opposing Unnerve also prevents the four berries from being
eaten. Jaboca and Rowap can retaliate from a hit that faints their holder.

A Pokemon that knows Recycle can recover its consumed copy while its held slot
is empty in the same battle. Recovery retires the old recovery references, so a
later theft cannot produce another copy through Recycle or the existing Harvest
and Pickup routes. Recovering a berry preserves the fact that it was eaten.
If it consumes a different item later, Recycle targets that newer use; Harvest
cannot retrieve the superseded berry slot.
Checkpoint rebuilds retain this history without replaying consumption or PP.

This is the six-item consumption/history repair in
[#921](https://github.com/PokemonFusion/Fusion2/issues/921). Canonical stage
interactions remain tracked separately in
[#923](https://github.com/PokemonFusion/Fusion2/issues/923), and retaliation damage
guards in [#925](https://github.com/PokemonFusion/Fusion2/issues/925). It does not
certify public stock, every Pickup/Belch eligibility rule, or a game deployment.
The [test report](testing/reactive-consumption-2026-10-27.md) separates ordinary
command/model evidence from the wider automated mechanics checks.
