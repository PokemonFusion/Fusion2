# Peat Block and ordinary Ursaluna — issue #760

Peat Block is now a complete supplemental gameplay item and supports
`+evolve <pokemon-id> Peat Block` through the existing atomic evolution service.
The [selected rule](../peat-block-evolution.md) was recorded before implementation:
PF2 uses #760's explicit item-use equivalent instead of a lunar calendar. It
requires exact native Ursaring and yields ordinary Ursaluna. No moon/time/region
attribute is required or asserted, and Bloodmoon is not an evolution target.
The existing-item gate and closed #755/#756 dependencies were refreshed first.

The cartridge baseline consumes Peat Block during a full moon, as described by
the [item reference](https://bulbapedia.bulbagarden.net/wiki/Peat_Block#Effect) and
the checked-in Ursaluna row. PF2's deliberate adaptation is labeled in the item
description, command help, main guide and dedicated rule contract. The reference
purchase price is 10000; the existing CSV has no Peat Block row and is unchanged.

## Bounded implementation

`PeatBlockEvolution` requires the complete item identity, exact source/target,
no foreign form metadata, and the reviewed `other` type/full-moon dex condition.
The normal evaluator retains source `evos` / target `prevo`, level, gender,
region and Everstone checks. This one exception supplies a synthesized bag-item
requirement. It does not make the generic condition evaluator accept a full moon
or enable unrelated unsupported rules. Generated dex files are unchanged.

The existing service continues to lock storage, trainer and fresh owned rows,
validate ownership/reservations/egg/battle state, debit one bag item, save the same
Pokemon and publish one receipt within its transaction. The service, placement
writers, schema and battle runtime are unchanged. Failure after actual SQL save
rolls back the item, transition and receipt, restores cached model state, and
allows a successful retry. Competing completions and last-copy requests cannot
double-spend. Reservation/deposit races follow one legal storage-lock order.

Peat Block metadata supplies complete normalized names, description, Evolution
Items category and reference price. Acquisition is opt-in through existing
shop/reward configuration. No live stock, automatic grant, quest, calendar,
weather system, plot-only item or generic evolution override is added. A held
Peat Block is not an evolution trigger; using a separate real bag copy preserves
the held copy. `+use` does not invent a second route.

## Ordinary player flow

Three complete walkthroughs use tagged ordinary owners, actual inventory/currency,
the existing shop editor/Buy path, the shipped commands and production SQL models.
Separate fixture setup configures stock with `add PeatBlock 10000 5`; ordinary
commands then buy two copies, inspect the item and discover the full target ID.
Only client output transport is captured. No staff permissions or live character
session are used.

```text
shop Buy: PeatBlock 2
+inventory
+itemdex Peat Block
+party 3
+evolve <ID copied from +party 3> Peat Block
+party 3
```

The walks cover Guts → Guts with no room, Quick Feet → Bulletproof during day,
and Unnerve → Unnerve during night with an explicit `=Ursaluna` target. Each
retains the same full ID and gapped party slot, consumes one of two bag copies,
and displays ordinary Ursaluna after a fresh SQL reload. Nickname, held Leftovers,
HP/status/sleep, EXP, IVs/EVs, friendship, moves/PP, owner, placement and mirrors
remain unchanged. Types and calculated maximum HP follow the new canonical
species; stored current HP is neither healed nor rescaled. Exact retry consumes
nothing. All three command/output records are retained in JSON.

Negative cases cover missing or partial item input, missing bag copies, held-only
copies, fake moon flags/prose, wrong source/nickname/target, Bloodmoon, Everstone,
eggs, Fusion reservations, battle locks at command/service, foreign/conflicting
owners and changed rule metadata. Positive integrity cases include legal boxed
evolution, legacy inventory aliases, stale cached source correction, preserved
held copies, rollback/retry, duplicate/distinct completion races, two Pokemon
competing for the final bag copy, and reservation/deposit races.

## Validation

The [JSON report](peat-block-2026-10-21.json) records exact commands, source/log
hashes, dependency review, walkthroughs, qualifying results and cleanup. The
new [production-model suite](../../tests/integration/peat_block_cases.py) is wired
into lifecycle CI.

| Check | Passing result |
| --- | --- |
| PostgreSQL alcremie | 76 cases |
| PostgreSQL evolution | 28 cases |
| PostgreSQL field food | 70 cases |
| PostgreSQL peat block | 29 cases |
| PostgreSQL smoke ball | 17 cases |
| PostgreSQL trade held | 33 cases |
| PostgreSQL ui | 14 cases |
| Total PostgreSQL | 267 cases |
| Focused pytest | 160 tests |
| Mandatory combined, repeat and battle-first | 4,500 passed / 4,014 skipped in each process |

All checks passed. All 956 frozen Python sources remained unchanged during validation. All schemas were removed and the private test cluster stopped. Skips remain outside enabled scope; existing warnings are retained.

Preliminary integration failures were fixture errors: the test expected owned
types to be a stored `type_` column rather than computed from species, supplied
`trainer` rather than `owner` to InventoryEntry, and omitted the production
party-slot getter from its captured player adapter. Assertions now inspect
reloaded computed types and use the actual inventory/player interfaces. These
diagnoses did not require changes to gameplay or the evolution service. The
final rerun is the qualifying proof.

Validation uses a fresh private loopback PostgreSQL cluster and isolated schemas,
with an explicit DSN and a guard against game-database fallback. The local wrapper
adapts only unittest argv and test log destinations. No migration runner or
existing service restart is used. This is local automated ordinary-command/model
acceptance, separate from a live login, hosted CI completion, main merge or
deployment. Historical item reports and unrelated work remain outside this change.
