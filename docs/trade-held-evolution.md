# Existing trade-held evolution items (#755)

## PF2 rule and dependencies

PF2 uses an explicit **non-transfer evolution equivalent** for the existing
trade-held items below. Equip the item with `+hold`, find the full Pokemon ID
with `+party <slot>`, then use `+evolve <pokemon-id>` without a bag item.
There is no trade, recipient, transfer receipt, new item or plot requirement.
The original owner and canonical party/box placement remain unchanged.

On October 21, #722 (transactional ownership transfer) and #725 (consent trading)
remain open, and the legacy `+trade` command still refuses all transfers. Those
issues are prerequisites for actual trading, which this change does not enable.
Future trading must define its evolution policy explicitly; it must not infer an
automatic trade hook from this direct evolution route. #723's Fusion reservations
remain protected by the existing placement checks. #731 retains broader player
guidance acceptance; this feature updates `+evolve` help and the evolution guide.

## Exact supported mappings

| Source | Held item | Target |
| --- | --- | --- |
| Clamperl | Deep Sea Scale | Gorebyss |
| Clamperl | Deep Sea Tooth | Huntail |
| Seadra | Dragon Scale | Kingdra |
| Porygon2 | Dubious Disc | Porygon-Z |
| Electabuzz | Electirizer | Electivire |
| Poliwhirl | King's Rock | Politoed |
| Slowpoke | King's Rock | Slowking |
| Magmar | Magmarizer | Magmortar |
| Onix | Metal Coat | Steelix |
| Scyther | Metal Coat | Scizor |
| Nohface | Metal Coat | Kitsunoh |
| Feebas | Prism Scale | Milotic |
| Rhydon | Protector | Rhyperior |
| Dusclops | Reaper Cloth | Dusknoir |
| Spritzee | Sachet | Aromatisse |
| Porygon | Up-Grade | Porygon2 |
| Swirlix | Whipped Dream | Slurpuff |

These are 17 transitions using 14 existing items, including the checked-in CAP
species Nohface. Eligibility requires the exact source/target/item allowlist,
matching dex evolution links and `trade`/`evoItem` metadata, plus every ordinary
level, gender, region and condition check. Unknown types, conditions or mappings
fail closed. Full names share the game's punctuation/case normalization. A bag
item argument cannot substitute for holding the item.

## Player flow and transaction

For example, with a Scyther in party slot 3 and a Metal Coat in trainer inventory:

1. `+party 3` shows its complete ID.
2. `+hold 3=Metal Coat` equips one inventory copy.
3. `+evolve <that-id>` evolves Scyther into Scizor and consumes its held copy.
4. `+party 3` shows Scizor, the same ID, and an empty held slot.

An optional exact target, such as `=Scizor`,
uses the normal branch selection rules. Do not supply `Metal Coat` after the ID.
Bag copies are untouched by evolution. With no spare bag copy, the held copy is
still sufficient. Clamperl's held scale/tooth selects its branch. Everstone,
eggs, active battles and Fusion reservations still block evolution.

The service locks storage, trainer and Pokemon, then revalidates saved ownership,
placement, reservation and battle state. One transaction saves the species,
corresponding ability slot, empty held slot and existing `evo:` retry receipt.
No owner or placement writer runs. HP, PP, status, EXP, IVs, EVs, nickname and
other flags remain saved. Failure rolls back consumption and restores the shared
model cache. Repeated requests and competing requests serialize on the same
storage lock and cannot consume a second copy.

At the same level, a repeated implicit request cannot advance a second stage.
After evolving Porygon with Up-Grade, equip Dubious Disc and explicitly request
`+evolve <id>=Porygon-Z` for the next stage. A new target expresses a new request.
Replacing/removing a held item retains the existing inventory return behavior.

Non-item trades (including partner-species trades) remain unsupported. No Linking
Cord, plot-only item, new item definition or battle held-item effect is added.

## Validation boundary

Production-command/model acceptance uses disposable PostgreSQL fixtures and the
real `+party`, `+hold`, `+evolve` parsers and gameplay services. Session transport
is captured separately. This proves local command behavior and persistence;
it does not claim a logged-in live session, deployment or merged main branch.
