# Healing food, drink and revival equivalents — issue #758

All 14 names in #758 now resolve as usable supplemental gameplay definitions:
five HP restoratives, seven major-status foods, Max Honey and Sacred Ash.
The [selected effect/price and acquisition table](../field-food-medicine.md)
defines PF2's field-only policy. No regional brand is omitted, no competitive dex
is rewritten, and no plot-only item or transformation unlock is introduced.

## Player flow and acquisition

The existing-item gate in #747 was complete before adding definitions. New
`FieldRecoveryItem` metadata supplies full normalized names, descriptions,
Medicine category, reference prices and effects. Prices match the existing CSV;
itemdex shows those reference costs, while shops charge their configured price.
Inventory displays the full names and the shared category renderer groups them
under Medicine.

Every item has a real shop-to-use walkthrough: disposable shop stock is configured
separately, an ordinary player buys two copies using real currency/inventory
operations, inspects inventory/itemdex, uses the item and reloads saved state.
Example commands for an explicitly stocked display-name shop:

```text
shop Buy: Fresh Water 2
+inventory
+itemdex Fresh Water
+use Fresh Water=<ID copied from +party 3>
+party 3
```

All five HP effects are capped at calculated maximum HP. All seven status foods
are tested against burn, poison, toxic poison, freeze, sleep and paralysis
(42 independently reported pairs), with HP/PP untouched and saved sleep cleaned
when cured. HP foods/drinks and revivals preserve valid saved status/sleep, PP
and other gameplay state through the existing medicine effect implementation.

`+use Max Honey=6` revives one eligible fainted target to full HP.
**`+use Sacred Ash=party`** revives eligible fainted canonical party members with
one debit. The recorded Sacred Ash flow revives two members; the spare bag copy
remains, and repeating the completed use consumes nothing. Living members, eggs,
boxes, foreign owners and every Fusion reservation are excluded. Single-target
equivalents retain the current Fusion route and reject inactive reservations.
No move selector is accepted by these items, and battles block field use.

Acquisition is intentionally opt-in through existing shop/reward mechanisms;
definitions do not stock live rooms, alter reward tables or grant characters
items. The current shop editor accepts one-token stock keys: a separate staff
fixture configures `add FreshWater 200 5`, then an ordinary player buys
`FreshWater 1` and uses the full name `+use Fresh Water=3`. Both this existing
editor route and full display-name Buy stock are tested. No shop parser is changed.

## Atomic effects and preserved behavior

`FieldFoodUse` extends the existing `FieldMedicineUse` target/effect hooks.
The shared service still locks storage, trainer and fresh owned rows, validates
canonical placement/ownership/egg/battle state and restores shared instances
after rollback. Single-target medicine/berry paths use the same behavior as
before. The new food subclass reuses `BattleMedicineUse`'s durable effect logic
without adding these definitions to its battle allowlist or changing battle code.

For party revival, eligible non-egg party rows are locked in deterministic UUID
order. One outer transaction owns all effect writes and one lazily applied item
debit. No useful target means no debit. A failure after the second SQL save rolls
back the first revival too, restores both cached instances and leaves inventory
unchanged. Retry then succeeds once. Competing party completions, party/single
revival and deposit requests serialize on the existing storage lock and produce
one legal result with exact consumption.

UUID, owner, placement, compatibility mirrors, nickname, species, nature,
friendship, held item, IVs, EVs, EXP, moves and PP remain unchanged. Only the
documented HP/status/sleep fields can change. Missing items, wrong targets,
conflicting owners, ambiguity, invalid scope and ineffective uses are guarded.

## Validation

The [JSON report](field-food-2026-10-21.json) contains the exact 14-item metadata
table, 42 status pairs, 14 purchase/use walkthroughs, source/log hashes, commands,
test results and cleanup. The standalone production-model suite is
[`tests/integration/field_food_cases.py`](../../tests/integration/field_food_cases.py).

| Check | Passing result |
| --- | --- |
| New PostgreSQL food/drink/revival suite | 70 cases: 14 shop-to-use flows, 42 status pairs, 14 integrity/acquisition/concurrency cases |
| Existing field medicine PostgreSQL | 23 cases |
| Existing field berry PostgreSQL | 26 cases |
| Existing battle medicine PostgreSQL | 8 cases |
| Total PostgreSQL | 127 production-model checks |
| Focused pytest | 62 metadata/effect/inventory/itemdex/shop/PP command checks |
| Mandatory combined, repeat and battle-first | 4,428 passed / 4,014 skipped in each process |

All checks passed. Skipped cases remain outside the enabled mandatory scope;
PostgreSQL proof is recorded separately. Existing model-reload and cache
permission warnings are retained. The new production-model suite is wired into
the lifecycle workflow; local success is separate from hosted CI completion.

An added unit renderer assertion initially failed because standalone tests did
not configure Evennia/Django settings. The UI assertion was moved into all 14
configured model walkthroughs without changing product code. The final focused
and integration reruns passed; the preliminary environment-error log is retained
separately and excluded from qualifying proof.

These are automated ordinary-command/model checks with captured transport,
separate staff fixture setup and no successful effect/save substitution. They
do not establish a logged-in live session, main merge or deployment. All ORM
work used generated schemas in a fresh loopback-only PostgreSQL cluster; schemas
were removed, public tables stayed empty and the private cluster was stopped.
The game database, existing characters/Pokemon and game services were untouched.
No migration runner, live shop edit, automatic grant or unrelated work is included.
