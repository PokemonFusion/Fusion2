# Healing food, drinks and revival equivalents (#758)

## Selected PF2 rules

All 14 names are included after the existing-item phase gate in #747. These are
field medicine equivalents through the shared `+use` service, with category
`Medicine`. Prices below retain the checked-in `pokemon/data/item_prices.csv`
reference costs. Recovery amounts and context rules are the selected PF2 policy.
No redundant brand is silently omitted.

| Item | Field effect | Reference price |
| --- | --- | --- |
| Fresh Water | Restore up to 30 HP to one living, injured target | 200 |
| Soda Pop | Restore up to 50 HP to one living, injured target | 300 |
| Lemonade | Restore up to 70 HP to one living, injured target | 400 |
| Moomoo Milk | Restore up to 100 HP to one living, injured target | 600 |
| Sweet Heart | Restore up to 20 HP to one living, injured target | 3000 |
| Lava Cookie | Cure one living target's major persistent status | 350 |
| Old Gateau | Cure one living target's major persistent status | 350 |
| Casteliacone | Cure one living target's major persistent status | 350 |
| Lumiose Galette | Cure one living target's major persistent status | 350 |
| Shalour Sable | Cure one living target's major persistent status | 350 |
| Big Malasada | Cure one living target's major persistent status | 350 |
| Pewter Crunchies | Cure one living target's major persistent status | 250 |
| Max Honey | Revive one fainted target to its calculated maximum HP | 4000 |
| Sacred Ash | Revive all eligible fainted canonical party members to maximum HP | 50000 |

HP is capped at the normal calculated maximum. Status foods cure burn, poison,
toxic poison, freeze, sleep or paralysis; curing sleep also clears saved sleep
turns. They do not heal HP or restore PP. HP foods/drinks and revival equivalents
preserve saved major status/sleep, PP, friendship and other progression state,
matching the existing field medicine boundary. None acts as a held berry or
invokes held-item effects. Max Honey only revives; it introduces no Max Soup,
raid, Gigantamax, Fusion or story unlock.

## Player commands and limits

Use `+use Fresh Water=3`, `+use Old Gateau=<full Pokemon ID>`, or
`+use Max Honey=6`. Single-target items accept canonical party slots (including
gaps), unambiguous full names/IDs, or the character's current `fusion`/`self`/`me`.
They reject eggs, boxed Pokemon, foreign owners and inactive Fusion reservations.
No move selector is accepted. Full normalized item names resolve; prefixes do not.

Use **`+use Sacred Ash=party`** for the party effect. It includes only eligible
owned, non-egg members in canonical party slots. Living members stay unchanged;
boxed Pokemon, eggs, other characters' Pokemon and all Fusion reservations stay
unchanged. It never selects a compacted party index or expands to account-wide
storage. A single-target or Fusion selector cannot request the party effect.

The shared service locks storage, trainer and fresh Pokemon rows, rechecks battle
and placement/ownership state, and applies effects in one transaction. Sacred Ash
debits exactly one item only when at least one member is actually revived. If
none can benefit, nothing is consumed. A failed later save rolls back every
earlier revival and the one debit, then restores shared model instances.
Concurrent/repeated completed uses recheck current state and cannot spend twice
for the same revival. Fixed-amount HP medicines may be used again while injury
remains, with one item consumed per effective use, as with Potion.

All `+use` routes are blocked during battle. #773 adds separate manual `+item`
support for the 13 single-target equivalents; Sacred Ash remains field-only.
See [the named battle allowlist and failure policy](battle-recovery-items.md).
No cooking, crafting, plot-only/key/quest item, acquisition
auto-grant or generational transformation is added.

## Intentional acquisition

Definitions make these names available to the existing optional shop/reward
systems; they do not stock a room or grant a character anything. Builders may
opt in to a food/drink/medicine shop using its existing inventory editor,
selected stock counts and these reference prices. Revival
equivalents are deliberately opt-in higher-value stock or configured gameplay
rewards, never automatic starter grants or story props.

The current inventory editor takes a one-token stock key. For example, a builder
can enter `add FreshWater 200 5`; ordinary players buy `FreshWater 1` using the
shop's displayed stock label. Inventory and itemdex render the full name, and
`+use Fresh Water=3` accepts the full name normally. Existing shops deliberately
configured with full display-name keys can instead sell `Fresh Water 1`.
The existing shop charges its configured price;
the reference price does not override room pricing. Tests use a disposable shop
and real purchase/inventory operations for every included item. No live shop,
reward table, character or room is populated by this change.
