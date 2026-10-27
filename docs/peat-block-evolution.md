# Peat Block and ordinary Ursaluna (#760)

## Selected PF2 rule

Recorded before implementation: PF2 selects #760's **explicit mechanical
equivalent**, rather than adding a lunar calendar or accepting a full-moon flag.
An ordinary owner uses `+evolve <pokemon-id> Peat Block` outside battle. One
Peat Block from trainer inventory evolves the exact native species **Ursaring**
into **ordinary Ursaluna**. `=Ursaluna` may be supplied explicitly. This action
has no additional level, time, region, weather or lunar requirement.

The cartridge baseline uses a Peat Block on Ursaring during a full moon and
consumes it ([Peat Block effect](https://bulbapedia.bulbagarden.net/wiki/Peat_Block#Effect),
reviewed October 21, 2026). The checked-in Ursaluna dex row records that exact
condition. PF2 deliberately replaces the lunar predicate with explicit item
use, as its existing Sweets/trade-held rules use documented mechanical
equivalents. This is PF2 policy, not a claim to reproduce the cartridge moon.

`PeatBlockEvolution` in `pokemon/evolution_items.py` is the bounded rule
authority. It requires the exact source/target, complete item identity, and
the reviewed dex type/condition. The ordinary evaluator still requires both
source `evos` and target `prevo` to agree. Unknown metadata and unrelated
`other` conditions continue to fail closed; the generic condition evaluator
does **not** learn to accept full moons. Missing item input, a held-only copy,
client text, room/character moon attributes, arbitrary Pokemon flags and
nicknames cannot substitute for the actual required bag item.

## Player flow and acquisition

```text
+inventory
+itemdex Peat Block
+party 3
+evolve <full ID copied from +party 3> Peat Block
+party 3
```

Peat Block is one supplemental gameplay definition with complete normalized
name lookup, an evolution description, Evolution Items category and a PF2
reference price of 10000. The reference cost follows the documented Legends:
Arceus purchase cost in the source above; actual shops use configured prices.
Existing shop/reward mechanisms may deliberately offer it. No live shop,
reward table, automatic grant, new acquisition system or plot unlock is added.
For the current shop editor, use the one-token stock key `PeatBlock`, then buy
it normally and use the full display name. Validation separates fixture shop
stock setup from the ordinary purchase/inventory/evolution flow.

This uses the current `+evolve` bag-item interface, not a new `+use` branch.
Equipping Peat Block with generic `+hold` does not activate it. If there is also
a real bag copy, the bag copy is consumed and the unrelated held copy remains.
Everstone still blocks evolution. Eggs, foreign/conflicting owners, Fusion
reservations and battle locks remain guarded by the existing lifecycle service.
Legal party/box placement stays unchanged; no placement or ownership transfer
is introduced.

## Persistence and limits

`EvolutionService` retains its storage/trainer/fresh-Pokemon locks, outer
transaction and retry receipt. It consumes exactly one bag copy and saves the
same Pokemon identity. Failed validation or save rolls back inventory, the
transition and cached state. Repeated or competing completion cannot consume a
second copy. Existing ability-slot mapping, saved nickname, HP/status/sleep,
EXP, IVs/EVs, moves/PP, held item, ownership and placement are preserved except
the canonical evolved species, ability, types and normal evolution receipt.

Bloodmoon is an unrelated fixed form in the checked-in dex with no evolution
link from Ursaring. This rule cannot select it or transform ordinary Ursaluna
into it. No generic evolution override, quest, calendar, weather simulation,
plot-only item, new dex species or schema migration is included. The #747
existing-item gate and closed #755/#756 dependencies were refreshed first.

Automated ordinary-command/model proof, live login acceptance, hosted CI,
main merge and deployment are reported separately in the closeout report.
