# Manual battle recovery (#773)

This is the reviewed PF2 bag-use contract for existing items. `+item` uses the
same transactional medicine service as Potion, never a held item's `onEat`
callback. `+use` retains its field rules. No item definitions or plot effects
are added.

## Named allowlist

| Bag item | Battle effect on an owned party member |
| --- | --- |
| Fresh Water | Up to 30 HP, living target |
| Soda Pop | Up to 50 HP, living target |
| Lemonade | Up to 70 HP, living target |
| Moomoo Milk | Up to 100 HP, living target |
| Sweet Heart | Up to 20 HP, living target |
| Lava Cookie | Cure a living target's major status |
| Old Gateau | Cure a living target's major status |
| Casteliacone | Cure a living target's major status |
| Lumiose Galette | Cure a living target's major status |
| Shalour Sable | Cure a living target's major status |
| Big Malasada | Cure a living target's major status |
| Pewter Crunchies | Cure a living target's major status |
| Max Honey | Revive a fainted target to maximum HP; no unlock |
| Oran Berry | Up to 10 HP, living target |
| Sitrus Berry | Up to floor(maximum HP / 4), minimum 1, living target |
| Berry Juice | Up to 20 HP, living target |
| Cheri Berry | Cure paralysis |
| Chesto Berry | Cure sleep, including saved sleep turns |
| Pecha Berry | Cure poison or toxic poison |
| Rawst Berry | Cure burn |
| Aspear Berry | Cure freeze |
| Lum Berry | Cure any major status |
| Leppa Berry | Restore up to 10 PP to one selected active move |
| Berry | Up to 10 HP, living target |
| Gold Berry | Up to 30 HP, living target |
| Burnt Berry | Cure freeze |
| Ice Berry | Cure burn |
| Mint Berry | Cure sleep, including saved sleep turns |
| Miracle Berry | Cure any major status |
| PRZ Cure Berry | Cure paralysis |
| PSN Cure Berry | Cure poison or toxic poison |
| Mystery Berry | Restore up to 5 PP to one selected active move |

Major status means burn, poison/toxic, freeze, sleep or paralysis. All recovery
is capped at calculated maximum HP/boosted PP. No recovery berry revives.
These 32 names retain existing PF2 field amounts and legacy identities (#754,
#758, #767); bag use does not apply nature confusion, Ripen, Cheek Pouch,
Cud Chew, held-item suppression or automatic eating thresholds. Held copies
and their existing automatic effects remain independent.

## Exclusions and mechanics review

Figy, Wiki, Mago, Aguav and Iapapa stay field/held-only. Pomeg, Kelpsy, Qualot,
Hondew, Grepa and Tamato stay field-only for EV/friendship feeding. Sacred Ash
stays field-only with its whole-party `+use Sacred Ash=party` contract.
Persim/Bitter confusion-only berries, stat/resistance/pinch/contest berries,
progression/training/ability items and all other unsupported items stay rejected
before reserving an action. No confusion-only effect is added to Full Heal,
Lum, Miracle Berry or food equivalents in this bounded major-status extension.

Primary mechanics references: the reconstructed game item tables in
[Emerald](https://github.com/pret/pokeemerald/blob/master/src/data/items.h)
explicitly mark standard recovery berries, Berry Juice, drinks and Lava Cookie
as battle medicine; flavor/EV berries and Sacred Ash have no battle-use entry.
The [Crystal attribute table](https://github.com/pret/pokecrystal/blob/master/data/items/attributes.asm)
marks the nine legacy equivalents as party-targetable in battle, and its
[effect dispatch](https://github.com/pret/pokecrystal/blob/master/engine/items/item_effects.asm)
separates bag medicine from held effects. These references establish eligibility,
not PF2's cross-generation amounts. Later food brands and Max Honey explicitly
inherit PF2's already reviewed Full Heal/Max Revive equivalence in
[field-food-medicine.md](field-food-medicine.md), without cooking or story routes.
PF2's existing permitted PvP/NPC/wild medicine rules remain in effect.

## Player flow and failure policy

Use `+item Fresh Water`, `+item Max Honey=3`, or
`+item A1 Leppa Berry=3/Water Gun`. Multiple active battlers require the acting
slot. Targets are canonical owned party members/current Fusion in this battle's
roster, including fainted reserves. A move slot or full move name selects PP;
without it, the first depleted active move is restored. Opponents, foreign
owners, eggs, boxes and inactive Fusion reservations are ineligible.

An unsupported item, missing stock, invalid actor or unresolved target is rejected
without reserving an action. A supported queued medicine with no useful effect
spends that action but no item. An invalid/stale move selector has no effect and
never falls back to a different move. A target that becomes ineligible before
execution receives no effect/debit. Useful effects debit exactly one bag copy;
SQL/runtime effects and the turn checkpoint roll back together on write failure.
The production turn recovery policy handles infrastructure failures; never retry
by mutating the persisted declaration into a different target or move.

Embargo also rejects medicine aimed at the affected active recipient before
reserving an action. This covers HP, status and selected/all-move PP medicine,
including the permitted foods and berries above. An embargoed actor can still
use medicine on an unaffected reserve or doubles partner. Magic Room and Klutz
do not restrict bag medicine. If Embargo appears after queuing, the action is
spent without an effect or item debit, following the existing stale-target
policy. Field `+use` retains its separate eligibility rules.

This target restriction follows the primary
[manual Embargo check](https://github.com/rh-hideout/pokeemerald-expansion/blob/master/src/item_use.c).
The [October 29 repair report](testing/item-repairs-2026-10-29.md) separates
isolated command/SQL checks from socket acceptance and deployment.

Held Pecha Berry and PSN Cure Berry also cure Toxic; Burnt Berry thaws freeze
and cannot cure burn. Their held triggers obey item suppression and Unnerve.
These repairs preserve the field and manual bag routes, their reviewed amounts,
and the supported no-effect action policy above. Current held evidence is in the
[2026-10-25 berry report](testing/held-status-berries-2026-10-25.md); earlier dated
reports remain historical receipts.
